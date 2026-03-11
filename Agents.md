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
- `HUB_URL` — verification hub endpoint (e.g. `https://hub.ag3nts.org/verify`)
