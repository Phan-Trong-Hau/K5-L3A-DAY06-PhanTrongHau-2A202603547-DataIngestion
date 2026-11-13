"""Portable source paths and explicit historical input snapshots."""
import hashlib
import json
from pathlib import Path


def local_source_path(root: Path, manifest: dict) -> Path:
    """Resolve a bundled source relative to the repo; support old local manifests."""
    value = manifest.get('local_path')
    if not value:
        value = manifest.get('source_path_or_url', '')
        if '://' in value:
            raise ValueError('Manifest needs local_path for a bundled source')
    path = Path(value)
    return path if path.is_absolute() else root / path


def recorded_input_path(root: Path, run_dir: Path, path: str, digest: str) -> Path:
    """Verify the current input or an explicitly archived execution-time snapshot.

    Never rewrites old run hashes or considers a changed file to be the old input.
    """
    current = root / path
    if current.is_file() and hashlib.sha256(current.read_bytes()).hexdigest() == digest:
        return current
    migrations = run_dir / 'provenance_migrations.json'
    if migrations.is_file():
        snapshots = json.loads(migrations.read_text())['snapshots']
        if path in snapshots:
            archived = root / snapshots[path]
            if archived.is_file() and hashlib.sha256(archived.read_bytes()).hexdigest() == digest:
                return archived
    raise ValueError(f'Recorded input hash mismatch: {path}')
