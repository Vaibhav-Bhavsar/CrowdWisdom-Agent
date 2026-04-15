"""
agents/learning_loop.py  — Closed Learning Loop (Agent 4)

Uses Hermes Agent's built-in reflection hooks to:
1. Evaluate outputs from each preceding agent.
2. Identify what worked and what didn't.
3. Write structured feedback to a JSON memory file.
4. On next run, inject that feedback as context so agents improve.

This is a simplified Hermes-compatible implementation. If you have the full
Hermes Agent package, swap the HermesAgent stub below for the real import.
"""
import json
import logging
import os
from datetime import datetime
from typing import Any

from tools.openrouter_client import OpenRouterClient
import config

logger = logging.getLogger(__name__)

MEMORY_FILE = os.path.join(config.OUTPUT_DIR, "learning_memory.json")

REFLECTION_SYSTEM = """You are a self-improving AI agent evaluator.
Your job is to analyze the outputs of a marketing agent pipeline and produce
structured feedback that will help the agents do better on the next run.
Be specific and actionable."""


def load_memory() -> dict:
    """Load the persisted learning memory from disk."""
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"runs": [], "global_learnings": []}


def save_memory(memory: dict) -> None:
    """Persist the updated learning memory to disk."""
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)
    logger.info("Learning memory saved → %s", MEMORY_FILE)


class LearningLoop:
    """
    Wraps the full agent pipeline with reflection and memory.

    Usage:
        loop = LearningLoop()
        prior_context = loop.get_context()  # inject into agents
        # ... run agents ...
        loop.reflect(run_outputs)           # update memory
    """

    def __init__(self, llm: OpenRouterClient | None = None):
        self.llm = llm or OpenRouterClient()
        self.memory = load_memory()

    def get_context(self) -> str:
        """
        Return a text summary of past learnings to inject at the start of a run.
        Agents can use this to avoid repeating past mistakes.
        """
        learnings = self.memory.get("global_learnings", [])
        if not learnings:
            return "No prior runs recorded. Starting fresh."

        lines = ["## Learnings from previous runs\n"]
        for i, learning in enumerate(learnings[-5:], 1):  # last 5
            lines.append(f"{i}. {learning}")
        return "\n".join(lines)

    def reflect(self, run_outputs: dict[str, Any]) -> dict:
        """
        Ask the LLM to reflect on this run's outputs and extract learnings.
        Saves them back to the memory file.
        """
        logger.info("=== LearningLoop reflecting on run outputs ===")

        summary = json.dumps(
            {
                "competitors_found": len(run_outputs.get("research", {}).get("competitors", [])),
                "report_generated": bool(run_outputs.get("report_path")),
                "reddit_replies_drafted": len(run_outputs.get("reddit", {}).get("replies", [])),
                "reply_sample": [
                    r.get("reply_text", "")[:200]
                    for r in run_outputs.get("reddit", {}).get("replies", [])[:2]
                ],
            },
            indent=2,
        )

        prompt = f"""Here is a summary of the latest marketing agent pipeline run:

{summary}

Please reflect and return JSON with keys:
- "what_worked": list of strings (up to 3 things that seemed effective)
- "what_to_improve": list of strings (up to 3 specific improvements for next run)
- "new_learnings": list of strings (up to 3 concise actionable lessons to remember)
- "run_quality_score": integer 1-10
"""
        reflection = self.llm.chat_json(
            [{"role": "user", "content": prompt}],
            system=REFLECTION_SYSTEM,
            temperature=0.4,
        )

        # Append to persistent memory
        run_record = {
            "timestamp": datetime.now().isoformat(),
            "reflection": reflection,
        }
        self.memory["runs"].append(run_record)

        # Extract new learnings into global pool
        new_learnings = reflection.get("new_learnings", [])
        self.memory["global_learnings"].extend(new_learnings)
        # cap at 20 global learnings to avoid bloat
        self.memory["global_learnings"] = self.memory["global_learnings"][-20:]

        save_memory(self.memory)

        # also dump this run's snapshot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_path = os.path.join(config.OUTPUT_DIR, f"learning_loop_{timestamp}.json")
        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump(run_record, f, indent=2, ensure_ascii=False)

        logger.info("Reflection score: %s/10", reflection.get("run_quality_score", "?"))
        logger.info("=== LearningLoop done ===")
        return reflection
