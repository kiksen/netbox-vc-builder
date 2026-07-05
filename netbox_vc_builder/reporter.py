import logging

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .constants import LOG_FILE_NAME
from .models import RunSummary


def _setup_log_file(log_file: str) -> logging.Logger:
    logger = logging.getLogger("netbox_vc_builder")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        fh = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        fh.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)-5s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
        )
        logger.addHandler(fh)
    return logger


class Reporter:
    def __init__(self, dry_run: bool = False, log_file: str = LOG_FILE_NAME):
        self._console = Console()
        self._dry_run = dry_run
        self._log = _setup_log_file(log_file)

    def info(self, message: str) -> None:
        self._console.print(f"[green]✓[/green] {message}")
        self._log.info(message)

    def newline(self):
        self._console.print("")

    def list(self, message: str):
        self._console.print(f"\t - {message}")
        self._log.warning(message)


    def warn(self, message: str) -> None:
        self._console.print(f"[yellow]⚠[/yellow] {message}")
        self._log.warning(message)

    def error(self, message: str) -> None:
        self._console.print(f"[red]✗[/red] {message}")
        self._log.error(message)

    def debug(self, message: str) -> None:
        self._console.print(f"[dim]{message}[/dim]")
        self._log.debug(message)

    def section(self, title: str) -> None:
        self._console.print()
        self._console.print(f"[bold]{title}[/bold]")
        self._log.info(title)

    def summary(self, summary: RunSummary) -> None:
        table = Table.grid(padding=(0, 2))
        table.add_column()
        table.add_column()

        table.add_row("[white]📊[/white]", f"{summary.stacks_found} Stacks found")
        table.add_row("[green]✓[/green]", f"Successfully updated: {summary.created}")
        table.add_row("[yellow]⚠[/yellow]", f"Skipped: {summary.skipped}")
        table.add_row("[red]✗[/red]", f"Failed: {summary.failed}")
        table.add_row("[white]⏱[/white]", f"Duration: {summary.duration_seconds:.1f}s")

        self._console.print(Panel(table, title="Summary"))
        self._log.info(
            f"Summary: {summary.stacks_found} found, {summary.created} created, "
            f"{summary.skipped} skipped, {summary.failed} failed"
        )


class NullReporter(Reporter):
    """Silent reporter for unit tests."""

    def __init__(self) -> None:
        pass

    def info(self, _: str) -> None:
        pass

    def warn(self, _: str) -> None:
        pass

    def error(self, _: str) -> None:
        pass

    def debug(self, _: str) -> None:
        pass

    def section(self, _: str) -> None:
        pass

    def summary(self, _: RunSummary) -> None:
        pass
