"""
main.py — CrowdWisdomTrading Product Marketing Agent
Entry point that orchestrates all four agents in sequence.

Run:
    python main.py
    python main.py --post-replies   # actually post to Reddit (DRY_RUN=False)
    python main.py --skip-research  # skip scraping, use cached results
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

import config
from agents.product_researcher import ProductResearcherAgent
from agents.report_writer import ReportWriterAgent
from agents.reddit_agent import RedditAgent
from agents.learning_loop import LearningLoop

# ── logging setup ──────────────────────────────────────────────────────────────
LOG_FILE = os.path.join(
    config.LOG_DIR,
    f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[
        RichHandler(rich_tracebacks=True),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")
console = Console()

CACHE_FILE = os.path.join(config.OUTPUT_DIR, "research_cache.json")


def validate_env() -> bool:
    """Check that required env vars are set."""
    missing = []
    if not config.OPENROUTER_API_KEY:
        missing.append("OPENROUTER_API_KEY")
    if not config.APIFY_API_TOKEN:
        missing.append("APIFY_API_TOKEN")
    if missing:
        console.print(f"[red]Missing env vars: {', '.join(missing)}[/red]")
        console.print("Copy .env.example to .env and fill in your credentials.")
        return False
    return True


def load_cache() -> dict | None:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return None


def save_cache(data: dict) -> None:
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def main(post_replies: bool = False, skip_research: bool = False) -> None:
    console.print(Panel.fit(
        "[bold cyan]CrowdWisdomTrading — Product Marketing Agent[/bold cyan]\n"
        "Multi-agent pipeline: Research → Report → Reddit → Learn",
        border_style="cyan",
    ))

    if not validate_env():
        sys.exit(1)

    loop = LearningLoop()
    prior_context = loop.get_context()
    logger.info("Prior learning context:\n%s", prior_context)

    run_outputs: dict = {}

    # ── Agent 1: Product & Competitor Research ─────────────────────────────────
    if skip_research and (cached := load_cache()):
        console.print("[yellow]Using cached research data.[/yellow]")
        research_data = cached
    else:
        console.print("\n[bold]Step 1:[/bold] Product & competitor research…")
        with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
            task = p.add_task("Scraping CWT & competitors via Apify…", total=None)
            researcher = ProductResearcherAgent()
            research_data = researcher.run()
            p.update(task, completed=True)
        save_cache(research_data)
        console.print(f"  ✓ Found [green]{len(research_data['competitors'])}[/green] competitors")

    run_outputs["research"] = research_data

    # ── Agent 2: Competitive Report ────────────────────────────────────────────
    console.print("\n[bold]Step 2:[/bold] Writing competitive analysis report…")
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
        task = p.add_task("Generating report…", total=None)
        writer = ReportWriterAgent()
        report_path = writer.run(research_data)
        p.update(task, completed=True)
    console.print(f"  ✓ Report saved → [green]{report_path}[/green]")
    run_outputs["report_path"] = report_path

    # ── Agent 3: Reddit Pain Finder ────────────────────────────────────────────
    console.print("\n[bold]Step 3:[/bold] Finding Reddit pain points & drafting replies…")
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
        task = p.add_task("Searching Reddit & drafting replies…", total=None)
        reddit_agent = RedditAgent()
        reddit_result = reddit_agent.run(post_replies=post_replies)
        p.update(task, completed=True)

    n_replies = len(reddit_result.get("replies", []))
    console.print(f"  ✓ Drafted [green]{n_replies}[/green] Reddit replies → {reddit_result.get('output_file', '')}")
    run_outputs["reddit"] = reddit_result

    # ── Print replies to console ───────────────────────────────────────────────
    console.print("\n[bold cyan]── Reddit Replies Preview ──[/bold cyan]")
    for i, r in enumerate(reddit_result.get("replies", []), 1):
        console.print(f"\n[bold]Reply {i}[/bold] → r/{r['subreddit']}")
        console.print(f"[dim]Post: {r['post_title'][:80]}[/dim]")
        console.print(f"[dim]URL: {r['post_url']}[/dim]")
        console.print(r["reply_text"])

    # ── Agent 4: Learning Loop ─────────────────────────────────────────────────
    console.print("\n[bold]Step 4:[/bold] Reflecting and updating learning memory…")
    reflection = loop.reflect(run_outputs)
    console.print(f"  ✓ Run quality score: [green]{reflection.get('run_quality_score', '?')}/10[/green]")
    if reflection.get("what_to_improve"):
        console.print("  [yellow]To improve next run:[/yellow]")
        for item in reflection["what_to_improve"]:
            console.print(f"    • {item}")

    console.print(Panel.fit(
        f"[bold green]All done![/bold green]\n"
        f"Log: {LOG_FILE}\n"
        f"Outputs: {config.OUTPUT_DIR}",
        border_style="green",
    ))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CWT Marketing Agent")
    parser.add_argument(
        "--post-replies",
        action="store_true",
        help="Actually post Reddit replies (default: dry run only)",
    )
    parser.add_argument(
        "--skip-research",
        action="store_true",
        help="Skip scraping and use cached research data",
    )
    args = parser.parse_args()
    main(post_replies=args.post_replies, skip_research=args.skip_research)
