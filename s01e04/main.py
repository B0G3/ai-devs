import base64
import os
import re
from datetime import date

import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

DIR = os.path.dirname(__file__)
INDEX_URL = f"{os.getenv('HUB_URL')}/dane/doc/index.md"
INCLUDE_RE = re.compile(r'\[include file="([^"]+)"\]')
COMPLETE_PATH = os.path.join(DIR, "complete.md")
PARCEL_PATH = os.path.join(DIR, "parcel.md")


def fetch_index() -> str:
    resp = requests.get(INDEX_URL)
    resp.raise_for_status()
    return resp.text


def extract_includes(content: str) -> list[str]:
    return INCLUDE_RE.findall(content)


def fetch_md(filename: str) -> str:
    url = f"{os.getenv('HUB_URL')}/dane/doc/{filename}"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.text


def fetch_png_as_text(filename: str) -> str:
    url = f"{os.getenv('HUB_URL')}/dane/doc/{filename}"
    resp = requests.get(url)
    resp.raise_for_status()
    b64 = base64.b64encode(resp.content).decode()

    llm = ChatOpenAI(model="gpt-4o", openai_api_key=os.getenv("OPENAI_API_KEY"))
    msg = HumanMessage(content=[
        {"type": "text", "text": "Extract all text and meaningful information from this image. Return plain text only."},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
    ])
    return llm.invoke([msg]).content


def resolve_file(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    print(f"      → resolving {filename} ({ext})")
    if ext == "md":
        return fetch_md(filename)
    elif ext == "png":
        return fetch_png_as_text(filename)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def build_complete(index: str) -> str:
    def replacer(match: re.Match) -> str:
        return resolve_file(match.group(1))

    return INCLUDE_RE.sub(replacer, index)


def generate_declaration(instructions: str, parcel: str) -> str:
    llm = ChatOpenAI(model="gpt-4o", openai_api_key=os.getenv("OPENAI_API_KEY"))
    messages = [
        SystemMessage(content=instructions),
        HumanMessage(content=f"Dzisiejsza data: {date.today().isoformat()}\n\nBiorąc pod uwagę zmyślone dane przesyłki:\n\n{parcel}\n\nWygeneruj deklarację dokładnie jak we wskazanym wzorze - zachowaj format 1:1, zamień nawiasy kwadratowe na faktyczne wartości."),
    ]
    return llm.invoke(messages).content


def main():
    # Step 3 — build complete.md (skip if already exists)
    if os.path.exists(COMPLETE_PATH):
        print("[3/6] complete.md already exists, skipping extraction.")
        with open(COMPLETE_PATH, encoding="utf-8") as f:
            complete = f.read()
    else:
        print("[1/3] Fetching index...")
        index = fetch_index()

        print("[2/3] Extracting includes...")
        includes = extract_includes(index)
        print(f"      → {len(includes)} include(s) found: {includes}")

        print("[3/3] Resolving and assembling complete.md...")
        complete = build_complete(index)
        with open(COMPLETE_PATH, "w", encoding="utf-8") as f:
            f.write(complete)
        print(f"      → written to {COMPLETE_PATH}")

    # Step 4 — load parcel data
    print("[4/6] Loading parcel data...")
    with open(PARCEL_PATH, encoding="utf-8") as f:
        parcel = f.read()

    # Step 5 — generate declaration
    print("[5/6] Generating declaration...")
    declaration = generate_declaration(complete, parcel)
    print(f"      → declaration:\n{declaration}")

    # Step 6 — send to hub
    print("[6/6] Sending declaration to hub...")
    payload = {
        "apikey": os.getenv("AGENT_API_KEY"),
        "task": "sendit",
        "answer": {"declaration": declaration},
    }
    resp = requests.post(f"{os.getenv('HUB_URL')}/verify", json=payload)
    print(f"      → {resp.status_code}: {resp.json()}")


if __name__ == "__main__":
    main()
