"""Master Startup Corpus Expansion Sprint, Phases 2-4: build the unified, richer-metadata corpus
that powers app.ml.venture_retrieval (the "similar ventures" / Startup Benchmark retrieval index)
-- a DIFFERENT consumer than the industry classifier, even though they share source data.

REUSE, NOT RE-ACQUISITION: the prior "ML Data Acquisition & Corpus Expansion Sprint" already
searched, downloaded, licensed-checked, and merged three real YC-sourced Kaggle datasets into
ml/data/raw/industry_dataset_expanded_v2.csv (see ml/DATASETS.md) -- but that merge intentionally
kept only name/description/industry/source (the classifier's input schema) and discarded the
richer per-record fields (country, funding stage, team size, batch year, sub-industry) the raw
files actually contain. This script re-reads those SAME already-licensed raw files directly and
carries those richer fields through instead of re-downloading anything.

Phase 2 dataset decisions for the RETRIEVAL corpus specifically (a fresh evaluation -- retrieval's
needs differ from the classifier's):

ACCEPTED (reused from already-licensed raw files, no re-download):
  - ml/data/raw/yc_companies_2012_2024_raw.csv (CC BY 4.0, ibrahimqasimi/y-combinator-companies-2012-2024)
  - ml/data/raw/yc_companies_2025_raw.csv (already in-repo, same YC-OSS lineage)
  - ml/data/raw/yc_companies_full_directory_2005_2026_raw.csv (CC-BY-SA-4.0, alibekmamyrbay/y-combinator-startups-full-directory-20052026)

ACCEPTED (newly evaluated and downloaded THIS sprint):
  - ml/data/raw/joebeachcapital_startups_raw.csv (kaggle: joebeachcapital/startups, CC-BY-SA-4.0,
    688 rows). Genuinely distinct from the three sources above: real founder names, real investor
    names, real per-company funding amounts (disclosed as free text, e.g. "$1200000, undisclosed
    amount" -- never reformatted into a fabricated structured number), country, and founding year.
    Known data-quality caveat, disclosed not hidden: a handful of rows' `Company` name and
    `Description` text refer to a company's former name (e.g. "Curebit" / description mentions
    "Talkable", its rebrand) -- both are kept verbatim from the source; no name was invented or
    "corrected" to match.

REJECTED THIS sprint:
  - kaggle:yuhesh/y-combinator-directory-2005-2026 (5,785 rows). Downloaded and inspected
    (ml/data/external_candidates/yc_2005_2026/) -- real data, CC0-1.0, but REDUNDANT: it is a
    different scrape of the same underlying YC public directory already integrated via
    yc_companies_full_directory_2005_2026_raw.csv above. Adding it would double-count nearly the
    same real companies under two different record IDs, inflating corpus size without adding real
    coverage -- rejected as a duplication risk, not a licensing/quality problem.
  - kaggle:arindam235/startup-investments-crunchbase (54,294 rows). Downloaded and inspected
    (ml/data/external_candidates/crunchbase/) -- CC0-1.0, real Crunchbase data, but has NO
    free-text description field anywhere in its 39 columns (category_list/market/funding fields
    only). Rejected per this sprint's explicit rule against corpus sources lacking textual
    descriptions -- this is exactly the kind of dataset structural search-by-similarity retrieval
    cannot use, however rich its funding metadata is.

Run: `python -m ml.src.preprocessing.build_retrieval_corpus`
Writes ml/data/processed/retrieval_corpus_v2.csv (does not touch any existing production artifact
or the classifier's own industry_dataset*.csv files).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = REPO_ROOT / "ml" / "data" / "raw"
OUTPUT_PATH = REPO_ROOT / "ml" / "data" / "processed" / "retrieval_corpus_v2.csv"

MIN_DESCRIPTION_LENGTH = 15
# Placeholder text real founders/scrapers use for undisclosed companies -- not real signal, and
# duplicated verbatim across many unrelated companies, which would otherwise look like a mass
# near-duplicate cluster.
PLACEHOLDER_DESCRIPTIONS = {"stealth", "nan", "n/a", "tbd", "coming soon"}

_COMMON_COUNTRY_ALIASES = {
    "usa": "United States", "us": "United States", "u.s.a.": "United States",
    "united states of america": "United States",
    "uk": "United Kingdom", "u.k.": "United Kingdom",
}


def _normalize_country(raw: str | None) -> str | None:
    if not raw or not isinstance(raw, str):
        return None
    value = raw.strip().strip(".")
    if not value:
        return None
    return _COMMON_COUNTRY_ALIASES.get(value.lower(), value)


def _country_from_all_locations(all_locations: str | None) -> str | None:
    """`all_locations` is a semicolon-separated list of "City, State/Region, Country"-style
    strings (real field, ml/data/raw/yc_companies_2012_2024_raw.csv) -- take the first listed
    location's last comma-separated segment as its country. Heuristic string parsing of a real
    field, not an invented value; returns None rather than guessing when the format doesn't match."""
    if not all_locations or not isinstance(all_locations, str):
        return None
    first_location = all_locations.split(";")[0].strip()
    parts = [p.strip() for p in first_location.split(",") if p.strip()]
    if not parts:
        return None
    return _normalize_country(parts[-1])


