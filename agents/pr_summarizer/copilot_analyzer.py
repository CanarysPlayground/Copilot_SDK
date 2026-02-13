import logging
from typing import Dict, List

from copilot import CopilotClient

from .config import settings

logger = logging.getLogger(__name__)


class CopilotAnalyzer:
    """Copilot SDK-powered PR analyzer."""

    def __init__(self) -> None:
        self.model = settings.copilot_model

    async def analyze_pr_with_copilot(
        self,
        pr_title: str,
        pr_body: str,
        files_changed: List[Dict],
        diff: str,
    ) -> str:
        prompt = self._build_prompt(pr_title, pr_body, files_changed, diff)

        client = CopilotClient()
        await client.start()

        try:
            session = await client.create_session({
                "model": self.model,
                "streaming": False,
            })

            response = await session.send_and_wait({"prompt": prompt})
            return self._extract_content(response).strip()
        finally:
            await client.stop()

    def _build_prompt(
        self,
        title: str,
        body: str,
        files: List[Dict],
        diff: str,
    ) -> str:
        files_summary = "\n".join(
            f"- {f['filename']} (+{f['additions']}/-{f['deletions']})"
            for f in files[:15]
        )

        diff_preview = diff[:2500] + "\n...[truncated]" if len(diff) > 2500 else diff

        return (
            "You are GitHub Copilot, an expert code reviewer.\n\n"
            f"PR Title: {title}\n\n"
            f"Description:\n{body or 'No description provided'}\n\n"
            f"Files Changed:\n{files_summary}\n\n"
            "Code Diff:\n"
            f"{diff_preview}\n\n"
            "Provide:\n"
            "1. Summary\n"
            "2. Key changes\n"
            "3. Risks or issues\n"
            "4. Quality and best practices\n"
            "5. Testing notes\n"
            "6. Recommendation\n"
        )

    def _extract_content(self, response) -> str:
        # Copilot SDK returns SessionEvent objects; normalize to text.
        if isinstance(response, str):
            return response

        data = getattr(response, "data", None)
        if isinstance(data, dict):
            content = data.get("content")
            if isinstance(content, str):
                return content

        for attr in ("content", "message", "text", "result"):
            value = getattr(response, attr, None)
            if isinstance(value, str):
                return value

        return str(response)