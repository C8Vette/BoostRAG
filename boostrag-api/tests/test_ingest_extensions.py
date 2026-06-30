import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ingest_urls import build_cleaned_text

MINIMAL_SCORE = {
    "source_type": "product_page",
    "trust_tier": 1,
    "review_status": "auto_approved",
    "claim_types": ["fitment"],
    "risk_flags": [],
    "reason": "Test",
}

BASE_KWARGS = dict(
    title="Test Product",
    url="https://www.ecstuning.com/b-ecs/ES123/",
    domain="ecstuning.com",
    description=None,
    brand="ECS Tuning",
    category="Intake",
    vehicle="BMW M340i G20",
    price="$349.00",
    body_text="Great intake for the B58.",
    score=MINIMAL_SCORE,
)


def test_build_cleaned_text_includes_fitment_when_provided():
    result = build_cleaned_text(**BASE_KWARGS, fitment=["G20", "G29", "G01"])
    assert "Fitment: G20, G29, G01" in result


def test_build_cleaned_text_fitment_appears_after_vehicle():
    result = build_cleaned_text(**BASE_KWARGS, fitment=["G20"])
    vehicle_pos = result.index("Vehicle:")
    fitment_pos = result.index("Fitment:")
    price_pos = result.index("Price:")
    assert vehicle_pos < fitment_pos < price_pos


def test_build_cleaned_text_omits_fitment_line_when_none():
    result = build_cleaned_text(**BASE_KWARGS)
    assert "Fitment:" not in result


def test_build_cleaned_text_price_in_output():
    result = build_cleaned_text(**BASE_KWARGS)
    assert "Price: $349.00" in result
