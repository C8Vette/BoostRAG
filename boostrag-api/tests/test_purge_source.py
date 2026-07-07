import json
import sys
from pathlib import Path
from unittest.mock import MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_purge_blacklists_and_deletes_files(tmp_path, monkeypatch):
    import purge_source, provenance, ingest_urls
    monkeypatch.setattr(provenance, "BLACKLIST_PATH", tmp_path / "blacklist.json")
    monkeypatch.setattr(purge_source, "METADATA_DIR", tmp_path / "metadata")
    (tmp_path / "metadata").mkdir()
    # a metadata file whose url matches -> should be deleted along with its text file
    txt = tmp_path / "vrsf.txt"; txt.write_text("body", encoding="utf-8")
    meta = tmp_path / "metadata" / "vrsf.json"
    meta.write_text(json.dumps({"url": "https://bad.com/ES1/", "text_file": str(txt)}), encoding="utf-8")

    fake_collection = MagicMock()
    result = purge_source.purge_source("https://bad.com/ES1/", collection=fake_collection)

    assert result["blacklisted"] is True
    assert result["files_deleted"] >= 1
    assert not txt.exists() and not meta.exists()
    fake_collection.delete.assert_called_once()  # chunks removed by url metadata
    assert provenance.is_blacklisted("https://bad.com/ES1/")
