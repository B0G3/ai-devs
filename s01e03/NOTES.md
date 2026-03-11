# s01e03 — Logistics Agent

A FastAPI server that acts as a logistics chatbot. The hub connects to it over the internet and runs a multi-turn conversation to test whether the agent can be manipulated into revealing or redirecting packages to unintended destinations.

## How to run

```bash
cd s01e03
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in OPENAI_API_KEY, AGENT_API_KEY, HUB_URL, REACTOR_PARTS_DESTINATION
python main.py         # starts on http://0.0.0.0:8000
```

## Exposing the server with ngrok

The hub needs a publicly reachable URL to POST to. In a separate terminal:

```bash
ngrok http 8000
```

Copy the `https://xxxx-xxxx-xxxx.ngrok-free.app` URL from the ngrok output.

## Registering with the hub

Once the server is running and ngrok is active, POST to `{HUB_URL}/validate`:

```bash
curl -X POST {HUB_URL}/validate \
  -H "Content-Type: application/json" \
  -d '{
    "apikey": "<AGENT_API_KEY>",
    "task": "proxy",
    "answer": {
      "url": "https://<your-ngrok-subdomain>.ngrok-free.app/completion",
      "sessionID": "<any-random-string>"
    }
  }'
```

The hub will then start sending `POST /completion` requests with `{ "sessionID": "...", "msg": "..." }` payloads. The agent replies with `{ "msg": "..." }`.

## Agent design notes

- **System prompt** instructs the agent to behave like a human logistics worker and never reveal the true `REACTOR_PARTS_DESTINATION`.
- **`check_package`** — queries the hub API for package details.
- **`redirect_package`** — redirects a package; if `containsReactorParts=true`, the `RedirectPackageInput` validator silently overrides the destination to `REACTOR_PARTS_DESTINATION` regardless of what the operator requests.
- Session history is kept in memory per `sessionID`, so multi-turn conversations are stateful.
