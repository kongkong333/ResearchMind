from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.collectors.paper_collector import PaperCollector
from app.services.collectors.pubmed_source import PubMedPaperSource


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Minimal diagnostic for the paper collection pipeline.",
    )
    parser.add_argument("--topic", default="agent")
    parser.add_argument("--show", type=int, default=5, help="How many sample titles to print.")
    parser.add_argument("--verbose", action="store_true", help="Print fetch-chain diagnostics.")
    args = parser.parse_args()

    source = PubMedPaperSource(limit=args.show)
    collector = PaperCollector()

    print("=== ResearchMind Collection Diagnostic ===")
    print(f"Topic: {args.topic}")

    if args.verbose:
        print("\n--- Fetch Chain ---")
        remote_query = source._build_topic_query(args.topic)
        relevance_ids = source._search_ids(remote_query, sort="relevance", limit=args.show * 3)
        print(f"  remote_query={remote_query}")
        print(f"  relevance_ids={relevance_ids}")

    papers = source.fetch(args.topic)
    print(f"\nRaw fetched papers: {len(papers)}")
    for index, paper in enumerate(papers[: args.show], start=1):
        print(f"  {index}. [{paper.venue} {paper.year}] {paper.title}")

    filtered = collector.collect_from_papers(
        papers,
        topic=args.topic,
    )
    print(f"\nCollected papers: {len(filtered)}")
    for index, paper in enumerate(filtered[: args.show], start=1):
        print(f"  {index}. [{paper.venue} {paper.year}] {paper.title}")

    if not papers:
        print("\nDiagnosis: fetch stage returned 0 papers. Check PubMed remote availability or the query topic.")
    elif not filtered:
        print("\nDiagnosis: fetch stage returned papers, but collection-stage constraints removed them.")
    else:
        print("\nDiagnosis: remote fetch and collection stages both returned usable papers.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
