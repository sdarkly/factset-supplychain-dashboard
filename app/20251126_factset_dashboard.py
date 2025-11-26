# app.py
# Streamlit dashboard for unique buyer–supplier relationships in 20251125_UKsuppliers_compiled.xlsx

import pandas as pd
import numpy as np
import streamlit as st

# -----------------------------
# Configuration
# -----------------------------
EXCEL_PATH = r"data/20251125_UKsuppliers_compiled.xlsx"  # adjust to your local path
SOURCE_SHEET = "source_uk"
TARGET_SHEET = "target_uk"

# -----------------------------
# Data loading and preparation
# -----------------------------
@st.cache_data
def load_and_prepare_data():
    # Read sheets
    source = pd.read_excel(EXCEL_PATH, sheet_name=SOURCE_SHEET)
    target = pd.read_excel(EXCEL_PATH, sheet_name=TARGET_SHEET)

    # Normalise from source_uk:
    # In source_uk the UK company is the SOURCE (buyer), target is the supplier.
    source_norm = pd.DataFrame({
        "buyer_company_id": source["source_company_id"],
        "buyer_name":       source["source_name"],
        "buyer_isin":       source["source_isin"],
        "buyer_has_scf":    source["has_scf"].fillna(0).astype(int),

        "supplier_company_id": source["target_company_id"],
        "supplier_name":       source["target_name"],
        "supplier_isin":       source["target_isin"],
        "supplier_ticker":     source["target_ticker"],
    })

    # Normalise from target_uk:
    # In target_uk the UK company is the TARGET (buyer), source is the supplier.
    target_norm = pd.DataFrame({
        "buyer_company_id": target["target_company_id"],
        "buyer_name":       target["target_name"],
        "buyer_isin":       target["target_isin"],
        "buyer_has_scf":    target["has_scf"].fillna(0).astype(int),

        "supplier_company_id": target["source_company_id"],
        "supplier_name":       target["source_name"],
        "supplier_isin":       target["source_isin"],
        "supplier_ticker":     target["source_ticker"],
    })

    # Concatenate and drop rows with missing buyer or supplier ids
    rels = pd.concat([source_norm, target_norm], ignore_index=True)

    rels = rels.dropna(subset=["buyer_company_id", "supplier_company_id"])

    # Deduplicate exact buyer–supplier pairs (id-based)
    rels = rels.drop_duplicates(subset=["buyer_company_id", "supplier_company_id"])

    # Derived attributes
    # Supplier is private if ticker is missing or empty
    rels["supplier_is_private"] = rels["supplier_ticker"].isna() | (rels["supplier_ticker"].astype(str).str.strip() == "")

    # Supplier in UK if ISIN starts with 'GB' (simple proxy)
    rels["supplier_is_uk"] = rels["supplier_isin"].astype(str).str.startswith("GB")

    # Buyer has SCF already encoded in buyer_has_scf (0/1)
    rels["buyer_has_scf"] = rels["buyer_has_scf"].fillna(0).astype(int)

    return rels


rels = load_and_prepare_data()

# -----------------------------
# Sidebar filters
# -----------------------------
st.sidebar.header("Filters")

supplier_listing_filter = st.sidebar.selectbox(
    "Supplier listing status",
    ("All suppliers", "Private suppliers only", "Listed suppliers only"),
)

supplier_uk_filter = st.sidebar.selectbox(
    "Supplier location",
    ("All suppliers", "UK suppliers only", "Non-UK suppliers only"),
)

buyer_scf_filter = st.sidebar.selectbox(
    "Buyer SCF status",
    ("All buyers", "Buyers with SCF only", "Buyers without SCF only"),
)

# -----------------------------
# Apply filters
# -----------------------------
filtered = rels.copy()

# Supplier listing filter
if supplier_listing_filter == "Private suppliers only":
    filtered = filtered[filtered["supplier_is_private"]]
elif supplier_listing_filter == "Listed suppliers only":
    filtered = filtered[~filtered["supplier_is_private"]]

# Supplier UK filter
if supplier_uk_filter == "UK suppliers only":
    filtered = filtered[filtered["supplier_is_uk"]]
elif supplier_uk_filter == "Non-UK suppliers only":
    filtered = filtered[~filtered["supplier_is_uk"]]

# Buyer SCF filter
if buyer_scf_filter == "Buyers with SCF only":
    filtered = filtered[filtered["buyer_has_scf"] == 1]
elif buyer_scf_filter == "Buyers without SCF only":
    filtered = filtered[filtered["buyer_has_scf"] == 0]

# Work on unique buyer–supplier pairs after filtering
pairs = filtered[["buyer_company_id", "supplier_company_id"]].drop_duplicates()

total_unique_relationships = len(pairs)

if total_unique_relationships > 0:
    suppliers_per_buyer = (
        pairs.groupby("buyer_company_id")["supplier_company_id"]
        .nunique()
        .astype(float)
    )
    avg_suppliers_per_buyer = suppliers_per_buyer.mean()
else:
    avg_suppliers_per_buyer = 0.0

# -----------------------------
# Dashboard layout
# -----------------------------
st.title("UK Buyer–Supplier Network Dashboard")

st.markdown(
    """
    This dashboard counts unique buyer–supplier relationships across the **source_uk** and **target_uk** sheets,
    and applies dynamic filters on supplier listing status, supplier UK status, and buyer SCF status.
    """
)

col1, col2 = st.columns(2)

with col1:
    st.metric(
        "Total unique buyer–supplier relationships",
        f"{total_unique_relationships:,}"
    )

with col2:
    st.metric(
        "Average number of suppliers per buyer",
        f"{avg_suppliers_per_buyer:,.2f}"
    )

st.markdown("### Filtered sample (first 50 relationships)")
st.dataframe(
    filtered[
        [
            "buyer_name",
            "buyer_company_id",
            "buyer_has_scf",
            "supplier_name",
            "supplier_company_id",
            "supplier_ticker",
            "supplier_is_private",
            "supplier_is_uk",
        ]
    ]
    .drop_duplicates(subset=["buyer_company_id", "supplier_company_id"])
    .head(50)
)

# Optional: show counts for context
st.markdown("### Context counts")
st.write(
    {
        "distinct buyers (after filters)": pairs["buyer_company_id"].nunique(),
        "distinct suppliers (after filters)": pairs["supplier_company_id"].nunique(),
    }
)
