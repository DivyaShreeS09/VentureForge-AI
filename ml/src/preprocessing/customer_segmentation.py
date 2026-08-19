"""Reusable leakage-safe transaction preprocessing for RFM segmentation."""

from __future__ import annotations


import pandas as pd

REQUIRED_TRANSACTION_COLUMNS = {"InvoiceNo", "InvoiceDate", "CustomerID", "Quantity", "UnitPrice"}


def prepare_transaction_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Clean transactional records and retain a documented audit in ``DataFrame.attrs``.

    Cancellations, returns, unknown customers, invalid dates, duplicate rows, and non-positive
    quantities/prices are excluded before aggregation. The function never imputes a customer ID.
    """
    missing = REQUIRED_TRANSACTION_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"dataset is missing required columns: {sorted(missing)}")

    data = frame.copy()
    audit: dict[str, int] = {"raw_rows": len(data)}
    data = data.drop_duplicates()
    audit["duplicate_rows_removed"] = audit["raw_rows"] - len(data)
    data["InvoiceDate"] = pd.to_datetime(data["InvoiceDate"], errors="coerce")
    data["Quantity"] = pd.to_numeric(data["Quantity"], errors="coerce")
    data["UnitPrice"] = pd.to_numeric(data["UnitPrice"], errors="coerce")
    valid_customer = data["CustomerID"].notna()
    valid_date = data["InvoiceDate"].notna()
    is_cancellation = data["InvoiceNo"].astype(str).str.upper().str.startswith("C")
    positive_transaction = (data["Quantity"] > 0) & (data["UnitPrice"] > 0)
    valid = valid_customer & valid_date & ~is_cancellation & positive_transaction
    audit["missing_customer_rows_removed"] = int((~valid_customer).sum())
    audit["invalid_date_rows_removed"] = int((~valid_date).sum())
    audit["cancellation_or_return_rows_removed"] = int(is_cancellation.sum())
    audit["non_positive_value_rows_removed"] = int((~positive_transaction).sum())
    data = data.loc[valid].copy()
    if data.empty:
        raise ValueError("no valid transactions remain after cleaning")
    data["CustomerID"] = data["CustomerID"].astype("string")
    data["transaction_value"] = data["Quantity"] * data["UnitPrice"]
    audit["cleaned_rows"] = len(data)
    data.attrs["cleaning_audit"] = audit
    return data


def build_rfm_features(frame: pd.DataFrame, reference_date: pd.Timestamp | None = None) -> pd.DataFrame:
    """Aggregate cleaned transactions to Recency/Frequency/Monetary features.

    ``reference_date`` must be fixed for reproducible training; absent one, the day after the
    latest valid transaction is used. It is never calculated using future data at inference.
    """
    data = prepare_transaction_frame(frame)
    snapshot_date = reference_date or (data["InvoiceDate"].max() + pd.Timedelta(days=1))
    if snapshot_date <= data["InvoiceDate"].max():
        raise ValueError("reference_date must be after the latest valid transaction")
    grouped = data.groupby("CustomerID", as_index=False).agg(
        last_purchase=("InvoiceDate", "max"),
        frequency=("InvoiceNo", "nunique"),
        monetary=("transaction_value", "sum"),
    )
    grouped["recency_days"] = (snapshot_date - grouped.pop("last_purchase")).dt.days.astype(float)
    result = grouped[["CustomerID", "recency_days", "frequency", "monetary"]]
    result.attrs["cleaning_audit"] = data.attrs["cleaning_audit"]
    result.attrs["snapshot_date"] = snapshot_date.isoformat()
    return result


def winsorize_rfm(rfm: pd.DataFrame, lower: float = 0.01, upper: float = 0.99) -> tuple[pd.DataFrame, dict[str, dict[str, float]]]:
    """Clip extreme customer-level RFM values, preserving every customer and recording bounds."""
    if not 0 <= lower < upper <= 1:
        raise ValueError("outlier quantiles must satisfy 0 <= lower < upper <= 1")
    result = rfm.copy()
    bounds: dict[str, dict[str, float]] = {}
    for column in ("recency_days", "frequency", "monetary"):
        low, high = result[column].quantile([lower, upper])
        bounds[column] = {"lower": float(low), "upper": float(high)}
        result[column] = result[column].clip(low, high)
    return result, bounds
