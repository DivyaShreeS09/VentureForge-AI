"""Master Startup Corpus Expansion Sprint, Phases 2-3: tests for the corpus-merge helpers in
ml/src/preprocessing/build_retrieval_corpus.py — small in-memory fixtures only, never a real
download in a test (matches this project's offline-test convention elsewhere).
"""

from __future__ import annotations

import pandas as pd

from ml.src.preprocessing.build_retrieval_corpus import (
    _country_from_all_locations,
    _dedupe_robustly,
    _normalize_country,
)


def test_country_from_all_locations_takes_first_location_last_segment():
    assert _country_from_all_locations("Toronto, ON, Canada") == "Canada"
    assert _country_from_all_locations("Menlo Park, CA, USA; Remote") == "United States"


def test_country_from_all_locations_handles_missing_gracefully():
    assert _country_from_all_locations(None) is None
    assert _country_from_all_locations("") is None
    assert _country_from_all_locations(float("nan")) is None


def test_normalize_country_aliases_common_variants():
    assert _normalize_country("USA") == "United States"
    assert _normalize_country("uk") == "United Kingdom"
    assert _normalize_country("France") == "France"


def test_dedupe_robustly_drops_exact_text_duplicates():
    df = pd.DataFrame({
        "name": ["Acme", "Acme Inc"],
        "description": ["A canteen ordering platform for offices.", "A canteen ordering platform for offices."],
        "source": ["s1", "s2"],
    })
    result = _dedupe_robustly(df)
    assert len(result) == 1


def test_dedupe_robustly_drops_near_duplicate_paraphrases_not_unrelated_rows():
    df = pd.DataFrame({
        "name": ["Acme", "Acme Rebrand", "Unrelated Co"],
        "description": [
            "A canteen ordering platform helping offices track inventory and reduce food waste daily.",
            "A canteen ordering platform helping offices track inventory and reduce daily food waste.",
            "A hospital scheduling tool for clinical staff shift management across departments.",
        ],
        "source": ["s1", "s1", "s1"],
    })
    result = _dedupe_robustly(df)
    assert len(result) == 2
    assert "Unrelated Co" in result["name"].tolist()


def test_dedupe_robustly_keeps_distinct_short_descriptions_untouched():
    """Short descriptions (<8 significant words) are exempt from near-duplicate candidate
    generation -- the same false-positive-avoidance rule already documented in ml/DATASETS.md for
    this exact corpus family (short descriptions trivially clear a 90% overlap threshold)."""
    df = pd.DataFrame({
        "name": ["A", "B"],
        "description": ["AI for security cameras", "Data for audio AI models"],
        "source": ["s1", "s1"],
    })
    result = _dedupe_robustly(df)
    assert len(result) == 2
