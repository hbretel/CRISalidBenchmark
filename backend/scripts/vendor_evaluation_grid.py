"""Refresh the vendored copy of the evaluation-grid project.

The qualitative-indicators pipeline (app/services/quality/) reuses the scoring
engine (grille/) and the per-criterion checkers (auto_checkers/) of
https://github.com/hbretel/evaluation-grid, copied verbatim under
backend/vendor/evaluation_grid/ so the backend image needs no access to that
repository at build time. Only the modules the backend imports are copied; the
CLI orchestrator, tests, fixtures, UI and reports stay upstream.

Usage (from backend/):
    python -m scripts.vendor_evaluation_grid                 # clone the default branch
    python -m scripts.vendor_evaluation_grid --source ../../evaluation-grid   # local checkout

Never edit the vendored files by hand: change them upstream, then re-run this
script. The commit copied is recorded in vendor/evaluation_grid/VENDORED.md.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

REPO_URL = "https://github.com/hbretel/evaluation-grid.git"
DEST = Path(__file__).resolve().parent.parent / "vendor" / "evaluation_grid"

FILES = [
    "grille/__init__.py",
    "grille/parameters.py",
    "grille/results.py",
    "grille/score_engine.py",
    "auto_checkers/__init__.py",
    "auto_checkers/checkers.py",
    "auto_checkers/orientation.py",
    "auto_checkers/publisher_lists.py",
    "auto_checkers/publisher_lists_data.json",
    "auto_checkers/retraction_watch.py",
    "auto_checkers/sources.py",
    "auto_checkers/type_tables.py",
    # score_engine.CSV_PATH (canonical grid) is the default path of several
    # helpers; the working grid actually used by the backend is the calibration
    # file below (see app/services/quality/grid.py::GRID_FILE).
    "data/criteres_grille_evaluation.csv",
    "data/ponderation_calibration_20261002.csv",
]


def _copy_from(source: Path) -> str:
    commit = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    if DEST.exists():
        shutil.rmtree(DEST)
    for rel in FILES:
        target = DEST / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / rel, target)
    (DEST / "VENDORED.md").write_text(
        "# Vendored copy of evaluation-grid\n\n"
        f"- Source : {REPO_URL}\n"
        f"- Commit : `{commit}`\n"
        f"- Copied on : {date.today().isoformat()}\n\n"
        "Do not edit these files here: change them upstream, then run\n"
        "`python -m scripts.vendor_evaluation_grid` from backend/.\n",
        encoding="utf-8",
    )
    return commit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, help="Local checkout of evaluation-grid (default: fresh clone).")
    args = parser.parse_args()

    if args.source:
        commit = _copy_from(args.source.resolve())
    else:
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "clone", "--depth", "1", REPO_URL, tmp], check=True)
            commit = _copy_from(Path(tmp))
    print(f"Vendored evaluation-grid @ {commit} into {DEST}", file=sys.stderr)


if __name__ == "__main__":
    main()
