"""
agents/product_researcher.py  — Agent 1

Responsibilities:
  1. Scrape the CWT website to understand the product.
  2. Run Google searches to find direct competitors in prediction markets.
  3. Scrape each competitor's homepage for a summary.
  4. Return a structured dict ready for the report agent.
"""
import logging
from typing import Any

from tools.apify_tools import scrape_website, search_google
from tools.openrouter_client import OpenRouterClient
import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a product research analyst specializing in fintech and prediction markets.
Given raw website text, extract a clean, structured summary. Be concise and factual."""


class ProductResearcherAgent:
    def __init__(self, llm: OpenRouterClient | None = None):
        self.llm = llm or OpenRouterClient()
        self.memory: dict[str, Any] = {}  # simple in-process memory for learning loop

    # ── helpers ────────────────────────────────────────────────────────────────

    def _summarize_site(self, pages: list[dict], site_name: str) -> dict:
        """Ask the LLM to distill raw scraped pages into a product summary."""
        if not pages:
            return {"name": site_name, "summary": "No data scraped.", "features": [], "pricing": "unknown"}

        combined_text = "\n\n".join(
            f"[{p['url']}]\n{p.get('title', '')}\n{p.get('text', '')}" for p in pages[:5]
        )[:4000]

        prompt = f"""Here is scraped content from {site_name}:

{combined_text}

Return JSON with keys:
- name (string)
- tagline (string, one sentence)
- summary (string, 2-3 sentences)
- features (list of strings, up to 6 key features)
- target_audience (string)
- pricing (string, e.g. "free", "subscription", "unknown")
- unique_value_prop (string)
"""
        return self.llm.chat_json(
            [{"role": "user", "content": prompt}],
            system=SYSTEM_PROMPT,
            temperature=0.3,
        )

    # ── main entry point ───────────────────────────────────────────────────────

    def run(self) -> dict:
        """
        Full research cycle. Returns a dict with:
          - product: CWT product summary
          - competitors: list of competitor summaries
          - competitor_urls: raw search results
        """
        logger.info("=== ProductResearcherAgent starting ===")

        # 1. Scrape CWT itself
        logger.info("Scraping CWT website: %s", config.CWT_URL)
        cwt_pages = scrape_website(config.CWT_URL)
        cwt_summary = self._summarize_site(cwt_pages, config.CWT_NAME)
        logger.info("CWT summary generated: %s", cwt_summary.get("tagline", ""))

        # 2. Search for competitors
        queries = [
            "prediction markets trading platform site",
            "crowd wisdom stock prediction platform",
            "collective intelligence trading signals app",
            "retail trader prediction market tool 2024",
        ]
        all_search_results: list[dict] = []
        for q in queries:
            results = search_google(q, max_results=8)
            all_search_results.extend(results)
            logger.info("Query '%s' → %d results", q, len(results))

        # Deduplicate by URL and exclude CWT itself
        seen_urls: set[str] = {config.CWT_URL}
        competitor_urls: list[dict] = []
        for r in all_search_results:
            url = r.get("url", "")
            if url and url not in seen_urls and "reddit" not in url:
                seen_urls.add(url)
                competitor_urls.append(r)

        # Keep top 6 by relevance (order preserved from search)
        top_competitors = competitor_urls[:6]
        logger.info("Identified %d unique competitor URLs to scrape", len(top_competitors))

        # 3. Scrape and summarize each competitor
        competitor_summaries = []
        for comp in top_competitors:
            url = comp["url"]
            logger.info("Scraping competitor: %s", url)
            pages = scrape_website(url)
            summary = self._summarize_site(pages, comp.get("title", url))
            summary["source_url"] = url
            competitor_summaries.append(summary)

        result = {
            "product": cwt_summary,
            "competitors": competitor_summaries,
            "raw_search_results": top_competitors,
        }

        # store in memory for learning loop
        self.memory["last_research"] = result
        logger.info("=== ProductResearcherAgent done. %d competitors profiled ===", len(competitor_summaries))
        return result
