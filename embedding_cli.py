"""CLI tool for building and querying problem embeddings."""

from __future__ import annotations

import argparse
import asyncio
import math
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple

from embeddings import EmbeddingGenerator, EmbeddingRewriter, EmbeddingStorage, SimilaritySearcher
from leetcode import html_to_text
from utils.config import get_config
from utils.database import EmbeddingDatabaseManager
from utils.logger import get_core_logger

logger = get_core_logger()


def _fetch_problems_with_content_sync(db: EmbeddingDatabaseManager) -> List[Tuple[str, str]]:
    rows = db.execute(
        """
        SELECT id, content
        FROM problems
        WHERE content IS NOT NULL AND content != ''
        ORDER BY id ASC
        """,
        fetchall=True,
    )
    return [(str(row[0]), row[1]) for row in rows] if rows else []


def _count_problems_with_content_sync(db: EmbeddingDatabaseManager) -> int:
    row = db.execute(
        """
        SELECT COUNT(*)
        FROM problems
        WHERE content IS NOT NULL AND content != ''
        """,
        fetchone=True,
    )
    return int(row[0]) if row else 0


async def _prepare_db(db: EmbeddingDatabaseManager, dim: int, rebuild: bool) -> None:
    if rebuild:
        db.execute("DROP TABLE IF EXISTS vec_embeddings", commit=True)
    db.create_vec_table(dim)


