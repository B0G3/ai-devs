import os
from pathlib import Path

import requests
from langchain_core.tools import tool

_writes_dir = Path(__file__).parent.parent / "writes"
_log_path = _writes_dir / "failure.log"


@tool
def search_logs(severity: str, component: str) -> str:
    """
    Search the failure log for lines matching a given severity level and component name.
    severity: one of INFO, WARN, ERRO, CRIT
    component: component/device name substring to match (e.g. WTRPMP, COOLSYS)
    Returns matching log lines as a string.
    """
    print(f"[search_logs] severity={severity!r} component={component!r}")
    lines = _log_path.read_text().splitlines()
    tag = f"[{severity}]"
    matches = [l for l in lines if tag in l and component in l]
    print(f"[search_logs] {len(matches)} matching lines")
    if not matches:
        return f"No lines found for severity={severity} component={component}"
    result = "\n".join(matches)
    out_file = _writes_dir / f"{severity}_{component}.log"
    out_file.write_text(result)
    print(f"[search_logs] wrote results to {out_file}")
    return result


@tool
def send_to_hub(content: str) -> str:
    """
    Submit log content to the hub for verification.
    content: the log lines to submit (plain text).
    Returns the hub's raw response text.
    """
    hub_url = os.getenv("HUB_URL", "")
    print(f"[send_to_hub] submitting {len(content.splitlines())} lines to {hub_url}/verify")
    resp = requests.post(
        f"{hub_url}/verify",
        json={"apikey": os.getenv("AGENT_API_KEY"), "task": "failure", "answer": {"logs": content}},
    )
    print(f"[send_to_hub] status={resp.status_code} response={resp.text[:200]}")
    return resp.text