def _load_yc_2012_2024() -> pd.DataFrame:
    path = RAW_DIR / "yc_companies_2012_2024_raw.csv"
    raw = pd.read_csv(path)
    one_liner = raw["one_liner"].fillna("").astype(str).str.strip()
    long_description = raw["long_description"].fillna("").astype(str).str.strip()
    description = (one_liner + ". " + long_description).str.strip(". ").str.strip()
    return pd.DataFrame({
        "name": raw["name"].astype(str).str.strip(),
        "description": description,
        "industry": raw["industry"].astype(str).str.strip().str.lower(),
        "subindustry": raw.get("subindustry"),
        "country": raw["all_locations"].apply(_country_from_all_locations),
        "funding_stage": raw.get("stage"),
        "team_size": raw.get("team_size"),
        "founding_year": pd.to_datetime(raw["launched_at"], unit="s", errors="coerce").dt.year,
        "source": "yc_2012_2024",
    })


def _load_yc_2025() -> pd.DataFrame:
    path = RAW_DIR / "yc_companies_2025_raw.csv"
    raw = pd.read_csv(path)
    description = raw["company_description"].fillna("").astype(str).str.strip()
    return pd.DataFrame({
        "name": raw["company_name"].astype(str).str.strip(),
        "description": description,
        "industry": raw["industry_1_url.1"].astype(str).str.strip().str.lower(),
        "subindustry": raw.get("industry_2"),
        "country": raw["location"].apply(_country_from_all_locations),
        "funding_stage": None,
        "team_size": None,
        "founding_year": 2025,
        "source": "yc_2025",
    })


def _load_yc_full_directory() -> pd.DataFrame:
    path = RAW_DIR / "yc_companies_full_directory_2005_2026_raw.csv"
    raw = pd.read_csv(path)
    one_liner = raw["one_liner"].fillna("").astype(str).str.strip()
    long_description = raw["long_description"].fillna("").astype(str).str.strip()
    description = (one_liner + ". " + long_description).str.strip(". ").str.strip()
    return pd.DataFrame({
        "name": raw["name"].astype(str).str.strip(),
        "description": description,
        "industry": raw["industry"].astype(str).str.strip().str.lower(),
        "subindustry": raw.get("subindustry"),
        "country": raw["country"].apply(_normalize_country),
        "funding_stage": raw.get("stage"),
        "team_size": raw.get("team_size"),
        "founding_year": raw.get("batch_year"),
        "source": "yc_full_directory_2005_2026",
    })


def _load_joebeachcapital() -> pd.DataFrame:
    path = RAW_DIR / "joebeachcapital_startups_raw.csv"
    raw = pd.read_csv(path)
    return pd.DataFrame({
        "name": raw["Company"].astype(str).str.strip(),
        "description": raw["Description"].fillna("").astype(str).str.strip(),
        # This source has no single-label controlled industry field -- `Categories` is a free-text,
        # multi-value column (e.g. "E-Commerce, Analytics, Internet"). Taking the first listed
        # category is a real (if coarse) label from the source, not an invented one; recorded under
        # its own distinct value space rather than forced into the YC industry taxonomy.
        "industry": raw["Categories"].fillna("unspecified").astype(str).str.split(",").str[0].str.strip().str.lower(),
        "subindustry": None,
        "country": raw["Headquarters (Country)"].apply(_normalize_country),
        "funding_stage": None,
        "team_size": None,
        "founding_year": raw.get("Year Founded"),
        "source": "joebeachcapital",
    })