async def build_embeddings(
    db: EmbeddingDatabaseManager,
    storage: EmbeddingStorage,
    rewriter: EmbeddingRewriter | None,
    generator: EmbeddingGenerator | None,
    source: str,
    batch_size: int,
    rebuild: bool,
    dry_run: bool,
) -> None:
    config = get_config()
    embedding_config = config.get_embedding_model_config()

    await _prepare_db(db, embedding_config.dim, rebuild)

    if rebuild:
        await storage.delete_all_embeddings(source)

    if not rebuild and not db.check_dimension_consistency(embedding_config.dim):
        raise ValueError(
            "Embedding dimension mismatch. Please run with --rebuild to reset the index."
        )

    total_problems = await asyncio.to_thread(_count_problems_with_content_sync, db)
    existing_metadata = await storage.get_existing_ids(
        source, embedding_config.name, embedding_config.dim
    )
    existing_vectors = await storage.get_existing_vector_ids(source)
    existing_ids = existing_metadata.intersection(existing_vectors)
    pending_count = max(total_problems - len(existing_ids), 0)

    logger.info("Total problems with content: %s", total_problems)
    logger.info("Existing embeddings: %s", len(existing_ids))
    logger.info("Pending embeddings: %s", pending_count)

    if dry_run:
        batch_calls = math.ceil(pending_count / batch_size) if batch_size else 0
        logger.info("Estimated embedding API calls: %s", batch_calls)
        logger.info("Estimated rewrite API calls: %s", pending_count)
        logger.info("Estimated cost: depends on Gemini billing settings")
        return
    if rewriter is None or generator is None:
        raise ValueError("Embedding generator not initialized")

    problems = await asyncio.to_thread(_fetch_problems_with_content_sync, db)
    pending = [(pid, content) for pid, content in problems if pid not in existing_ids]

    if not pending:
        logger.info("No pending embeddings to process.")
        return

    total_pending = len(pending)
    effective_batch_size = max(1, batch_size or 1)
    rewrite_workers = max(
        1, min(getattr(rewriter.model_config, "workers", 1), total_pending)
    )
    logger.info(
        "Starting rewrite pipeline: %s problems, workers=%s, batch_size=%s",
        total_pending,
        rewrite_workers,
        effective_batch_size,
    )
    executor = ThreadPoolExecutor(max_workers=rewrite_workers)
    try:
        rewrite_queue: asyncio.Queue[Tuple[str, str] | None] = asyncio.Queue()
        embed_queue: asyncio.Queue[Tuple[str, str] | None] = asyncio.Queue()
        for item in pending:
            rewrite_queue.put_nowait(item)
        for _ in range(rewrite_workers):
            rewrite_queue.put_nowait(None)

        progress_lock = asyncio.Lock()
        rewritten_count = 0
        skipped_count = 0

        async def rewrite_worker(worker_id: int) -> None:
            nonlocal rewritten_count, skipped_count
            while True:
                item = await rewrite_queue.get()
                if item is None:
                    rewrite_queue.task_done()
                    break
                problem_id, content = item
                text = html_to_text(content) if content else ""
                if not text.strip():
                    logger.warning("Problem %s skipped: empty content", problem_id)
                    async with progress_lock:
                        skipped_count += 1
                        rewritten_count += 1
                    rewrite_queue.task_done()
                    continue
                try:
                    rewritten = await rewriter.rewrite_with_executor(text, executor)
                except Exception as exc:
                    logger.error("Rewrite failed for problem %s: %s", problem_id, exc)
                    async with progress_lock:
                        skipped_count += 1
                        rewritten_count += 1
                    rewrite_queue.task_done()
                    continue
                if not rewritten or not rewritten.strip():
                    logger.warning(
                        "Problem %s skipped: rewrite produced empty content", problem_id
                    )
                    async with progress_lock:
                        skipped_count += 1
                        rewritten_count += 1
                    rewrite_queue.task_done()
                    continue
                await embed_queue.put((problem_id, rewritten))
                async with progress_lock:
                    rewritten_count += 1
                    if rewritten_count % 50 == 0 or rewritten_count == total_pending:
                        logger.info(
                            "Rewrite progress %s/%s (skipped %s)",
                            rewritten_count,
                            total_pending,
                            skipped_count,
                        )
                rewrite_queue.task_done()

        async def embed_worker() -> None:
            buffer: List[Tuple[str, str]] = []
            embedded_total = 0
            while True:
                item = await embed_queue.get()
                if item is None:
                    embed_queue.task_done()
                    break
                buffer.append(item)
                if len(buffer) >= effective_batch_size:
                    embedded_total += await _flush_embeddings(
                        buffer, storage, generator, embedding_config, source
                    )
                    buffer.clear()
                embed_queue.task_done()
            if buffer:
                embedded_total += await _flush_embeddings(
                    buffer, storage, generator, embedding_config, source
                )
            logger.info("Embedding pipeline complete (%s problems)", embedded_total)

        async def _flush_embeddings(
            batch: List[Tuple[str, str]],
            storage: EmbeddingStorage,
            generator: EmbeddingGenerator,
            embedding_config,
            source: str,
        ) -> int:
            rewritten_texts = [item[1] for item in batch]
            problem_ids = [item[0] for item in batch]
            try:
                embeddings = await generator.embed_batch(rewritten_texts)
            except Exception as exc:
                logger.error("Embedding batch failed: %s", exc)
                return 0
            for problem_id, rewritten, embedding in zip(
                problem_ids, rewritten_texts, embeddings
            ):
                await storage.save_embedding(
                    source,
                    problem_id,
                    rewritten,
                    embedding_config.name,
                    embedding_config.dim,
                    embedding,
                )
            return len(problem_ids)

        rewrite_tasks = [
            asyncio.create_task(rewrite_worker(i)) for i in range(rewrite_workers)
        ]
        embed_task = asyncio.create_task(embed_worker())

        await rewrite_queue.join()
        await embed_queue.put(None)
        await embed_queue.join()
        await asyncio.gather(*rewrite_tasks)
        await embed_task
    finally:
        executor.shutdown(wait=True)


