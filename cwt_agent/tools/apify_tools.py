"""
tools/apify_tools.py

Wrappers around Apify actors used in the pipeline:
  - Web scraper (website content)
  - Google search scraper (competitor research)
  - Reddit scraper (pain point discovery)
"""
import logging
import time
from typing import Optional

from apify_client import ApifyClient

import config

logger = logging.getLogger(__name__)
_client = ApifyClient(config.APIFY_API_TOKEN)


def _run_actor(actor_id: str, run_input: dict, timeout_secs: int = 120) -> list[dict]:
    """Run an Apify actor synchronously and return all dataset items."""
    logger.info("Starting Apify actor: %s", actor_id)
    run = _client.actor(actor_id).call(run_input=run_input, timeout_secs=timeout_secs)
    items = list(_client.dataset(run["defaultDatasetId"]).iterate_items())
    logger.info("Actor %s returned %d items", actor_id, len(items))
    return items


def scrape_website(url: str) -> list[dict]:
    """
    Scrape a website using Apify's cheerio-scraper (fast, lightweight).
    Returns a list of page objects with url, title, and text content.
    """
    run_input = {
        "startUrls": [{"url": url}],
        "maxCrawlDepth": 2,
        "maxCrawlPages": 15,
        "pageFunction": """
async function pageFunction(context) {
    const { $, request } = context;
    return {
        url: request.url,
        title: $('title').text().trim(),
        h1: $('h1').map((i, el) => $(el).text().trim()).get().join(' | '),
        text: $('body').text().replace(/\\s+/g, ' ').trim().slice(0, 3000),
    };
}
""",
    }
    try:
        return _run_actor("apify/cheerio-scraper", run_input, timeout_secs=180)
    except Exception as e:
        logger.error("scrape_website failed: %s", e)
        return []


def search_google(query: str, max_results: int = 10) -> list[dict]:
    """
    Use Apify's Google Search Results Scraper to find competitor pages.
    Returns list of {title, url, description} dicts.
    """
    run_input = {
        "queries": query,
        "maxPagesPerQuery": 1,
        "resultsPerPage": max_results,
        "languageCode": "en",
        "countryCode": "us",
    }
    try:
        items = _run_actor("apify/google-search-scraper", run_input, timeout_secs=120)
        results = []
        for item in items:
            for r in item.get("organicResults", []):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "description": r.get("description", ""),
                })
        return results
    except Exception as e:
        logger.error("search_google failed: %s", e)
        return []


def scrape_reddit_posts(
    subreddit: str,
    search_query: str,
    max_posts: int = 20,
) -> list[dict]:
    """
    Search a subreddit for posts matching search_query via Apify's Reddit scraper.
    Returns list of post dicts with id, title, url, selftext, score, num_comments.
    """
    run_input = {
        "startUrls": [
            {"url": f"https://www.reddit.com/r/{subreddit}/search/?q={search_query}&restrict_sr=1&sort=relevance"}
        ],
        "maxPostCount": max_posts,
        "maxComments": 5,
    }
    try:
        items = _run_actor("trudax/reddit-scraper-lite", run_input, timeout_secs=180)
        posts = []
        for item in items:
            if item.get("dataType") == "post":
                posts.append({
                    "id": item.get("id", ""),
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "permalink": "https://www.reddit.com" + item.get("permalink", ""),
                    "selftext": (item.get("selftext") or "")[:1000],
                    "score": item.get("score", 0),
                    "num_comments": item.get("numComments", 0),
                    "subreddit": subreddit,
                })
        return posts
    except Exception as e:
        logger.error("scrape_reddit_posts(%s, %s) failed: %s", subreddit, search_query, e)
        return []
