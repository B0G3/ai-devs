import base64
import io
import os
import zipfile
from typing import Any

import requests
from langchain_core.tools import tool

HUB_URL = os.getenv("HUB_URL")
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
def decode_attachment(data_uri: str) -> dict:
    """Decode a base64 data URI attachment and return its contents.

    Supports ZIP archives (extracts all text files) and plain text/binary data.

    Args:
        data_uri: The full data URI string, e.g. 'data:application/zip;base64,<base64data>'

    Returns:
        A dict with 'files' mapping filename -> text content, or 'error' on failure.
    """
    try:
        if "," not in data_uri:
            return {"error": "Invalid data URI format"}
        header, encoded = data_uri.split(",", 1)
        raw = base64.b64decode(encoded)

        if "zip" in header:
            files = {}
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                for name in zf.namelist():
                    with zf.open(name) as f:
                        try:
                            files[name] = f.read().decode("utf-8")
                        except UnicodeDecodeError:
                            files[name] = f.read().decode("latin-1")
            print(f"[decode_attachment] extracted zip files: {list(files.keys())}")
            return {"files": files}
        else:
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("latin-1")
            print(f"[decode_attachment] decoded text: {text[:200]}")
            return {"files": {"content": text}}
    except Exception as e:
        return {"error": str(e)}


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
