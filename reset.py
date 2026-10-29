#!/usr/bin/env python3
"""Reset generated edit state without touching source media or configuration.

Run from any directory: python3 /path/to/repo/reset.py [--dry-run]
Clears work/ and workdir/ (including working Markdown), root audio/video
exports, and root *_project.json render recipes. Recreates a fresh progress.md.
Source directories, assets, and workflow docs are preserved.
"""

import argparse
from pathlib import Path
import shutil
import subprocess


MEDIA_EXTENSIONS = {
    ".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".mpg", ".mpeg",
    ".3gp", ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus",
    ".wma", ".aiff", ".aif", ".mxf", ".mts", ".m2ts",
}


def fresh_progress():
    """Return a fresh checklist without depending on workflow documentation."""
    return """# Edit progress

## Selected inputs
- Clips:
- Music:

## Steps
- [ ] 0 — Preflight
- [ ] 1 — Footage analysis
- [ ] 2 — Music analysis
- [ ] 3 — Edit plan
- [ ] 4 — Framing
- [ ] 5 — Grade tuning
- [ ] 6 — Render, audio mix and verify
"""


def tracked_files(root):
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, check=True, capture_output=True,
    )
    return {p.decode("utf-8", errors="surrogateescape")
            for p in result.stdout.split(b"\0") if p}


def cleanup_targets(root, tracked):
    candidates = []
    for name in ("work", "workdir"):
        folder = root / name
        if folder.is_symlink():
            raise ValueError(f"Refusing symlinked workspace: {name}")
        if folder.exists():
            if not folder.is_dir():
                raise ValueError(f"Expected a directory: {name}")
            candidates.extend(folder.iterdir())
    for path in root.iterdir():
        if path.is_file() and (
            path.suffix.lower() in MEDIA_EXTENSIONS
            or path.name.endswith("_project.json")
        ):
            candidates.append(path)
    targets = []
    for path in sorted(candidates):
        relative = path.relative_to(root).as_posix()
        if any(p == relative or p.startswith(relative + "/") for p in tracked):
            raise ValueError(f"Refusing to remove tracked content: {relative}")
        targets.append(path)
    if "workdir/progress.md" in tracked:
        raise ValueError("Refusing to overwrite tracked workdir/progress.md")
    return targets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Preview without changing files")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    try:
        # Validate everything before deleting anything.
        progress = fresh_progress()
        targets = cleanup_targets(root, tracked_files(root))
        for path in targets:
            print(f"{'Would remove' if args.dry_run else 'Removing'} {path.relative_to(root)}")
            if not args.dry_run:
                if path.is_dir() and not path.is_symlink():
                    shutil.rmtree(path)
                else:
                    path.unlink()
        if args.dry_run:
            print("Would write fresh workdir/progress.md (all steps unchecked)")
        else:
            (root / "workdir").mkdir(exist_ok=True)
            (root / "workdir" / "progress.md").write_text(progress, encoding="utf-8")
            print("Reset complete: workdir/progress.md is ready for a new edit.")
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Reset failed: {error}\n")


if __name__ == "__main__":
    main()
