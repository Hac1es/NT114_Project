#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Network-Domain EDA -> JSON Export
Groups features into discrete and continuous data.
"""

import json
import argparse
import numpy as np
import pandas as pd


def build_quantiles(series):
    quantiles = list(np.arange(0.05, 1.00, 0.05)) + [0.99]
    q_vals = series.quantile(quantiles).to_dict()
    return {f"q{int(q * 100):02d}": float(v) for q, v in q_vals.items()}


def build_quantile_profile(quantiles):
    values = list(quantiles.values())
    rounded_values = [round(v, 10) for v in values]
    unique_quantile_count = len(set(rounded_values))
    total_quantiles = len(values)
    quantile_unique_ratio = unique_quantile_count / total_quantiles
    repeated_quantile_ratio = 1 - quantile_unique_ratio
    fractional_quantile_count = sum(
        not np.isclose(v, round(v), rtol=0, atol=1e-9) for v in values
    )

    return {
        "quantile_count": total_quantiles,
        "unique_quantile_count": unique_quantile_count,
        "quantile_unique_ratio": float(quantile_unique_ratio),
        "repeated_quantile_ratio": float(repeated_quantile_ratio),
        "fractional_quantile_count": int(fractional_quantile_count),
        "fractional_quantile_ratio": float(fractional_quantile_count / total_quantiles),
    }


def classify_numeric_by_quantiles(quantile_profile, unique_count):
    dense_quantiles = quantile_profile["quantile_unique_ratio"] >= 0.85
    has_fractional_quantiles = quantile_profile["fractional_quantile_ratio"] > 0.15
    high_cardinality = unique_count > 100

    return has_fractional_quantiles or (dense_quantiles and high_cardinality)


def network_domain_eda(df):
    result = {
        "assessment": {
            "discrete_data": [],
            "continuous_data": [],
        },
        "discrete_data": {},
        "continuous_data": {},
    }

    num_cols = df.select_dtypes(include=['number']).columns
    cat_cols = df.select_dtypes(include=['object', 'category', 'str']).columns

    # ===================== NUMERIC =====================
    if len(num_cols) > 0:
        for col in num_cols:
            col_series = df[col].dropna()
            if len(col_series) == 0:
                continue

            unique_count = int(col_series.nunique())
            quantiles = build_quantiles(col_series)
            quantile_profile = build_quantile_profile(quantiles)
            is_continuous = classify_numeric_by_quantiles(quantile_profile, unique_count)
            is_discrete = not is_continuous

            stats = {
                "count": int(len(col_series)),
                "missing_count": int(df[col].isna().sum()),
                "data_type": str(df[col].dtype),
                "mean": float(col_series.mean()),
                "std": float(col_series.std()),
                "min": float(col_series.min()),
                "max": float(col_series.max()),
                "unique_count": unique_count,
                "top_frequency_percent": float(col_series.value_counts(normalize=True).iloc[0] * 100),
                "quantiles": quantiles,
                "quantile_profile": quantile_profile,
            }

            if is_discrete:
                result["assessment"]["discrete_data"].append(col)
                result["discrete_data"][col] = stats
            else:
                result["assessment"]["continuous_data"].append(col)
                result["continuous_data"][col] = stats

    # ===================== CATEGORICAL =====================
    if len(cat_cols) > 0:
        for col in cat_cols:
            col_series = df[col].dropna()
            vc = col_series.value_counts(dropna=False)
            
            cat_stats = {
                "count": int(col_series.count()),
                "missing_count": int(df[col].isna().sum()),
                "data_type": str(df[col].dtype),
                "unique_count": int(col_series.nunique()),
                "top": str(vc.index[0]) if len(vc) > 0 else None,
                "top_frequency_percent": float(vc.iloc[0] / len(col_series) * 100) if len(vc) > 0 and len(col_series) > 0 else None,
            }

            result["assessment"]["discrete_data"].append(col)
            result["discrete_data"][col] = cat_stats

    return result


def main():
    parser = argparse.ArgumentParser(description="EDA JSON Exporter")
    parser.add_argument("input", help="Input CSV file")
    parser.add_argument(
        "-o", "--output", default="eda_report.json", help="Output JSON file"
    )
    args = parser.parse_args()

    try:
        df = pd.read_csv(args.input)
    except Exception as e:
        print(f"[ERROR] Cannot read file: {e}")
        return

    result = network_domain_eda(df)

    try:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4, ensure_ascii=False)
        print(f"[OK] EDA report saved to: {args.output}")
    except Exception as e:
        print(f"[ERROR] Cannot write JSON: {e}")

if __name__ == "__main__":
    main()
