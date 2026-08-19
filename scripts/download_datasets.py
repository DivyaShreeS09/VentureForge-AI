#!/usr/bin/env python3
"""Download datasets listed in ml/dataset_manifest.json into ml/data/raw/.

Only entries with source == "kaggle" and a non-null kaggle_id are downloaded via the Kaggle CLI.
Entries with source == "local" (e.g. the hand-authored bootstrap dataset) are left untouched —
they already live in the repository's data directory.

Usage:
    python scripts/download_datasets.py --list          # show manifest status, no downloads
    python scripts/download_datasets.py                 # download all kaggle entries with a set id
    python scripts/download_datasets.py --force          # re-download even if the file exists

This script never prints or commits credentials. Kaggle authentication must already be configured
via a standard Kaggle CLI mechanism — any of: ~/.kaggle/kaggle.json, ~/.kaggle/access_token (new
token-based auth), or the KAGGLE_USERNAME/KAGGLE_KEY or KAGGLE_API_TOKEN env vars — see
https://www.kaggle.com/docs/api for setup. This script does not read or write those files
directly; it only invokes the Kaggle CLI, which handles credentials itself. The CLI is invoked as
`python -m kaggle` rather than a bare `kaggle` executable, since the kaggle console-script entry
point is not always on PATH even when the package is installed.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "ml" / "dataset_manifest.json"
RAW_DIR = REPO_ROOT / "ml" / "data" / "raw"
KAGGLE_CMD = [sys.executable, "-m", "kaggle"]


def load_manifest() -> list[dict]:
    if not MANIFEST_PATH.exists():
        print(f"ERROR: manifest not found at {MANIFEST_PATH}", file=sys.stderr)
        sys.exit(1)
    return json.loads(MANIFEST_PATH.read_text())["datasets"]


def kaggle_cli_available() -> bool:
    result = subprocess.run(KAGGLE_CMD + ["--version"], capture_output=True, text=True)
    return result.returncode == 0


def kaggle_authenticated() -> bool:
    """Best-effort check without ever printing credential contents."""
    kaggle_dir = Path.home() / ".kaggle"
    return (
        (kaggle_dir / "kaggle.json").exists()
        or (kaggle_dir / "access_token").exists()
        or bool(os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY"))
        or bool(os.environ.get("KAGGLE_API_TOKEN"))
    )


def list_manifest(entries: list[dict]) -> None:
    print(f"{'name':35} {'source':8} {'task':22} {'status':24} kaggle_id")
    print("-" * 110)
    for e in entries:
        print(
            f"{e['name']:35} {e['source']:8} {e['task']:22} {e['status']:24} {e.get('kaggle_id') or '-'}"
        )


def download_entry(entry: dict, force: bool) -> bool:
    dest = REPO_ROOT / entry["path"]
    if dest.exists() and not force:
        print(f"[skip] {entry['name']}: already present at {dest} (use --force to re-download)")
        return True

    dest.parent.mkdir(parents=True, exist_ok=True)
    before = set(dest.parent.glob("*.csv"))

    cmd = KAGGLE_CMD + [
        "datasets",
        "download",
        "-d",
        entry["kaggle_id"],
        "-p",
        str(dest.parent),
        "--unzip",
    ]
    print(f"[download] {entry['name']} <- kaggle:{entry['kaggle_id']}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: kaggle download failed for {entry['name']}:\n{result.stderr}", file=sys.stderr)
        return False

    if not dest.exists():
        # Kaggle's archive filename rarely matches our manifest path — if exactly one new CSV
        # appeared, rename it to the expected path rather than failing.
        after = set(dest.parent.glob("*.csv"))
        new_files = after - before
        if len(new_files) == 1:
            new_files.pop().rename(dest)
        else:
            print(
                f"ERROR: expected file {dest} was not produced by the download, and "
                f"{len(new_files)} new CSVs appeared (expected exactly 1) — "
                "inspect the downloaded archive and update ml/dataset_manifest.json.",
                file=sys.stderr,
            )
            return False

    print(f"[ok] {entry['name']} -> {dest}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", action="store_true", help="List manifest entries and exit (dry-run)")
    parser.add_argument("--force", action="store_true", help="Re-download even if the file already exists")
    args = parser.parse_args()

    entries = load_manifest()

    if args.list:
        list_manifest(entries)
        return 0

    # Only "approved" entries with both a kaggle_id and a destination path are ever downloaded.
    # Rejected/under-evaluation entries are kept in the manifest purely as an audit trail of
    # datasets that were inspected and why they were not used — never fetched or trained on.
    kaggle_entries = [
        e for e in entries if e["source"] == "kaggle" and e.get("kaggle_id") and e.get("path") and e["status"] == "approved"
    ]
    skipped_not_approved = [
        e for e in entries if e["source"] == "kaggle" and e["status"] != "approved"
    ]

    for e in skipped_not_approved:
        print(f"[skip] {e['name']}: status={e['status']} (not approved for download — see ml/DATASETS.md)")

    if not kaggle_entries:
        print("No Kaggle datasets are configured for download. Nothing to do.")
        return 0

    if not kaggle_cli_available():
        print(
            "ERROR: the `kaggle` CLI is not installed or not on PATH. "
            "Install it with `pip install kaggle` and re-run.",
            file=sys.stderr,
        )
        return 1

    if not kaggle_authenticated():
        print(
            "ERROR: Kaggle credentials not found. Configure ~/.kaggle/kaggle.json "
            "(downloaded from https://www.kaggle.com/settings -> API -> Create New Token) "
            "or set KAGGLE_USERNAME and KAGGLE_KEY environment variables. "
            "Credentials are never read from or written to this repository.",
            file=sys.stderr,
        )
        return 1

    ok = all(download_entry(e, args.force) for e in kaggle_entries)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
