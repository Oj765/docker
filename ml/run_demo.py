"""
Misinfo Shield - Interactive Demo Runner
=========================================
Accepts either a direct text claim or a public URL to scrape text from.

Usage:
    cd hack
    python run_demo.py
"""

import sys
import os
import asyncio
import json
import logging
import re
import hashlib
from datetime import datetime, timezone

# Setup path and env
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ml-agent"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "ml-agent", ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-30s | %(message)s",
    datefmt="%H:%M:%S",
)

from agent.graph import graph


def is_url(text: str) -> bool:
    return text.strip().startswith("http://") or text.strip().startswith("https://")


async def scrape_text_from_url(url: str) -> str:
    """Fetch a public URL and extract readable text from it."""
    try:
        import httpx
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            resp = await client.get(url, headers={"User-Agent": "MisinfoShield/1.0"})
            resp.raise_for_status()
            html = resp.text

        # Strip HTML tags to get raw text
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()

        # Take first 1500 chars as the claim content (enough for analysis)
        if len(text) > 1500:
            text = text[:1500] + "..."

        return text
    except Exception as e:
        print(f"  [!] Failed to fetch URL: {e}")
        return ""


def generate_claim_id(text: str) -> str:
    return "claim_" + hashlib.md5(text[:100].encode()).hexdigest()[:10]


def detect_platform(url: str) -> str:
    url_lower = url.lower()
    if "twitter.com" in url_lower or "x.com" in url_lower:
        return "twitter"
    if "reddit.com" in url_lower:
        return "reddit"
    if "t.me" in url_lower or "telegram" in url_lower:
        return "telegram"
    if "facebook.com" in url_lower or "fb.com" in url_lower:
        return "facebook"
    if "instagram.com" in url_lower:
        return "instagram"
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    return "web"


def print_verdict(verdict: dict):
    """Pretty-print the verdict in a readable format."""
    label = verdict.get("label", "???")
    conf = verdict.get("confidence", 0)
    risk = verdict.get("risk_score", 0)
    severity = verdict.get("severity_rating", "???")

    print()
    print("  " + "=" * 60)
    print(f"  VERDICT: {label}")
    print("  " + "=" * 60)
    print(f"  Confidence  : {conf:.2f}")
    print(f"  Risk Score  : {risk:.2f}")
    print(f"  Severity    : {severity}")
    print(f"  Satire      : {verdict.get('satire_flag', False)}")
    print(f"  Language    : {verdict.get('language', '?')}")
    print(f"  Mutation of : {verdict.get('mutation_of', 'None')}")
    print(f"  6h Reach    : {verdict.get('predicted_6h_reach', 0)}")

    # Geo Info
    geo = verdict.get("geo_info", {})
    if geo:
        print(f"\n  Region      : {geo.get('predicted_region', '?')} (conf: {geo.get('region_confidence', 0):.2f})")
        print(f"  Topics      : {', '.join(geo.get('topic_tags', []))}")
        print(f"  Time Context: {geo.get('time_context', '?')}")
        regions = geo.get("predicted_regions", [])
        if len(regions) > 1:
            print(f"  All Regions : {', '.join(regions)}")

    # Narrative Graph
    narrative = verdict.get("narrative", {})
    if narrative and narrative.get("account_id"):
        print(f"\n  Narrative Graph:")
        print(f"    Account   : {narrative.get('account_id', '?')} ({narrative.get('platform', '?')})")
        linked = narrative.get("linked_claims", [])
        if linked:
            print(f"    Linked    : {len(linked)} related claim(s)")
        campaign = narrative.get("campaign_id")
        if campaign:
            print(f"    Campaign  : {campaign}")

    # Reasoning Chain
    chain = verdict.get("reasoning_chain", [])
    if chain:
        print(f"\n  Reasoning Chain ({len(chain)} steps):")
        for i, step in enumerate(chain, 1):
            display = step if len(step) < 120 else step[:117] + "..."
            print(f"    {i}. {display}")

    # Evidence Sources
    sources = verdict.get("evidence_sources", [])
    if sources:
        print(f"\n  Evidence Sources ({len(sources)}):")
        for src in sources:
            cred = src.get("credibility_score", 0)
            stype = src.get("source_type", "?")
            title = src.get("title", "?")
            if len(title) > 70:
                title = title[:67] + "..."
            print(f"    - [{cred:.1f}] [{stype}] {title}")
            print(f"      {src.get('url', '')}")

    # Save to JSON for easy access
    with open("verdict_output.json", "w", encoding="utf-8") as f:
        json.dump(verdict, f, indent=2, ensure_ascii=False)
    print(f"\n  [Saved to verdict_output.json]")
    print()


async def process_input(user_input: str):
    """Process a single input (URL or direct text)."""
    if is_url(user_input):
        url = user_input.strip()
        platform = detect_platform(url)
        print(f"\n  Fetching content from {platform} URL...")
        text = await scrape_text_from_url(url)
        if not text:
            print("  Could not extract text from URL. Try pasting the text directly.")
            return
        print(f"  Extracted {len(text)} chars of text.")
        source_url = url
    else:
        text = user_input.strip()
        platform = "direct_input"
        source_url = ""

    claim_state = {
        "claim_id": generate_claim_id(text),
        "original_text": text,
        "source_platform": platform,
        "source_account_id": "demo_user",
        "source_post_url": source_url,
        "source_followers": 1000,
        "media_urls": [],
        "engagement": {"likes": 100, "shares": 50, "comments": 20},
        "posted_at": datetime.now(timezone.utc).isoformat(),
    }

    print(f"\n  Claim ID: {claim_state['claim_id']}")
    print(f"  Platform: {platform}")
    print(f"  Text: {text[:100]}{'...' if len(text) > 100 else ''}")
    print("\n  Running pipeline: ingest > translate > extract > dedup > verify > score > enrich > guardrail > verdict > output")
    print("  " + "-" * 60)

    try:
        result = await graph.ainvoke(claim_state)
        verdict = result.get("verdict")
        if verdict:
            print_verdict(verdict)
        else:
            print("\n  [!] No verdict generated. Check logs above.")
    except Exception as e:
        print(f"\n  [ERROR] Pipeline failed: {e}")


async def main():
    print()
    print("  ============================================================")
    print("  MISINFO SHIELD - ML/AI Pipeline Demo")
    print("  ============================================================")
    print()
    print("  Enter a claim to fact-check. You can provide:")
    print("    1. Direct text  (e.g. 'Drinking bleach cures viruses')")
    print("    2. A public URL (e.g. https://twitter.com/user/status/123)")
    print()
    print("  Type 'quit' or 'exit' to stop.")
    print()

    while True:
        try:
            user_input = input("  >> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("  Goodbye!")
            break

        await process_input(user_input)


if __name__ == "__main__":
    asyncio.run(main())
