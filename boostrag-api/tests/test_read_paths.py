import sys, importlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_corpus_read_paths_track_storage_root(monkeypatch, tmp_path):
    """preprocess (corpus read) and purge_source (metadata scan) must relocate
    with BOOSTRAG_DATA_DIR, so the read path tracks the write path on a disk."""
    monkeypatch.setenv("BOOSTRAG_DATA_DIR", str(tmp_path))
    import storage; importlib.reload(storage)
    import preprocess; importlib.reload(preprocess)
    import purge_source; importlib.reload(purge_source)
    assert preprocess.DATA_DIR == tmp_path / "data" / "cleaned"
    assert purge_source.METADATA_DIR == tmp_path / "data" / "metadata"


def test_corpus_read_paths_default_to_repo_relative(monkeypatch):
    monkeypatch.delenv("BOOSTRAG_DATA_DIR", raising=False)
    import storage; importlib.reload(storage)
    import preprocess; importlib.reload(preprocess)
    import purge_source; importlib.reload(purge_source)
    assert preprocess.DATA_DIR == Path("data") / "cleaned"
    assert purge_source.METADATA_DIR == Path("data") / "metadata"