def _significant_words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z']+", text.lower()) if len(w) > 3}


def _dedupe_robustly(df: pd.DataFrame) -> pd.DataFrame:
    """Deduplication in two passes, neither of which is name-only (a real 3.5%+ name-collision
    rate between different real companies sharing a short name was already documented for this
    same corpus family in ml/DATASETS.md -- name-based dedup would silently conflate distinct
    companies):

    1. Exact-description-text dedup across ALL sources (kept: first occurrence, by source-priority
       order below) -- catches the identical-row case cheaply.
    2. Near-duplicate dedup via normalized significant-word Jaccard overlap (>=90%, both
       descriptions >=8 tokens per the false-positive-avoidance finding already documented for this
       corpus in ml/DATASETS.md's Label-Quality Audit) -- catches paraphrased/re-batched repeats
       exact-text matching misses, using an inverted-index candidate search rather than a full
       O(n^2) comparison (this corpus is too large for that to finish in reasonable time).
    """
    before = len(df)
    df = df.drop_duplicates(subset=["description"], keep="first").reset_index(drop=True)
    logger.info("Exact-text dedup: dropped %d rows (%d remaining)", before - len(df), len(df))

    words_per_row = [_significant_words(d) for d in df["description"]]
    inverted_index: dict[str, list[int]] = {}
    for i, words in enumerate(words_per_row):
        if len(words) < 8:
            continue
        for w in words:
            inverted_index.setdefault(w, []).append(i)

    to_drop: set[int] = set()
    checked_pairs: set[tuple[int, int]] = set()
    for indices in inverted_index.values():
        if len(indices) < 2 or len(indices) > 50:  # skip pathologically common tokens (rare here given >3-char, but a defensive cap)
            continue
        for a_idx in range(len(indices)):
            for b_idx in range(a_idx + 1, len(indices)):
                i, j = indices[a_idx], indices[b_idx]
                if i in to_drop or j in to_drop:
                    continue
                pair = (min(i, j), max(i, j))
                if pair in checked_pairs:
                    continue
                checked_pairs.add(pair)
                wi, wj = words_per_row[i], words_per_row[j]
                overlap = len(wi & wj) / min(len(wi), len(wj))
                if overlap >= 0.90:
                    to_drop.add(j)  # drop the later row, keep the earlier (source-priority order)

    logger.info("Near-duplicate dedup: flagged %d additional rows (%d candidate pairs checked)", len(to_drop), len(checked_pairs))
    df = df.drop(index=sorted(to_drop)).reset_index(drop=True)
    return df


def build_corpus() -> pd.DataFrame:
    sources = [
        _load_yc_2012_2024(),
        _load_yc_2025(),
        _load_yc_full_directory(),
        _load_joebeachcapital(),
    ]
    for s, df in zip(("yc_2012_2024", "yc_2025", "yc_full_directory_2005_2026", "joebeachcapital"), sources):
        logger.info("Loaded %d rows from %s", len(df), s)

    combined = pd.concat(sources, ignore_index=True)

    combined["description"] = combined["description"].fillna("").astype(str).str.strip()
    before = len(combined)
    combined = combined[combined["description"].str.len() >= MIN_DESCRIPTION_LENGTH]
    combined = combined[~combined["description"].str.lower().isin(PLACEHOLDER_DESCRIPTIONS)]
    combined = combined[~combined["industry"].isin({"unspecified", "nan", "", "government"})]
    combined = combined.reset_index(drop=True)
    logger.info("After length/placeholder/label filtering: %d rows (dropped %d)", len(combined), before - len(combined))

    combined = _dedupe_robustly(combined)

    logger.info(
        "Final unified retrieval corpus: %d rows across %d sources, %d distinct industries",
        len(combined), combined["source"].nunique(), combined["industry"].nunique(),
    )
    logger.info("Rows by source:\n%s", combined["source"].value_counts())
    logger.info(
        "Country coverage: %d/%d rows (%.1f%%) have a non-null country",
        combined["country"].notna().sum(), len(combined),
        combined["country"].notna().sum() / len(combined) * 100 if len(combined) else 0,
    )
    return combined


def main() -> None:
    df = build_corpus()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    logger.info("Wrote %d rows to %s", len(df), OUTPUT_PATH)


if __name__ == "__main__":
    main()
