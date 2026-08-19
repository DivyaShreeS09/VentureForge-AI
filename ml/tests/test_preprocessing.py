import pandas as pd
import pytest

from ml.src.preprocessing.clean_data import clean_industry_dataset


def test_drops_duplicate_descriptions():
    df = pd.DataFrame(
        {
            "name": ["A", "B"],
            "description": ["Same description here.", "Same description here."],
            "industry": ["saas", "saas"],
        }
    )
    cleaned = clean_industry_dataset(df)
    assert len(cleaned) == 1


def test_drops_short_descriptions():
    df = pd.DataFrame(
        {"name": ["A"], "description": ["short"], "industry": ["saas"]}
    )
    cleaned = clean_industry_dataset(df)
    assert len(cleaned) == 0


def test_normalizes_industry_label_case():
    df = pd.DataFrame(
        {"name": ["A"], "description": ["A sufficiently long description of the company."], "industry": ["  SaaS  "]}
    )
    cleaned = clean_industry_dataset(df)
    assert cleaned.iloc[0]["industry"] == "saas"


def test_missing_required_column_raises():
    df = pd.DataFrame({"name": ["A"], "description": ["A long enough description."]})
    with pytest.raises(ValueError):
        clean_industry_dataset(df)
