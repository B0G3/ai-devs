import os
from typing import Any

import requests
from langchain_core.tools import tool

HUB_URL = os.getenv("HUB_URL", "")
AGENT_API_KEY = os.getenv("AGENT_API_KEY")


@tool
def verify_answer(password: str, date: str, confirmation_code: str) -> dict:
    """Submit the final answer to the hub for verification.

    Args:
        password: The employee system password found in the mailbox.
        date: The attack date in YYYY-MM-DD format.
        confirmation_code: The SEC- confirmation code (36 chars total).

    Returns:
        The JSON response from the hub.
    """
    payload = {
        "apikey": AGENT_API_KEY,
        "task": "mailbox",
        "answer": {
            "password": password,
            "date": date,
            "confirmation_code": confirmation_code,
        },
    }
    response = requests.post(f"{HUB_URL}/verify", json=payload)

    try:
        result = response.json()
    except Exception:
        result = {"error": response.text, "status_code": response.status_code}

    print(f"<<< [verify_answer] {result}")
    return result


@tool
def call_api_action(action: str, params: dict[str, Any] | None = None) -> dict:
    """Call an action on the zmail API at the hub.

    Args:
        action: The action to perform: 'help', 'getInbox', 'getThread', 'getMessages', 'search', 'reset'.
        params: Optional dict of extra parameters, e.g. {"query": "...", "threadID": 123, "ids": [...], "page": 1, "perPage": 5}.

    Returns:
        The JSON response from the API.
    """
    extras = params or {}
    print(f">>> [call_api_action][{action}] kwargs={extras}")
    payload = {"apikey": AGENT_API_KEY, "action": action, **extras}
    response = requests.post(f"{HUB_URL}/api/zmail", json=payload)

    try:
        result = response.json()
    except Exception:
        result = {"error": response.text, "status_code": response.status_code}
 
    print(f"<<< [call_api_action][{action}] {result}")
    return result
