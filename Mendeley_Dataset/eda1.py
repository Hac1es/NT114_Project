#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Basic dataset scan utility.

Prints a lightweight overview:
- shape
- column names
- data types
- missing values per column
- rows containing at least one missing value
- duplicate rows count
"""

import argparse
from pathlib import Path

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent


def resolve_path(path):
    path = Path(path)
    if path.is_absolute() or path.exists():
        return path

    script_relative_path = SCRIPT_DIR / path
    if script_relative_path.exists():
        return script_relative_path

    return path


def scan_dataset(input_path):
    input_path = resolve_path(input_path)

    print(f"[INFO] Reading dataset: {input_path}")
    df = pd.read_csv(input_path)

    print(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns")

    print("\nColumns:")
    for column in df.columns:
        print(f"- {column}")

    print("\nData types:")
    print(df.dtypes.to_string())

    print("\nMissing values by column:")
    missing_count = df.isna().sum().sort_values(ascending=False)
    missing_percent = (missing_count / len(df) * 100).round(2)
    missing_report = pd.DataFrame(
        {
            "missing_count": missing_count,
            "missing_percent": missing_percent,
        }
    )
    missing_report = missing_report[missing_report["missing_count"] > 0]

    if missing_report.empty:
        print("- No missing values found in any column")
    else:
        print(missing_report.to_string())

    rows_with_missing = df.isna().any(axis=1)
    missing_rows_count = int(rows_with_missing.sum())
    print(f"\nRows containing missing values: {missing_rows_count}")
    if missing_rows_count > 0:
        print("Sample rows with missing values:")
        sample_missing_rows = df.loc[rows_with_missing].head(5)
        print(sample_missing_rows.to_string(index=True))

    duplicate_rows = int(df.duplicated().sum())
    print(f"\nDuplicate rows: {duplicate_rows}")


def main():
    parser = argparse.ArgumentParser(description="Basic dataset EDA scanner")
    parser.add_argument(
        "input",
        nargs="?",
        default="dataset.csv",
        help="Input CSV file",
    )
    args = parser.parse_args()

    try:
        scan_dataset(args.input)
    except Exception as exc:
        print(f"[ERROR] Cannot scan dataset: {exc}")


if __name__ == "__main__":
    main()