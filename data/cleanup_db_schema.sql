-- Manual cleanup for obsolete local SQLite tables.
-- Run this manually only while the bot is stopped.
-- If you want to reclaim database file space after cleanup, run VACUUM manually.

DROP TABLE IF EXISTS problems;
DROP TABLE IF EXISTS daily_challenge;
DROP TABLE IF EXISTS problem_embeddings;
DROP TABLE IF EXISTS vec_embeddings;
DROP TABLE IF EXISTS vec_embeddings_chunks;
DROP TABLE IF EXISTS vec_embeddings_info;
DROP TABLE IF EXISTS vec_embeddings_metadatachunks00;
DROP TABLE IF EXISTS vec_embeddings_metadatachunks01;
DROP TABLE IF EXISTS vec_embeddings_metadatatext00;
DROP TABLE IF EXISTS vec_embeddings_metadatatext01;
DROP TABLE IF EXISTS vec_embeddings_rowids;
DROP TABLE IF EXISTS vec_embeddings_vector_chunks00;
