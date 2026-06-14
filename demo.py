"""
demo.py — Local Demo Entry Point
Test the Pipeline without starting the Teams Bot.

Usage:
    # Demo mode (built-in sample data, no API calls)
    DEMO_MODE=true python demo.py

    # Full mode (requires .env with real API keys)
    python demo.py

    # Knowledge query mode
    python demo.py --query "how to handle large Excel exports"
"""
from __future__ import annotations
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["DEMO_MODE"] = os.getenv("DEMO_MODE", "false")


def main():
    parser = argparse.ArgumentParser(description="AI Requirement Pipeline — Demo")
    parser.add_argument(
        "input", nargs="?",
        default="Our QC inspectors need photo-based defect classification on the factory floor to replace paper forms",
        help="Requirement description text",
    )
    parser.add_argument("--query", "-q", action="store_true", help="Knowledge query mode")
    parser.add_argument("--demo", action="store_true", default=True, help="Demo mode (default on)")
    parser.add_argument("--full", action="store_true", help="Full pipeline mode (requires .env API keys)")

    args = parser.parse_args()

    if args.full:
        os.environ["DEMO_MODE"] = "false"

    from pipeline.pipeline import run_pipeline, query_foundry_iq

    if args.query:
        print(f"\nSearching Foundry IQ: {args.input}")
        answer = query_foundry_iq(args.input)
        print(f"\n{'='*60}\n{answer}\n{'='*60}\n")
        return

    print(f"\n{'='*60}")
    print(f"  AI Requirement Pipeline — Demo")
    print(f"  Demo Mode: {os.environ.get('DEMO_MODE', 'false')}")
    print(f"{'='*60}")

    state = run_pipeline(args.input, submitted_by="demo_user")

    print(f"\n{'='*60}")
    print(f"  Pipeline Results Summary")
    print(f"{'='*60}")
    print(f"  Requirement ID: {state.requirement_id}")
    print(f"  Original Input: {state.original_text[:80]}...")
    if state.requirement_title:
        print(f"  AI Title: {state.requirement_title}")

    for stage_num, schema in state.schemas.items():
        stage_name = schema.get("stage", f"stage{stage_num}")
        print(f"\n  -- Stage {stage_num}: {stage_name} --")
        print(json.dumps(schema, ensure_ascii=False, indent=2)[:500])

    print(f"\n  -- Execution Log --")
    for entry in state.log:
        print(f"  {entry}")

    output_file = "demo_output.json"
    output = {
        "requirement_id": state.requirement_id,
        "original_text": state.original_text,
        "ai_title": state.requirement_title,
        "schemas": state.schemas,
        "log": state.log,
    }
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n  Full output saved to: {output_file}")


if __name__ == "__main__":
    main()
