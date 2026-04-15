# CrowdWisdomTrading – Product Marketing Agent

A multi-agent pipeline built for the CWT internship assessment. The system researches the product, analyzes competitors, scrapes Reddit pain points, and drafts authentic reply posts — all in one automated flow.

## What It Does

1. **Product & Competitor Agent** — Scrapes the CWT website and searches for direct competitors in prediction markets using Apify.
2. **Report Agent** — Synthesizes the gathered data into a structured competitive analysis report.
3. **Reddit Pain Finder Agent** — Searches Reddit for users complaining about problems CWT solves; drafts 3–5 human-sounding replies.
4. **Closed Learning Loop** — Built on Hermes Agent's native reflection/memory tooling; each run feeds back into the next.

## Stack

| Layer | Tool |
|---|---|
| Agent framework | [Hermes Agent](https://github.com/nousresearch/hermes-agent) |
| LLM | OpenRouter → `mistralai/mistral-7b-instruct:free` |
| Web scraping | [Apify](https://apify.com) |
| Reddit API | PRAW (read) + Apify Reddit scraper (write simulation) |
| Storage | Local JSON + rotating log files |

## Setup

```bash
git clone <your-repo-url>
cd cwt_agent
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# fill in your keys in .env
python main.py
```

## Environment Variables

```
OPENROUTER_API_KEY=sk-or-...
APIFY_API_TOKEN=apify_api_...
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=cwt_agent/1.0
```

## Output

All outputs land in `outputs/`:
- `competitor_report_<timestamp>.md` — full competitive analysis
- `reddit_replies_<timestamp>.json` — the 3–5 drafted Reddit replies with target thread links
- `learning_loop_<timestamp>.json` — agent reflection / memory snapshot

## Project Structure

```
cwt_agent/
├── agents/
│   ├── product_researcher.py   # Agent 1 – product & competitor search
│   ├── report_writer.py        # Agent 2 – competitive report
│   ├── reddit_agent.py         # Agent 3 – Reddit pain finder + reply drafter
│   └── learning_loop.py        # Closed learning loop wrapper
├── tools/
│   ├── apify_tools.py          # Apify actor wrappers
│   ├── openrouter_client.py    # LLM client (OpenRouter)
│   └── reddit_tools.py         # PRAW helpers
├── outputs/                    # Generated reports & replies
├── logs/                       # Rotating log files
├── main.py                     # Entry point
├── config.py                   # Config / env loading
├── requirements.txt
├── .env.example
└── README.md
```

## Notes

- Reddit replies are drafted to sound organic — short, conversational, no promotional links dropped cold.
- The agent deliberately spaces out "engagement" to avoid spam signals.
- Learning loop stores structured feedback after each run so the next run can reference what worked.
