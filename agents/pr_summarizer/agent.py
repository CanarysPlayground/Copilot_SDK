import argparse
import asyncio
import logging

from rich.console import Console
from rich.logging import RichHandler

from .copilot_analyzer import CopilotAnalyzer
from .github_integration import GitHubPRClient

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)],
)

logger = logging.getLogger(__name__)
console = Console()


async def analyze_pr(pr_number: int) -> None:
    console.print("[cyan]🤖 Copilot PR Analyzer[/cyan]")
    console.print(f"[dim]Analyzing PR #{pr_number}...[/dim]\n")

    try:
        github = GitHubPRClient()
        copilot = CopilotAnalyzer()

        console.print("[yellow]📥 Fetching PR data...[/yellow]")
        pr_data = github.get_pr_data(pr_number)

        console.print(f"[green]✓[/green] PR: {pr_data['title']}")
        console.print(f"[dim]Files changed: {len(pr_data['files'])}[/dim]\n")

        console.print("[yellow]🧠 Analyzing with Copilot SDK...[/yellow]")
        summary = await copilot.analyze_pr_with_copilot(
            pr_title=pr_data["title"],
            pr_body=pr_data["body"],
            files_changed=pr_data["files"],
            diff=pr_data["diff"],
        )

        console.print("[yellow]💬 Posting summary comment...[/yellow]")
        github.post_summary_comment(pr_number, summary)

        console.print(f"\n[green]✅ Successfully analyzed PR #{pr_number}[/green]")
        console.print("\n[bold]Generated Summary:[/bold]")
        console.print(summary)

    except Exception as exc:
        console.print(f"\n[red]❌ Error: {exc}[/red]")
        logger.exception("Agent failed")
        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PR Summarizer using GitHub Copilot SDK"
    )
    parser.add_argument(
        "--pr",
        type=int,
        required=True,
        help="PR number to analyze",
    )
    args = parser.parse_args()
    asyncio.run(analyze_pr(args.pr))


if __name__ == "__main__":
    main()