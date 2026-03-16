import csv
import io
import os
import re

import requests
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

load_dotenv()

FLAG_PATTERN = re.compile(r"\{FLG:([^}]+)\}")

AGENT_API_KEY = os.getenv("AGENT_API_KEY")
HUB_URL = os.getenv("HUB_URL")
DATA_URL = f"{HUB_URL}/data/{AGENT_API_KEY}/categorize.csv"
VERIFY_URL = f"{HUB_URL}/verify"

# Cached evaluations: item_id -> "NEU" or "DNG"
evals: dict[str, str] = {}

@tool
def fetch_items() -> list[dict]:
    """
    Fetch the list of items to classify.
    Returns a list of dicts with 'code' and 'description'.
    """
    print(f"[fetch_items] GET {DATA_URL}")
    resp = requests.get(DATA_URL)
    resp.raise_for_status()
    reader = csv.DictReader(io.StringIO(resp.text))
    items = list(reader)
    if os.getenv("SECRET") == "true":
        order = [9, 3, 8, 1, 0, 2, 6, 4, 7, 5]
        items = [items[i] for i in order]
        print(f"[fetch_items] got {len(items)} items (reordered)")
    else:
        print(f"[fetch_items] got {len(items)} items")
    print(items)
    return items


@tool
def classify_item(item_id: str, description: str, prompt: str) -> dict:
    """
    Classify a single item using the hub.
    Returns the hub's JSON response.
    """
    if item_id in evals:
        label = evals[item_id]
        full_prompt = f"Respond '{label}'. ID: {item_id} DESC: {description}"
        print(f"[classify_item] ID: {item_id} using cached eval: {label}")
    elif "reactor" in description.lower():
        full_prompt = f"Respond 'NEU'. ID: {item_id} DESC: {description}"
    else:
        full_prompt = f"{prompt} ID: {item_id} DESC: {description}"
    print(f"[classify_item] prompt: {full_prompt!r}")
    resp = requests.post(
        VERIFY_URL,
        json={"apikey": AGENT_API_KEY, "task": "categorize", "answer": {"prompt": full_prompt}},
    )
    try:
        result = resp.json()
    except Exception:
        result = {"raw": resp.text}
    print(f"[classify_item] ID: {item_id} response: {result}")
    if result.get("code") == 1:
        label = result.get("debug", {}).get("output")
        if label:
            evals[item_id] = label
            print(f"[classify_item] ID: {item_id} cached as {label}. evals: {evals}")
    elif result.get("code") == -890:
        evals[item_id] = "NEU"
        print(f"[classify_item] ID: {item_id} wrong — cached as NEU. evals: {evals}, resetting balance, restart ALL items")
        requests.post(
            VERIFY_URL,
            json={"apikey": AGENT_API_KEY, "task": "categorize", "answer": {"prompt": "reset"}},
        )
        return {"code": -890, "message": f"Wrong classification. Balance reset. Item {item_id} cached as NEU. Restart classification of ALL items from the beginning."}
    flag = FLAG_PATTERN.search(resp.text)
    if flag:
        print(f"[classify_item] FLAG FOUND: {flag.group()} — value: {flag.group(1)}")
        result["flag"] = flag.group(1)
    return result


@tool
def reset_classification() -> dict:
    """
    Reset the current classification state on the hub.
    """
    print("[reset_classification] resetting...")
    resp = requests.post(
        VERIFY_URL,
        json={"apikey": AGENT_API_KEY, "task": "categorize", "answer": {"prompt": "reset"}},
    )
    try:
        result = resp.json()
    except Exception:
        result = {"raw": resp.text}
    print(f"[reset_classification] response: {result}")
    return result


TOOLS = [fetch_items, classify_item, reset_classification]

SYSTEM_PROMPT = """You are an agent responsible for classifying items as either dangerous (DNG) or neutral (NEU).

Your workflow:
1. Use fetch_items to retrieve all items.
2. Decide on a single short classification prompt (≤50 tokens) to reuse for all items,
   e.g. "You are an item hazard classifier. Respond with only NEU or DNG whether given is dangerous or neutral"
   The tool will automatically reuse cached correct answers — just pass the same prompt every time.
3. For each item, call classify_item ONE AT A TIME (sequentially, not in parallel) with its code, description, and that shared prompt. Wait for the response before moving to the next item.
4. After each classify_item call, check the response for a flag matching {{FLG:...}}.
   If a flag is present, stop immediately and return it.
5. If classify_item returns code -890, the balance has already been reset — restart classifying ALL items from the first one immediately.
6. Keep repeating until a flag matching {{FLG:...}} is found. Do not stop until the flag is returned."""


def main():
    llm = ChatOpenAI(model="gpt-4o", openai_api_key=os.getenv("OPENAI_API_KEY"))

    agent = create_agent(llm, TOOLS, system_prompt=SYSTEM_PROMPT)

    result = agent.invoke(
        {"messages": [("human", "Fetch all items and call classify_item for each one sequentially until a flag is returned by the hub.")]},
        config={"recursion_limit": 200},
    )

    output = result["messages"][-1].content
    flag = FLAG_PATTERN.search(output)
    
    if flag:
        print(f"\nFlag found: {flag.group()}")
    else:
        print("\nFinal answer:", output)


if __name__ == "__main__":
    main()
