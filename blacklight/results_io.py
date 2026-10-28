"""Create result files without replacing an existing artifact."""

from argparse import ArgumentParser
from pathlib import Path


def require_new_output(path: Path) -> None:
    """Fail early before an expensive simulation if its destination exists.

    The final write must still use exclusive creation: a preflight check alone
    cannot prevent another process from creating the file in the meantime.
    """
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"Output already exists; choose a new filename: {path}")


def write_new_text(path: Path, content: str, *, newline: str | None = None) -> None:
    """Create a UTF-8 file atomically with respect to the destination name."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline=newline) as handle:
        handle.write(content)


def historical_output(description: str | None) -> Path:
    """Require an explicit legacy-rules opt-in and a fresh destination."""
    parser = ArgumentParser(description=description)
    parser.add_argument('--historical-rules', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.historical_rules:
        parser.error('This study uses historical Fast Strikes rules; pass --historical-rules explicitly')
    try:
        require_new_output(args.output)
    except FileExistsError as exc:
        parser.error(str(exc))
    return args.output
