"""
agents/reddit_agent.py  — Agent 3

1. Searches Reddit for threads where users express pain points that CWT solves.
2. Scores threads by relevance & engagement.
3. Drafts 3–5 authentic, non-spammy replies using the LLM.
4. (Optionally) posts them via PRAW in DRY_RUN=False mode.
"""
import json
import logging
import os
import random
from datetime import datetime
from typing import Any

from tools.apify_tools import scrape_reddit_posts
from tools.reddit_tools import search_subreddit, post_reply
from tools.openrouter_client import OpenRouterClient
import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a helpful Reddit community member who trades actively
and genuinely wants to help others. You occasionally mention tools you've found useful
but never come across as promotional or spammy. You write like a real person — casual,
sometimes with minor typos or abbreviations, never corporate-sounding."""

# How many replies to draft
TARGET_REPLIES = 5


class RedditAgent:
    def __init__(self, llm: OpenRouterClient | None = None):
        self.llm = llm or OpenRouterClient()
        self.memory: dict[str, Any] = {}

    # ── post collection ────────────────────────────────────────────────────────

    def _collect_posts(self) -> list[dict]:
        """Gather candidate Reddit posts across target subreddits."""
        all_posts: list[dict] = []

        for subreddit in config.REDDIT_SUBREDDITS:
            for keyword in random.sample(config.PAIN_KEYWORDS, k=min(3, len(config.PAIN_KEYWORDS))):
                # try PRAW first (lighter), fall back to Apify
                posts = search_subreddit(subreddit, keyword, limit=10)
                if not posts:
                    posts = scrape_reddit_posts(subreddit, keyword, max_posts=10)
                all_posts.extend(posts)
                logger.debug("r/%s + '%s' → %d posts", subreddit, keyword, len(posts))

        # deduplicate by post id
        seen: set[str] = set()
        unique: list[dict] = []
        for p in all_posts:
            pid = p.get("id", p.get("url", ""))
            if pid and pid not in seen:
                seen.add(pid)
                unique.append(p)

        logger.info("Collected %d unique posts across %d subreddits", len(unique), len(config.REDDIT_SUBREDDITS))
        return unique

    # ── relevance scoring ──────────────────────────────────────────────────────

    def _score_post(self, post: dict) -> float:
        """
        Heuristic score: higher = better candidate for a reply.
        Factors: engagement (comments), recency proxy (score), keyword density.
        """
        text = (post.get("title", "") + " " + post.get("selftext", "")).lower()
        pain_keywords = [
            "how do i", "struggling", "anyone know", "help me", "not sure how",
            "confused about", "what's the best", "recommendation", "losing money",
            "can't figure out", "tips", "advice", "where do you", "signal",
            "predict", "edge", "better than", "anyone tried",
        ]
        keyword_hits = sum(1 for kw in pain_keywords if kw in text)
        score = (
            keyword_hits * 3
            + min(post.get("num_comments", 0), 50)
            + min(post.get("score", 0) / 10, 20)
        )
        return score

    # ── reply drafting ─────────────────────────────────────────────────────────

    def _draft_reply(self, post: dict) -> str:
        """Ask the LLM to write a contextual, human-sounding reply."""
        prompt = f"""A Reddit user posted this in r/{post['subreddit']}:

TITLE: {post['title']}
BODY: {post.get('selftext', '(no body)')}

Write a helpful reply from the perspective of an experienced retail trader.
The reply should:
- Directly address their specific question or frustration
- Share a relatable personal experience or opinion
- Naturally mention that you've been using a tool called CrowdWisdomTrading (crowdwisdomtrading.com)
  that aggregates crowd signals — but only if it genuinely fits the context
- Sound like a regular Reddit comment: casual, maybe 3-5 sentences, no bullet points
- NOT start with "I" and NOT use phrases like "Great question!" or "As an AI"
- Feel organic — NOT like a product pitch

Reply:"""

        reply = self.llm.chat(
            [{"role": "user", "content": prompt}],
            system=SYSTEM_PROMPT,
            temperature=0.85,  # higher temp = more human variation
            max_tokens=300,
        )
        return reply.strip()

    # ── main entry point ───────────────────────────────────────────────────────

    def run(self, post_replies: bool = False) -> dict:
        """
        Full Reddit agent cycle.
        Returns a dict with the drafted replies and target post metadata.
        """
        logger.info("=== RedditAgent starting ===")

        posts = self._collect_posts()
        if not posts:
            logger.warning("No posts collected — check API keys and subreddit config.")
            return {"replies": [], "posts_targeted": []}

        # rank and pick the best candidates
        scored = sorted(posts, key=self._score_post, reverse=True)
        candidates = scored[:TARGET_REPLIES * 2]  # small buffer in case some drafts are poor

        drafted_replies: list[dict] = []
        for post in candidates:
            if len(drafted_replies) >= TARGET_REPLIES:
                break

            logger.info("Drafting reply for: %s", post["title"][:80])
            reply_text = self._draft_reply(post)

            result = {
                "post_id": post.get("id", ""),
                "post_title": post["title"],
                "post_url": post.get("permalink", post.get("url", "")),
                "subreddit": post["subreddit"],
                "reply_text": reply_text,
                "relevance_score": self._score_post(post),
            }

            if post_replies:
                post_result = post_reply(post.get("id", ""), reply_text)
                result["post_result"] = post_result

            drafted_replies.append(result)

        # save output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        outfile = os.path.join(config.OUTPUT_DIR, f"reddit_replies_{timestamp}.json")
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(drafted_replies, f, indent=2, ensure_ascii=False)

        logger.info("Reddit replies saved → %s", outfile)
        self.memory["last_replies"] = drafted_replies

        logger.info("=== RedditAgent done. %d replies drafted ===", len(drafted_replies))
        return {"replies": drafted_replies, "output_file": outfile}
