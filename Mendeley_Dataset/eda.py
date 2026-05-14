#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Comprehensive EDA → JSON Export
- Numeric stats + skew + kurtosis + imbalance
- Quantiles: 5% → 95%
- Categorical summary
"""

import json
import argparse
import numpy as np
import pandas as pd


def comprehensive_eda_to_json(df):
    result = {}

    num_cols = df.select_dtypes(include=['number']).columns
    cat_cols = df.select_dtypes(include=['object', 'category', 'str']).columns

    # ===================== NUMERIC =====================
    if len(num_cols) > 0:
        desc = df[num_cols].describe().T

        desc['skew'] = df[num_cols].skew()
        desc['kurtosis'] = df[num_cols].kurt()
        desc['top_freq_pct'] = df[num_cols].apply(
            lambda x: x.value_counts(normalize=True).iloc[0] * 100
        )
        desc['unique'] = df[num_cols].nunique()

        # ===== QUANTILES (5% step) =====
        quantiles = np.arange(0.05, 1.00, 0.05)
        q_df = df[num_cols].quantile(quantiles)
        q_dict = q_df.to_dict()

        numeric_dict = desc.to_dict(orient='index')

        for col, stats in numeric_dict.items():
            clean_stats = {
                k: (None if pd.isna(v) else float(v))
                for k, v in stats.items()
            }

            # Add quantiles
            if col in q_dict:
                clean_stats["quantiles"] = {
                    f"q{int(q*100):02d}": (
                        None if pd.isna(v) else float(v)
                    )
                    for q, v in q_dict[col].items()
                }

            result[col] = clean_stats

    # ===================== CATEGORICAL =====================
    if len(cat_cols) > 0:
        for col in cat_cols:
            vc = df[col].value_counts(dropna=False)

            result[col] = {
                "type": "categorical",
                "count": int(df[col].count()),
                "unique": int(df[col].nunique()),
                "top": vc.index[0] if len(vc) > 0 else None,
                "top_freq": int(vc.iloc[0]) if len(vc) > 0 else None,
                "top_freq_pct": (
                    float(vc.iloc[0] / len(df) * 100) if len(vc) > 0 else None
                )
            }

    return result


def main():
    parser = argparse.ArgumentParser(description="EDA → JSON exporter")
    parser.add_argument("input", help="Input CSV file")
    parser.add_argument(
        "-o", "--output", default="eda_output.json", help="Output JSON file"
    )

    args = parser.parse_args()

    # Load data
    try:
        df = pd.read_csv(args.input)
    except Exception as e:
        print(f"[ERROR] Cannot read file: {e}")
        return

    # Run EDA
    result = comprehensive_eda_to_json(df)

    # Export JSON
    try:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4, ensure_ascii=False)
        print(f"[OK] EDA saved to: {args.output}")
    except Exception as e:
        print(f"[ERROR] Cannot write JSON: {e}")


if __name__ == "__main__":
    main()