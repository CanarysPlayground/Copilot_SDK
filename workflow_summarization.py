import argparse
import asyncio
import io
import json
import os
import urllib.request
import zipfile

from copilot import CopilotClient


def github_json(url: str, token: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "copilot-sdk-summarizer",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def github_bytes(url: str, token: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "copilot-sdk-summarizer",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def get_workflow_id(owner: str, repo: str, token: str, workflow_name: str) -> int:
    data = github_json(
        f"https://api.github.com/repos/{owner}/{repo}/actions/workflows",
        token,
    )
    for wf in data.get("workflows", []):
        if wf.get("name") == workflow_name:
            return wf.get("id")
    raise RuntimeError(f"Workflow not found: {workflow_name}")


def get_latest_run_id(owner: str, repo: str, token: str, workflow_id: int) -> int:
    data = github_json(
        f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs?per_page=1",
        token,
    )
    runs = data.get("workflow_runs", [])
    if not runs:
        raise RuntimeError("No workflow runs found.")
    return runs[0].get("id")


def download_run_logs(owner: str, repo: str, token: str, run_id: int) -> str:
    log_zip = github_bytes(
        f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/logs",
        token,
    )
    text_parts = []
    with zipfile.ZipFile(io.BytesIO(log_zip)) as zf:
        for name in sorted(zf.namelist()):
            content = zf.read(name).decode("utf-8", errors="ignore")
            text_parts.append(f"## {name}\n{content}")
    return "\n\n".join(text_parts)


def trim_text(text: str, max_chars: int = 120000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[truncated]\n"


async def summarize_logs_with_copilot(log_text: str) -> str:
    client = CopilotClient()
    await client.start()

    session = await client.create_session({
        "model": "gpt-4.1",
        "streaming": False,
    })

    prompt = (
        "Summarize these GitHub Actions run logs in 6-8 bullets. "
        "Focus on failures, self-heal behavior, and any PR creation. "
        "Include the key steps and outcomes.\n\n"
        f"{log_text}"
    )

    response = await session.send_and_wait({"prompt": prompt})
    await client.stop()

    return extract_copilot_content(response)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner", default=os.getenv("GITHUB_OWNER", "CanarysPlayground"))
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPO", "Copilot_SDK"))
    parser.add_argument("--workflow-name", default=os.getenv("WORKFLOW_NAME", "Self-Healing Workflow"))
    parser.add_argument("--run-id", type=int, default=None)
    args = parser.parse_args()

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not set.")

    if args.run_id is None:
        workflow_id = get_workflow_id(args.owner, args.repo, token, args.workflow_name)
        run_id = get_latest_run_id(args.owner, args.repo, token, workflow_id)
    else:
        run_id = args.run_id

    logs = download_run_logs(args.owner, args.repo, token, run_id)
    logs = trim_text(logs)

    summary = await summarize_logs_with_copilot(logs)
    print(summary)


if __name__ == "__main__":
    asyncio.run(main())