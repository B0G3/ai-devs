# AI Agents Course

A hands-on course for building AI agents. Each task is a standalone Python project with its own virtual environment and dependencies.

## Project Structure

```
AIdevs/
├── Agents.md         # This file
├── s01e01/           # Season 1, Episode 1
├── s01e02/           # Season 1, Episode 2
└── ...
```

## Task Index

| Task    | Title                        | Topics                              |
|---------|------------------------------|-------------------------------------|
| s01e01  | People Classifier            | Load a CSV, filter by gender/age/city, classify jobs with OpenAI structured output (Instructor + Pydantic), POST results to a verification hub |
| s01e02  | Find Him                     | Fetch power plant locations from hub, resolve city coordinates via OpenAI, compute haversine distances, fetch person locations and access levels from hub API, submit closest high-access candidate |
| s01e03  | Logistics Agent              | FastAPI server exposing `/completion` endpoint, LangChain agent with tool use (check/redirect packages), session-based conversation history, covert destination override via Pydantic model validator; expose via ngrok and register URL with hub `/validate` |
| s01e04  | Parcel Declaration Generator | Fetch a multi-file document index from hub, resolve `[include file="..."]` directives (Markdown fetched as text, PNG fetched and OCR'd via GPT-4o vision), assemble into one complete doc, use it as system prompt to generate a formatted customs declaration for a fictional parcel, POST answer to hub |
| s01e05  | Railway Route Agent          | LangChain agent with two tools (`get_route_status`, `set_route_status`) that call hub `/verify` with structured action payloads; agent must check status, reconfigure, set status to RTOPEN, and save route X-01; flag is returned in the final assistant message |

## Setup Convention

Each task follows the same pattern:

```bash
cd sXXeYY
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # fill in your keys
python main.py
```

## Environment Variables

Each task uses a local `.env` file (never committed). Copy `.env.example` and fill in values.

Common keys:
- `OPENAI_API_KEY` — your OpenAI API key
- `AGENT_API_KEY` — API key for the verification hub
- `HUB_URL` — verification hub endpoint (e.g. `/verify`)
