import os
import re
from pathlib import Path

import requests
from langchain_core.tools import tool

_writes_dir = Path(__file__).parent.parent / "writes"
_log_path = _writes_dir / "failure.log"


@tool
def download_logs() -> str:
    """
    Download the failure log from the hub and save it locally.
    Must be called before search_logs. Returns the number of lines downloaded.
    """
    hub_url = os.getenv("HUB_URL")
    api_key = os.getenv("AGENT_API_KEY")
    url = f"{hub_url}/data/{api_key}/failure.log"
    print(f"[download_logs] fetching {url}")
    resp = requests.get(url)
    resp.raise_for_status()
    _writes_dir.mkdir(exist_ok=True)
    _log_path.write_text(resp.text)
    line_count = len(resp.text.splitlines())
    print(f"[download_logs] saved {line_count} lines to {_log_path}")
    return f"Downloaded {line_count} lines to {_log_path}"


@tool
def read_file(offset: int = 0, limit: int = 200) -> str:
    """
    Read lines from the downloaded failure log.
    offset: line number to start from (0-indexed, default 0)
    limit: max number of lines to return (default 200)
    Use this to inspect component names present in the log before searching.
    Call repeatedly with increasing offset to page through the file.
    """
    print(f"[read_file] reading {_log_path} offset={offset} limit={limit}")
    lines = _log_path.read_text().splitlines()
    total = len(lines)
    chunk = lines[offset:offset + limit]
    print(f"[read_file] returning lines {offset}-{offset + len(chunk) - 1} of {total}")
    return "\n".join(chunk)


@tool
def merge_logs(dir1: str = "", dir2: str = "") -> str:
    """
    Merge searched log files from up to two directories into a single merged.log.
    dir1: first directory path to read *.log files from (defaults to writes dir)
    dir2: second directory path to read *.log files from (optional)
    Returns the merged content.
    """
    exclude = {"failure.log", "merged.log"}
    dirs = [Path(d) for d in (dir1, dir2) if d] or [_writes_dir]
    parts = []
    for d in dirs:
        for f in sorted(d.glob("*.log")):
            if f.name not in exclude:
                parts.append(f.read_text())
                print(f"[merge_logs] included {f}")
    merged = "\n".join(p.strip() for p in parts if p.strip())
    out = _writes_dir / "merged.log"
    out.write_text(merged)
    line_count = len(merged.splitlines())
    print(f"[merge_logs] wrote {line_count} lines to {out}")
    return merged


@tool
def compress_logs(content: str) -> str:
    """
    Deduplicate log lines by stripping timestamps and removing repeated messages.
    Returns compressed log content with only unique events (preserving original lines).
    """
    seen, result = set(), []
    for line in content.splitlines():
        msg = re.sub(r"^\[.*?\]\s*", "", line)
        if msg and msg not in seen:
            seen.add(msg)
            result.append(line)
    compressed = "\n".join(result)
    print(f"[compress_logs] {len(content.splitlines())} -> {len(result)} lines after dedup")
    return compressed


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
def send_file_to_hub(content: str) -> str:
    """
    Submit log content to the hub for verification.
    content: the log lines to submit (plain text).
    Returns the hub's raw response text.
    """
    hub_url = os.getenv("HUB_URL")
    print(f"[send_file_to_hub] submitting {len(content.splitlines())} lines to {hub_url}/verify")
    resp = requests.post(
        f"{hub_url}/verify",
        json={"apikey": os.getenv("AGENT_API_KEY"), "task": "failure", "answer": {"logs": content}},
    )
    print(f"[send_file_to_hub] status={resp.status_code} response={resp.text[:200]}")
    return resp.text
