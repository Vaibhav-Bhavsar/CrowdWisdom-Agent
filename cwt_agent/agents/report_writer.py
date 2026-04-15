"""
agents/report_writer.py  — Agent 2

Takes the structured research output from Agent 1 and produces a
polished Markdown competitive analysis report.
"""
import logging
import os
from datetime import datetime

from tools.openrouter_client import OpenRouterClient
import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior product marketing strategist.
Write clear, data-driven competitive analysis reports in Markdown.
Be direct and actionable. Avoid fluff."""


class ReportWriterAgent:
    def __init__(self, llm: OpenRouterClient | None = None):
        self.llm = llm or OpenRouterClient()

    def _build_prompt(self, research: dict) -> str:
        product = research.get("product", {})
        competitors = research.get("competitors", [])

        comp_section = ""
        for i, c in enumerate(competitors, 1):
            comp_section += f"""
### Competitor {i}: {c.get('name', 'Unknown')}
- **URL**: {c.get('source_url', 'N/A')}
- **Tagline**: {c.get('tagline', 'N/A')}
- **Summary**: {c.get('summary', 'N/A')}
- **Key Features**: {', '.join(c.get('features', []))}
- **Target Audience**: {c.get('target_audience', 'N/A')}
- **Pricing**: {c.get('pricing', 'N/A')}
- **UVP**: {c.get('unique_value_prop', 'N/A')}
"""

        return f"""
Here is research data for a competitive analysis:

## OUR PRODUCT — {product.get('name', 'CrowdWisdomTrading')}
- **Tagline**: {product.get('tagline', '')}
- **Summary**: {product.get('summary', '')}
- **Key Features**: {', '.join(product.get('features', []))}
- **Target Audience**: {product.get('target_audience', '')}
- **Pricing**: {product.get('pricing', '')}
- **UVP**: {product.get('unique_value_prop', '')}

## COMPETITORS
{comp_section}

Write a comprehensive competitive analysis Markdown report with these sections:
1. Executive Summary
2. Product Overview (CrowdWisdomTrading)
3. Competitive Landscape (table + narrative per competitor)
4. Strengths & Differentiators (CWT vs field)
5. Gaps & Opportunities
6. Recommended Positioning Statement
7. Go-to-Market Suggestions

Use real Markdown headers, bullet points, and a comparison table.
"""

    def run(self, research: dict) -> str:
        """Generate and save the competitive report. Returns the file path."""
        logger.info("=== ReportWriterAgent starting ===")

        prompt = self._build_prompt(research)
        report_md = self.llm.chat(
            [{"role": "user", "content": prompt}],
            system=SYSTEM_PROMPT,
            temperature=0.5,
            max_tokens=2500,
        )

        # Save to outputs/
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"competitor_report_{timestamp}.md"
        filepath = os.path.join(config.OUTPUT_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report_md)

        logger.info("Report saved → %s", filepath)
        logger.info("=== ReportWriterAgent done ===")
        return filepath
