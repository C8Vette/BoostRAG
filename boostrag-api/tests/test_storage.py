import sys, importlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_defaults_to_repo_relative(monkeypatch):
    monkeypatch.delenv("BOOSTRAG_DATA_DIR", raising=False)
    import storage; importlib.reload(storage)
    assert storage.DATA_DIR == Path("data")
    assert storage.CHROMA_PATH == str(Path("vectorstore") / "chroma_db")
    assert storage.COLLECTION_NAME == "boostrag_docs"


def test_root_override_relocates_paths(monkeypatch, tmp_path):
    monkeypatch.setenv("BOOSTRAG_DATA_DIR", str(tmp_path))
    import storage; importlib.reload(storage)
    assert storage.DATA_DIR == tmp_path / "data"
    assert storage.CHROMA_PATH == str(tmp_path / "vectorstore" / "chroma_db")
