"""Conservative source snapshots for read-only audit scripts."""

from hashlib import sha256
from pathlib import Path

from blacklight.results_io import require_unchanged_sources


ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = ('blacklight', 'combatants', 'experimental', 'scripts', 'tests')


def audit_source_manifest(root: Path = ROOT) -> dict[str, str]:
    paths = sorted(path for name in DIRECTORIES
                   for path in (root / name).rglob('*.py') if path.is_file())
    return {path.relative_to(root).as_posix(): sha256(path.read_bytes()).hexdigest()
            for path in paths}


def require_audit_sources_unchanged(before, root: Path = ROOT):
    require_unchanged_sources(before, audit_source_manifest(root))