async def query_similar(
    db: EmbeddingDatabaseManager,
    storage: EmbeddingStorage,
    rewriter: EmbeddingRewriter,
    generator: EmbeddingGenerator,
    source: str,
    query: str,
    top_k: int,
    min_similarity: float,
) -> None:
    if not query.strip():
        print("Please provide a problem description or keywords.")
        return

    config = get_config()
    embedding_config = config.get_embedding_model_config()

    await _prepare_db(db, embedding_config.dim, rebuild=False)

    if not db.check_dimension_consistency(embedding_config.dim):
        raise ValueError(
            "Embedding dimension mismatch. Please run with --rebuild to reset the index."
        )

    total_vectors = await storage.count_embeddings(source)
    if total_vectors == 0:
        print("Embedding index is empty. Run embedding_cli.py --build first.")
        return

    rewritten = await rewriter.rewrite(query)
    embedding = await generator.embed(rewritten)
    searcher = SimilaritySearcher(db, storage)
    results = await searcher.search(embedding, source, top_k, min_similarity)

    if not results:
        print("No similar problems found. Try a more detailed description.")
        return

    print("Top similar problems:")
    for idx, result in enumerate(results, start=1):
        title = result.get("title") or result.get("problem_id")
        difficulty = result.get("difficulty") or "N/A"
        similarity = result.get("similarity")
        link = result.get("link") or ""
        print(f"{idx}. {title} ({difficulty}) similarity={similarity:.2f}")
        if link:
            print(f"   {link}")


async def show_stats(db: EmbeddingDatabaseManager, storage: EmbeddingStorage, source: str) -> None:
    config = get_config()
    embedding_config = config.get_embedding_model_config()

    await _prepare_db(db, embedding_config.dim, rebuild=False)

    total_problems = await asyncio.to_thread(_count_problems_with_content_sync, db)
    total_vectors = await storage.count_embeddings(source)
    total_metadata = await storage.count_metadata(source)

    pending = max(total_problems - total_metadata, 0)
    print("Embedding stats:")
    print(f"  Total problems (with content): {total_problems}")
    print(f"  Metadata rows: {total_metadata}")
    print(f"  Vector rows: {total_vectors}")
    print(f"  Pending: {pending}")


DEFAULT_EMBEDDING_SOURCE = "leetcode"


async def main() -> None:
    parser = argparse.ArgumentParser(description="Embedding CLI tool")
    parser.add_argument("--build", action="store_true", help="Build embeddings")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild embeddings")
    parser.add_argument("--query", type=str, help="Query similar problems")
    parser.add_argument("--stats", action="store_true", help="Show embedding stats")
    parser.add_argument("--dry-run", action="store_true", help="Estimate embedding cost")
    # Compromise: problems table has no source, so CLI default tags embeddings as leetcode.
    parser.add_argument(
        "--source",
        type=str,
        help="Problem source",
        default=DEFAULT_EMBEDDING_SOURCE,
    )
    parser.add_argument("--top-k", type=int, help="Top-k results", default=None)
    parser.add_argument(
        "--min-similarity",
        type=float,
        help="Minimum similarity threshold",
        default=None,
    )
    parser.add_argument("--batch-size", type=int, help="Embedding batch size", default=None)

    args = parser.parse_args()
    config = get_config()
    similar_config = config.get_similar_config()
    embedding_config = config.get_embedding_model_config()

    source = args.source
    top_k = args.top_k or similar_config.top_k
    min_similarity = (
        args.min_similarity if args.min_similarity is not None else similar_config.min_similarity
    )
    batch_size = args.batch_size or embedding_config.batch_size

    if not (args.build or args.rebuild or args.query or args.stats):
        parser.print_help()
        return

    db = EmbeddingDatabaseManager(db_path=config.database_path)
    storage = EmbeddingStorage(db)
    rewriter = None
    generator = None
    needs_llm = args.query or ((args.build or args.rebuild) and not args.dry_run)
    if needs_llm:
        rewriter = EmbeddingRewriter(config)
        generator = EmbeddingGenerator(config)

    if args.stats:
        await show_stats(db, storage, source)
    if args.query:
        await query_similar(
            db,
            storage,
            rewriter,
            generator,
            source,
            args.query,
            top_k,
            min_similarity,
        )
    if args.build or args.rebuild:
        await build_embeddings(
            db,
            storage,
            rewriter,
            generator,
            source,
            batch_size,
            args.rebuild,
            args.dry_run,
        )


if __name__ == "__main__":
    asyncio.run(main())
