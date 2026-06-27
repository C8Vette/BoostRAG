"""
Quick CLI test for BoostRAG Research Mode source discovery.

Usage:
    python test_research.py "Can I run a valved dump exhaust on my M340i xDrive?"
"""

from __future__ import annotations

import sys

from research_search import tavily_research_search


def main() -> None:
    """Run a test web research query and print ranked candidate sources."""
    if len(sys.argv) < 2:
        print('Usage: python test_research.py "your research question"')
        raise SystemExit(1)

    query = " ".join(sys.argv[1:])
    print(f"\nResearch query: {query}\n")

    sources = tavily_research_search(query, max_results=5)

    for index, source in enumerate(sources[:10], start=1):
        print("=" * 90)
        print(f"{index}. {source.title}")
        print(f"URL: {source.url}")
        print(f"Score: {source.score}")
        print(f"Trust: {source.trust_label}")
        print(f"Reason: {source.reason}")
        print(f"Preview: {source.content[:350].strip()}...")


if __name__ == "__main__":
    main()