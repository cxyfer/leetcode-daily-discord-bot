from utils.database import LLMInspireDatabaseManager, LLMTranslateDatabaseManager


def test_translate_cache_accepts_string_id(tmp_path):
    db_path = tmp_path / "db.sqlite"
    manager = LLMTranslateDatabaseManager(db_path=str(db_path), expire_seconds=3600)

    manager.save_translation("abc436_g", "atcoder", "translated", model_name="m")
    result = manager.get_translation("abc436_g", "atcoder")

    assert result is not None
    assert result["translation"] == "translated"
    assert result["model_name"] == "m"


def test_inspire_cache_accepts_string_id(tmp_path):
    db_path = tmp_path / "db.sqlite"
    manager = LLMInspireDatabaseManager(db_path=str(db_path), expire_seconds=3600)

    manager.save_inspire(
        "abc436_g",
        "atcoder",
        "thinking",
        "traps",
        "algorithms",
        "inspiration",
        model_name="m",
    )
    result = manager.get_inspire("abc436_g", "atcoder")

    assert result is not None
    assert result["thinking"] == "thinking"
    assert result["model_name"] == "m"
