import json
import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from tools import TOOLS

load_dotenv()

HUB_URL = os.getenv("HUB_URL", "")
AGENT_API_KEY = os.getenv("AGENT_API_KEY")

LOG_URL = f"{HUB_URL}/data/{AGENT_API_KEY}/failure.log"

_writes_dir = Path(__file__).parent / "writes"

FLAG_PATTERN = re.compile(r"\{FLG:([^}]+)\}")

_CRIT_COMPONENTS = re.compile(r"WTRPMP|STMTURB12|WTANK07|PWR01|WSTPOOL2|FIRMWARE")

VERIFY_URL = f"{HUB_URL}/verify"

def solve_manually():
    response = requests.get(LOG_URL)
    response.raise_for_status()
    _writes_dir.mkdir(exist_ok=True)
    all_lines = response.text.splitlines()
    seen, filtered = set(), []
    for l in all_lines:
        if "[CRIT]" not in l or not _CRIT_COMPONENTS.search(l):
            continue
        msg = re.sub(r"^\[.*?\]\s*", "", l)  # strip timestamp
        if msg not in seen:
            seen.add(msg)
            filtered.append(l)
    log_path = _writes_dir / "failure_log_complete.log"
    log_path.write_text("\n".join(filtered) + "\n")
    logs_str = "\n".join(filtered)
    json_path = _writes_dir / "failure_log_complete.json"
    json_path.write_text(json.dumps(logs_str))
    print(f"[solve_manually] saved {len(filtered)}/{len(all_lines)} lines to {log_path} and {json_path}")

    payload = {"apikey": AGENT_API_KEY, "task": "failure", "answer": {"logs": logs_str}}
    resp = requests.post(VERIFY_URL, json=payload)
    print(f"[solve_manually] POST {VERIFY_URL} -> {resp.status_code}")
    print(resp.text)
    flag = FLAG_PATTERN.search(resp.text)
    if flag:
        print(f"\nFlag found: {flag.group()}")


def main():
    solve_manually()

#     system_prompt = """You are analysing a power-plant failure log to find the root cause of an incident.

# STEP 1: Call search_logs(severity="CRIT", component="WTRPMP") to get critical water-pump events.
# STEP 2: Call send_to_hub with the results.
# STEP 3: Read the hub response carefully. If it mentions additional component names, call
#         search_logs for each one (use severity="CRIT" first, or "ERRO"/"WARN" if no CRIT results)
#         and send_to_hub with the combined results from ALL components the hub has ever mentioned.
#         Keep track of ALL components mentioned across responses — never drop one.
# STEP 4: Repeat until the hub returns a {FLG:...} flag.
# """

#     llm = ChatOpenAI(model="gpt-4o", openai_api_key=os.getenv("OPENAI_API_KEY"), max_tokens=4096)
#     agent = create_agent(llm, TOOLS, system_prompt=system_prompt)

#     result = agent.invoke(
#         {"messages": [("human",
#             "Analyse the failure log and produce a condensed version containing only events relevant. "
#             "Submit it to the hub using submit_logs_from_file_to_hub. If the hub does not return a flag, "
#             "adjust the log and resubmit until you receive a {FLG:...} flag in the response."
#         )]},
#         # config={"recursion_limit": 200},
#     )

#     output = result["messages"][-1].content
#     flag = FLAG_PATTERN.search(output)

#     if flag:
#         print(f"\nFlag found: {flag.group()}")
#     else:
#         print("\nAgent analysis:\n", output)


if __name__ == "__main__":
    main()
