"""CSV loading and core data functions (get_targets, get_expressions)."""
import logging
import os
from pathlib import Path
from typing import Dict, List

import pandas as pd

logger = logging.getLogger(__name__)

_df = None
_DEFAULT_CSV = "owkin_take_home_data.csv"


def _get_df():
    """Load CSV once; look in cwd then parent (for Docker)."""
    global _df
    if _df is not None:
        return _df
    base = Path(__file__).resolve().parent.parent
    for path in [Path.cwd() / _DEFAULT_CSV, base / _DEFAULT_CSV]:
        if path.exists():
            _df = pd.read_csv(path)
            return _df
    env_path = os.getenv("OWKIN_CSV_PATH")
    if env_path and Path(env_path).exists():
        _df = pd.read_csv(env_path)
        return _df
    raise FileNotFoundError(f"CSV not found: {_DEFAULT_CSV} (tried cwd and project root)")


def get_available_cancers() -> List[str]:
    """Return list of unique cancer types in the dataset."""
    df = _get_df()
    result = sorted(df["cancer_indication"].dropna().unique().tolist())
    logger.info("get_available_cancers() called -> %d cancer types: %s", len(result), result[:12])
    return result


def get_all_genes() -> List[str]:
    """Return list of unique gene symbols in the dataset."""
    df = _get_df()
    return sorted(df["gene"].dropna().unique().tolist())


def get_targets(cancer_name: str) -> List[str]:
    """Return a list of gene targets for a given cancer type."""
    df = _get_df()
    result = df[df["cancer_indication"] == cancer_name]["gene"].tolist()
    logger.info("get_targets(cancer_name=%r) called -> %d genes", cancer_name, len(result))
    return result


def get_expressions(genes: List[str]) -> Dict[str, float]:
    """Return the median values for the given list of genes (across all cancers, last wins)."""
    df = _get_df()
    subset = df[df["gene"].isin(genes)]
    result = dict(zip(subset["gene"], subset["median_value"]))
    logger.info("get_expressions(genes=%s) called -> %d values", genes[:10], len(result))
    return result


def get_expressions_for_cancer(cancer_name: str, genes: List[str]) -> Dict[str, float]:
    """Return median values for genes filtered to a specific cancer type."""
    df = _get_df()
    subset = df[(df["cancer_indication"] == cancer_name) & (df["gene"].isin(genes))]
    result = dict(zip(subset["gene"], subset["median_value"]))
    logger.info(
        "get_expressions_for_cancer(cancer=%r, genes=%s) called -> %d values",
        cancer_name, genes[:10], len(result),
    )
    return result
