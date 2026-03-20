import base64
import io
import os
import zipfile

import openai
import requests
from langchain_core.tools import tool

HUB_URL = os.getenv("HUB_URL")
AGENT_API_KEY = os.getenv("AGENT_API_KEY")


@tool
def verify_answer(instructions: list[str]) -> dict:
    """Submit the final drone flight instructions to the hub for verification.

    Args:
        instructions: Non-empty list of instruction strings for the drone.

    Returns:
        The JSON response from the hub.
    """
    payload = {
        "apikey": AGENT_API_KEY,
        "task": "drone",
        "answer": {
            "instructions": instructions,
        },
    }
    print(f">>> [verify_answer] instructions={instructions}")
    response = requests.post(f"{HUB_URL}/verify", json=payload)

    try:
        result = response.json()
    except Exception:
        result = {"error": response.text, "status_code": response.status_code}

    print(f"<<< [verify_answer] {result}")
    return result


@tool
def inspect_drone_documentation() -> str:
    """Fetch the drone HTML documentation and return it in a readable plain-text format.

    Results are cached to drone_docs.md next to this file — subsequent calls read
    from the cache instead of fetching again.

    Returns:
        Plain text content of the drone documentation.
    """
    if os.path.exists(_DRONE_DOCS_CACHE):
        print(f">>> [inspect_drone_documentation] reading from cache {_DRONE_DOCS_CACHE}")
        with open(_DRONE_DOCS_CACHE, "r") as f:
            result = f.read()
        print(f"<<< [inspect_drone_documentation] {len(result)} chars (cached)")
        return result

    print(">>> [inspect_drone_documentation] fetching drone.html")
    response = requests.get(f"{HUB_URL}/dane/drone.html")
    response.raise_for_status()

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["style", "script"]):
            tag.decompose()
        result = soup.get_text(separator="\n", strip=True)
    except ImportError:
        import re
        text = re.sub(r"<style[^>]*>.*?</style>", "", response.text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
        result = re.sub(r"<[^>]+>", "", text)
        result = re.sub(r"\n{3,}", "\n\n", result).strip()

    with open(_DRONE_DOCS_CACHE, "w") as f:
        f.write(result)
    print(f"<<< [inspect_drone_documentation] {len(result)} chars")
    return result


_DRONE_MAP_CACHE = os.path.join(os.path.dirname(__file__), "drone_map.md")
_DRONE_DOCS_CACHE = os.path.join(os.path.dirname(__file__), "drone_docs.md")


@tool
def inspect_drone_map() -> str:
    """Fetch the drone map image and return a grid-based description of each sector.

    Downloads drone.png from the hub, uses vision AI to identify the grid layout,
    and returns a description for every cell in the format:
    COL X ROW Y - <short description>

    Results are cached to drone_map.md next to this file — subsequent calls read
    from the cache instead of calling the vision API again.

    Returns:
        A newline-separated string with one entry per grid sector.
    """
    if os.path.exists(_DRONE_MAP_CACHE):
        print(f">>> [inspect_map] reading from cache {_DRONE_MAP_CACHE}")
        with open(_DRONE_MAP_CACHE, "r") as f:
            result = f.read()
        print(f"<<< [inspect_map] {len(result)} chars (cached)")
        return result

    print(">>> [inspect_map] fetching drone.png")
    response = requests.get(f"{HUB_URL}/data/{AGENT_API_KEY}/drone.png")
    response.raise_for_status()

    image_data = base64.standard_b64encode(response.content).decode("utf-8")

    client = openai.OpenAI()
    message = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_data}",
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "This image is a map divided into a grid of rectangle sectors (split by red lines). "
                            "First determine the grid dimensions (number of columns and rows). "
                            "Then describe each sector in detail — mention terrain type, visible structures, "
                            "water features, vegetation, roads, or any notable landmarks. "
                            "Pay special attention to any dam, reservoir, or water-control structure: "
                            "if you see one, explicitly call it out with the word 'DAM'. "
                            "Output ONLY lines in this exact format, one per sector, no extra text:\n"
                            "COL 1 ROW 1 - <detailed description>\n"
                            "COL 2 ROW 1 - <detailed description>\n"
                            "... and so on, scanning left-to-right, top-to-bottom."
                        ),
                    },
                ],
            }
        ],
    )

    result = message.choices[0].message.content
    with open(_DRONE_MAP_CACHE, "w") as f:
        f.write(result)
    print(f"<<< [inspect_map]\n{result}")
    return result
