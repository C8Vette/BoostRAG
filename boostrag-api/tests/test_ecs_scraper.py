import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> BeautifulSoup:
    html = (FIXTURES / name).read_text(encoding="utf-8")
    return BeautifulSoup(html, "lxml")


# --- get_ingested_urls ---

def test_get_ingested_urls_returns_urls_from_metadata_jsons(tmp_path, monkeypatch):
    (tmp_path / "product_a.json").write_text(
        json.dumps({"url": "https://www.ecstuning.com/b-ecs/ES111/"}), encoding="utf-8"
    )
    (tmp_path / "product_b.json").write_text(
        json.dumps({"url": "https://www.ecstuning.com/b-ecs/ES222/"}), encoding="utf-8"
    )
    import ecs_scraper
    monkeypatch.setattr(ecs_scraper, "METADATA_DIR", tmp_path)
    result = ecs_scraper.get_ingested_urls()
    assert result == {
        "https://www.ecstuning.com/b-ecs/ES111/",
        "https://www.ecstuning.com/b-ecs/ES222/",
    }


def test_get_ingested_urls_ignores_malformed_json(tmp_path, monkeypatch):
    (tmp_path / "bad.json").write_text("not json", encoding="utf-8")
    (tmp_path / "good.json").write_text(
        json.dumps({"url": "https://www.ecstuning.com/b-ecs/ES333/"}), encoding="utf-8"
    )
    import ecs_scraper
    monkeypatch.setattr(ecs_scraper, "METADATA_DIR", tmp_path)
    result = ecs_scraper.get_ingested_urls()
    assert result == {"https://www.ecstuning.com/b-ecs/ES333/"}


def test_get_ingested_urls_returns_empty_set_when_no_metadata(tmp_path, monkeypatch):
    import ecs_scraper
    monkeypatch.setattr(ecs_scraper, "METADATA_DIR", tmp_path)
    assert ecs_scraper.get_ingested_urls() == set()
