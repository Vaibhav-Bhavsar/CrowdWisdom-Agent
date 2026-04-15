"""
tools/reddit_tools.py

PRAW-based helpers for reading Reddit data and (optionally) posting replies.
Posting is gated behind a DRY_RUN flag — set to False when ready to go live.
"""
import logging
import time
import random

import praw

import config

logger = logging.getLogger(__name__)

# Set to True while testing — replies are logged but not actually posted
DRY_RUN = True

_reddit: praw.Reddit | None = None


def get_reddit() -> praw.Reddit:
    global _reddit
    if _reddit is None:
        _reddit = praw.Reddit(
            client_id=config.REDDIT_CLIENT_ID,
            client_secret=config.REDDIT_CLIENT_SECRET,
            user_agent=config.REDDIT_USER_AGENT,
            # add username/password here if you need to post
            # username="your_username",
            # password="your_password",
        )
    return _reddit


def search_subreddit(subreddit_name: str, query: str, limit: int = 15) -> list[dict]:
    """Search a subreddit and return matching posts."""
    reddit = get_reddit()
    try:
        sub = reddit.subreddit(subreddit_name)
        posts = []
        for post in sub.search(query, limit=limit, sort="relevance", time_filter="year"):
            posts.append({
                "id": post.id,
                "title": post.title,
                "url": post.url,
                "permalink": f"https://www.reddit.com{post.permalink}",
                "selftext": post.selftext[:800],
                "score": post.score,
                "num_comments": post.num_comments,
                "subreddit": subreddit_name,
                "author": str(post.author),
            })
        return posts
    except Exception as e:
        logger.error("search_subreddit(%s, %s) failed: %s", subreddit_name, query, e)
        return []


def post_reply(post_id: str, reply_text: str) -> dict:
    """
    Post a reply to a Reddit thread.
    In DRY_RUN mode this just logs and returns a simulated result.
    """
    if DRY_RUN:
        logger.info("[DRY RUN] Would post to %s:\n%s", post_id, reply_text)
        return {"status": "dry_run", "post_id": post_id, "reply": reply_text}

    reddit = get_reddit()
    try:
        submission = reddit.submission(id=post_id)
        comment = submission.reply(reply_text)
        # small random delay to look human
        time.sleep(random.uniform(8, 20))
        return {"status": "posted", "comment_id": comment.id, "post_id": post_id}
    except Exception as e:
        logger.error("post_reply(%s) failed: %s", post_id, e)
        return {"status": "error", "error": str(e), "post_id": post_id}
