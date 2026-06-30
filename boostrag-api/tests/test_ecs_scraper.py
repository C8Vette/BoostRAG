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


# --- extract_ecs_price ---

def test_extract_ecs_price_reads_json_ld_price():
    from ecs_scraper import extract_ecs_price
    soup = load_fixture("ecs_product_intake.html")
    assert extract_ecs_price(soup) == "$349.00"


def test_extract_ecs_price_falls_back_when_no_json_ld():
    from ecs_scraper import extract_ecs_price
    soup = load_fixture("ecs_product_downpipe.html")
    # No JSON-LD in downpipe fixture; regex should find $549.00, not $150.00 core deposit
    result = extract_ecs_price(soup)
    assert result == "$549.00"


def test_extract_ecs_price_returns_unknown_when_no_price():
    from ecs_scraper import extract_ecs_price
    soup = BeautifulSoup("<html><body><p>No price info here.</p></body></html>", "lxml")
    assert extract_ecs_price(soup) == "Unknown"


# --- extract_fitment ---

def test_extract_fitment_returns_sorted_chassis_codes():
    from ecs_scraper import extract_fitment
    soup = load_fixture("ecs_product_intake.html")
    result = extract_fitment(soup)
    assert result == ["F30", "G01", "G20", "G29"]


def test_extract_fitment_returns_partial_list_when_fewer_chassis():
    from ecs_scraper import extract_fitment
    soup = load_fixture("ecs_product_downpipe.html")
    result = extract_fitment(soup)
    assert result == ["G20", "G26"]


def test_extract_fitment_returns_empty_list_when_no_chassis_found():
    from ecs_scraper import extract_fitment
    soup = BeautifulSoup("<html><body><p>No fitment info.</p></body></html>", "lxml")
    assert extract_fitment(soup) == []


# --- URL discovery ---

def test_extract_product_urls_from_page_finds_ecs_sku_links():
    from ecs_scraper import _extract_product_urls_from_page
    soup = load_fixture("ecs_category_page.html")
    urls = _extract_product_urls_from_page(soup, "https://www.ecstuning.com")
    assert "https://www.ecstuning.com/b-ecs-tuning/s-intake/ES4563456/" in urls
    assert "https://www.ecstuning.com/b-vrsf/s-charge-pipe/ES7891234/" in urls
    assert "https://www.ecstuning.com/b-ecs-tuning/s-heat-exchanger/ES1122334/" in urls
    assert len(urls) == 3


def test_get_next_page_url_returns_href_when_present():
    from ecs_scraper import _get_next_page_url
    soup = load_fixture("ecs_category_page.html")
    result = _get_next_page_url(soup)
    assert result == "https://www.ecstuning.com/b-BMW/c-B58/?page=2"


def test_get_next_page_url_returns_none_on_last_page():
    from ecs_scraper import _get_next_page_url
    soup = BeautifulSoup("<html><body><p>Last page, no next link.</p></body></html>", "lxml")
    assert _get_next_page_url(soup) is None


def test_get_product_urls_follows_pagination():
    from ecs_scraper import get_product_urls

    page1_html = (FIXTURES / "ecs_category_page.html").read_text(encoding="utf-8")
    page2_html = """
    <html><body>
      <a href="https://www.ecstuning.com/b-ecs/s-exhaust/ES9999999/">Exhaust</a>
    </body></html>
    """

    responses = {
        "https://www.ecstuning.com/b-BMW/c-B58/": page1_html,
        "https://www.ecstuning.com/b-BMW/c-B58/?page=2": page2_html,
    }

    mock_session = MagicMock()
    def fake_get(url, **kwargs):
        r = MagicMock()
        r.text = responses[url]
        r.raise_for_status = MagicMock()
        return r
    mock_session.get.side_effect = fake_get

    with patch("ecs_scraper.time.sleep"):
        urls = get_product_urls("https://www.ecstuning.com/b-BMW/c-B58/", mock_session)

    assert len(urls) == 4
    assert "https://www.ecstuning.com/b-ecs/s-exhaust/ES9999999/" in urls
