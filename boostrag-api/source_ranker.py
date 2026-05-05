from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Literal
from urllib.parse import urlparse


TrustTier = Literal[1, 2, 3]
ReviewStatus = Literal["auto_approved", "limited_use", "quarantined"]
Route = Literal["cleaned", "limited", "quarantine"]


HIGH_TRUST_DOMAINS = {
    "vr-speed.com",
    "vrspeed.com",
    "dinancars.com",
    "ctsturbo.com",
    "activeautowerke.com",
    "burgertuning.com",
    "protuningfreaks.com",
    "bootmod3.net",
    "bm3tuning.com",
    "mhd.tuning.com",
    "mhdtuning.com",
    "turnermotorsport.com",
    "ecstuning.com",
    "fcpeuro.com",
    "getbmwparts.com",
    "kiesmotorsports.com",
}

MEDIUM_TRUST_DOMAINS = {
    "bimmerpost.com",
    "g20.bimmerpost.com",
    "reddit.com",
    "youtube.com",
    "youtu.be",
    "bmwblog.com",
}

LOW_TRUST_HINTS = {
    "best",
    "top 10",
    "cheap",
    "affiliate",
    "coupon",
    "deals",
    "sponsored",
}

FITMENT_KEYWORDS = {
    "fits",
    "fitment",
    "compatible",
    "compatibility",
    "g20",
    "m340i",
    "m440i",
    "b58",
    "b58tu",
    "xdrive",
}

PERFORMANCE_KEYWORDS = {
    "horsepower",
    "hp",
    "whp",
    "torque",
    "dyno",
    "gain",
    "gains",
    "power",
    "flow",
    "backpressure",
    "boost",
    "pure800",
    "pure 800",
    "turbo upgrade",
}

INSTALL_KEYWORDS = {
    "install",
    "installation",
    "instructions",
    "tools",
    "bolt-on",
    "hardware",
    "clamp",
    "o2 sensor",
}

EMISSIONS_KEYWORDS = {
    "emissions",
    "catalyst",
    "catted",
    "catless",
    "gesi",
    "cel",
    "check engine",
    "epa",
    "track use",
    "off-road",
}

RELIABILITY_KEYWORDS = {
    "reliability",
    "reliable",
    "failure",
    "issue",
    "problems",
    "long term",
    "daily",
    "heat soak",
}

PRICE_KEYWORDS = {
    "$",
    "price",
    "sale",
    "msrp",
    "shipping",
}


@dataclass
class SourceScore:
    source_type: str
    trust_tier: TrustTier
    review_status: ReviewStatus
    route: Route
    claim_types: list[str]
    risk_flags: list[str]
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_domain(url: str) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc.lower().strip()

    if domain.startswith("www."):
        domain = domain[4:]

    return domain


def domain_matches(domain: str, approved_domains: set[str]) -> bool:
    return any(
        domain == approved or domain.endswith(f".{approved}")
        for approved in approved_domains
    )


def classify_source_type(url: str, title: str, text: str) -> str:
    domain = normalize_domain(url)
    haystack = f"{domain}\n{title}\n{text}".lower()

    if "youtube.com" in domain or "youtu.be" in domain:
        return "video_or_transcript"

    if "reddit.com" in domain:
        return "community_discussion"

    if "bimmerpost.com" in domain or "forum" in haystack:
        return "forum_thread"

    product_signals = [
        "add to cart",
        "quantity",
        "subtotal",
        "vendor",
        "product type",
        "sku",
        "price",
    ]

    if any(word in haystack for word in product_signals):
        return "product_page"

    if "install" in haystack or "installation" in haystack:
        return "install_or_technical_guide"

    if any(word in haystack for word in ["blog", "article", "review"]):
        return "article_or_review"

    return "web_page"


def tag_claim_types(title: str, text: str) -> list[str]:
    haystack = f"{title}\n{text}".lower()
    claim_types: list[str] = []

    if any(keyword in haystack for keyword in FITMENT_KEYWORDS):
        claim_types.append("fitment")

    if any(keyword in haystack for keyword in PERFORMANCE_KEYWORDS):
        claim_types.append("performance_claim")

    if any(keyword in haystack for keyword in INSTALL_KEYWORDS):
        claim_types.append("installation")

    if any(keyword in haystack for keyword in EMISSIONS_KEYWORDS):
        claim_types.append("emissions_or_cel")

    if any(keyword in haystack for keyword in RELIABILITY_KEYWORDS):
        claim_types.append("reliability_or_user_issue")

    if any(keyword in haystack for keyword in PRICE_KEYWORDS):
        claim_types.append("price_or_purchase_info")

    if not claim_types:
        claim_types.append("general_information")

    return claim_types


def detect_risk_flags(url: str, title: str, text: str) -> list[str]:
    domain = normalize_domain(url)
    haystack = f"{domain}\n{title}\n{text}".lower()
    risk_flags: list[str] = []

    if len(text) < 800:
        risk_flags.append("thin_content")

    if not any(keyword in haystack for keyword in ["m340i", "g20", "b58", "b58tu", "m440i"]):
        risk_flags.append("target_vehicle_unclear")

    if any(hint in haystack for hint in LOW_TRUST_HINTS):
        risk_flags.append("possible_seo_or_affiliate_content")

    if any(
        phrase in haystack
        for phrase in [
            "guaranteed gains",
            "massive horsepower",
            "best ever",
            "unbeatable",
            "secret trick",
        ]
    ):
        risk_flags.append("marketing_or_extreme_claims")

    if "catless" in haystack or "off-road use only" in haystack or "track use only" in haystack:
        risk_flags.append("emissions_sensitive")

    if domain_matches(domain, MEDIUM_TRUST_DOMAINS):
        risk_flags.append("anecdotal_or_community_source")

    if not domain_matches(domain, HIGH_TRUST_DOMAINS) and not domain_matches(
        domain, MEDIUM_TRUST_DOMAINS
    ):
        risk_flags.append("unknown_domain")

    return risk_flags


def score_source(url: str, title: str, text: str) -> SourceScore:
    domain = normalize_domain(url)
    source_type = classify_source_type(url, title, text)
    claim_types = tag_claim_types(title, text)
    risk_flags = detect_risk_flags(url, title, text)

    is_high_trust = domain_matches(domain, HIGH_TRUST_DOMAINS)
    is_medium_trust = domain_matches(domain, MEDIUM_TRUST_DOMAINS)

    if is_high_trust and "thin_content" not in risk_flags:
        if "target_vehicle_unclear" in risk_flags:
            return SourceScore(
                source_type=source_type,
                trust_tier=2,
                review_status="limited_use",
                route="limited",
                claim_types=claim_types,
                risk_flags=risk_flags,
                reason="Known automotive domain, but target vehicle/engine is unclear.",
            )

        return SourceScore(
            source_type=source_type,
            trust_tier=1,
            review_status="auto_approved",
            route="cleaned",
            claim_types=claim_types,
            risk_flags=risk_flags,
            reason="Known high-trust automotive/product source with sufficient content.",
        )

    if is_medium_trust and "thin_content" not in risk_flags:
        return SourceScore(
            source_type=source_type,
            trust_tier=2,
            review_status="limited_use",
            route="limited",
            claim_types=claim_types,
            risk_flags=risk_flags,
            reason="Community or editorial source. Useful as anecdotal/supporting evidence.",
        )

    return SourceScore(
        source_type=source_type,
        trust_tier=3,
        review_status="quarantined",
        route="quarantine",
        claim_types=claim_types,
        risk_flags=risk_flags,
        reason="Unknown, thin, or risky source. Requires review before trusted use.",
    )
