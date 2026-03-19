import os
import re
import time

import requests
from dotenv import load_dotenv
from langchain_core.tools import tool

from .image_utils import prepare_image, interpret_circuit_image

load_dotenv()

FLAG_PATTERN = re.compile(r"\{FLG:([^}]+)\}")
TARGET_IMAGE_URL = os.getenv("TARGET_IMAGE_URL")


def _get_with_retry(url: str) -> requests.Response:
    """GET with exponential backoff on 429."""
    delay = 5
    for attempt in range(5):
        resp = requests.get(url)
        if resp.status_code != 429:
            resp.raise_for_status()
            return resp
        print(f"[retry] 429 received, waiting {delay}s (attempt {attempt + 1})")
        time.sleep(delay)
        delay *= 2
    resp.raise_for_status()
    return resp


def _image_url() -> str:
    return f"{os.getenv('HUB_URL')}/data/{os.getenv('AGENT_API_KEY')}/electricity.png"


def _verify_url() -> str:
    return f"{os.getenv('HUB_URL')}/verify"


@tool
def show_circuits() -> dict:
    """
    Fetch the circuit image from the hub and interpret it as a 3x3 grid of cells.
    Each cell is itself a 3x3 binary matrix where X=filled, o=empty.
    Returns a structured text representation of the full grid.
    """
    url = _image_url()
    print(f"[show_circuits] GET {url}")
    resp = _get_with_retry(url)
    raw_img = prepare_image(resp.content)
    result = interpret_circuit_image(raw_img)
    print(f"[show_circuits] matrix:\n{result['full_grid']}")
    return result


@tool
def rotate_circuit(field: str) -> dict:
    """
    Rotate a single circuit cell by sending a rotate request to the hub.
    field must be in RxC format, e.g. "2x3".
    Returns the hub's JSON response.
    """
    print(f"[rotate_circuit] rotating field {field}")
    resp = requests.post(
        _verify_url(),
        json={"apikey": os.getenv("AGENT_API_KEY"), "task": "electricity", "answer": {"rotate": field}},
    )
    try:
        result = resp.json()
    except Exception:
        result = {"raw": resp.text}
    flag = FLAG_PATTERN.search(resp.text)
    if flag:
        print(f"[rotate_circuit] FLAG FOUND: {flag.group()}")
        result["flag"] = flag.group(1)
    print(f"[rotate_circuit] response: {result}")
    return result


_target_cache: dict | None = None


@tool
def show_target_circuits() -> dict:
    """
    Fetch the target/solved circuit image and interpret it as a 3x3 grid of cells.
    Each cell is itself a 3x3 binary matrix where X=filled, o=empty.
    Returns the expected final state of the circuits.
    """
    global _target_cache
    if _target_cache is not None:
        print("[show_target_circuits] returning cached result")
        return _target_cache
    print(f"[show_target_circuits] GET {TARGET_IMAGE_URL}")
    resp = _get_with_retry(TARGET_IMAGE_URL)
    raw_img = prepare_image(resp.content)
    _target_cache = interpret_circuit_image(raw_img)
    print(f"[show_target_circuits] matrix:\n{_target_cache['full_grid']}")
    return _target_cache
