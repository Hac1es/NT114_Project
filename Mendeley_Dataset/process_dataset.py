#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Process dataset using feature groups from eda_report.json.

- Discrete data: QuantileTransformer, then multiply by 20000.
- Continuous data: value * (20000 / (column_max + 0.1)).
- hourOfDay/dayOfWeek: cyclical sin/cos encoding scaled to 0..20000.
- One-hot columns: kept as 0/1.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import OrdinalEncoder, QuantileTransformer


SCALE_TARGET = 20000.0
SCRIPT_DIR = Path(__file__).resolve().parent
SKIP_COLUMNS = {"Id", "FunctionId"}
CYCLICAL_COLUMNS = {"hourOfDay", "dayOfWeek"}
ONE_HOT_PREFIXES = ("functionTrigger_", "vmcategory_")


def resolve_path(path):
    path = Path(path)
    if path.is_absolute() or path.exists():
        return path

    script_relative_path = SCRIPT_DIR / path
    if script_relative_path.exists():
        return script_relative_path

    return path


def load_eda_report(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def is_one_hot_column(col):
    return col.startswith(ONE_HOT_PREFIXES)


def get_existing_columns(df, columns, group_name):
    missing = [col for col in columns if col not in df.columns]
    if missing:
        print(f"[WARN] Missing {group_name} columns skipped: {missing}")

    skipped = [
        col
        for col in columns
        if col in df.columns
        and (col in SKIP_COLUMNS or col in CYCLICAL_COLUMNS or is_one_hot_column(col))
    ]
    if skipped:
        print(f"[INFO] Skipping {group_name} columns: {skipped}")

    return [
        col
        for col in columns
        if col in df.columns
        and col not in SKIP_COLUMNS
        and col not in CYCLICAL_COLUMNS
        and not is_one_hot_column(col)
    ]


def scale_sincos(values, period):
    radians = 2 * np.pi * pd.to_numeric(values, errors="coerce") / period
    sin_scaled = (np.sin(radians) + 1) * (SCALE_TARGET / 2)
    cos_scaled = (np.cos(radians) + 1) * (SCALE_TARGET / 2)
    return sin_scaled, cos_scaled


def transform_cyclical_columns(df):
    if "hourOfDay" in df.columns:
        hour_sin, hour_cos = scale_sincos(df["hourOfDay"], 24)
        df["hourOfDay_sin"] = hour_sin
        df["hourOfDay_cos"] = hour_cos
        df.drop(columns=["hourOfDay"], inplace=True)
        print("[INFO] Encoded hourOfDay as scaled sin/cos")

    if "dayOfWeek" in df.columns:
        day_sin, day_cos = scale_sincos(df["dayOfWeek"], 7)
        df["dayOfWeek_sin"] = day_sin
        df["dayOfWeek_cos"] = day_cos
        df.drop(columns=["dayOfWeek"], inplace=True)
        print("[INFO] Encoded dayOfWeek as scaled sin/cos")


def encode_if_needed(series):
    if pd.api.types.is_numeric_dtype(series):
        return series.astype(float).to_numpy().reshape(-1, 1), None

    encoder = OrdinalEncoder(
        handle_unknown="use_encoded_value",
        unknown_value=-1,
        encoded_missing_value=-1,
    )
    values = series.astype("string").fillna("__MISSING__").to_numpy().reshape(-1, 1)
    encoded = encoder.fit_transform(values)
    return encoded, encoder


def transform_discrete_column(df, col):
    values, _ = encode_if_needed(df[col])
    non_missing_count = np.count_nonzero(~pd.isna(values.ravel()))
    n_quantiles = max(1, min(1000, non_missing_count))

    transformer = QuantileTransformer(
        n_quantiles=n_quantiles,
        output_distribution="uniform",
        random_state=42,
        copy=True,
    )

    transformed = transformer.fit_transform(values).ravel()
    df[col] = transformed * SCALE_TARGET


def transform_continuous_column(df, col, eda_report):
    col_max = eda_report["continuous_data"][col]["max"]
    factor = SCALE_TARGET / (float(col_max) + 0.1)
    df[col] = pd.to_numeric(df[col], errors="coerce") * factor


def process_dataset(input_path, eda_path, output_path):
    input_path = resolve_path(input_path)
    eda_path = resolve_path(eda_path)

    eda_report = load_eda_report(eda_path)
    discrete_cols = eda_report["assessment"]["discrete_data"]
    continuous_cols = eda_report["assessment"]["continuous_data"]

    print(f"[INFO] Reading dataset: {input_path}")
    df = pd.read_csv(input_path)
    transform_cyclical_columns(df)

    discrete_cols = get_existing_columns(df, discrete_cols, "discrete")
    continuous_cols = get_existing_columns(df, continuous_cols, "continuous")

    print(f"[INFO] Transforming {len(discrete_cols)} discrete columns")
    for col in discrete_cols:
        transform_discrete_column(df, col)

    print(f"[INFO] Scaling {len(continuous_cols)} continuous columns")
    for col in continuous_cols:
        transform_continuous_column(df, col, eda_report)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"[OK] Processed dataset saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Process dataset using EDA report")
    parser.add_argument(
        "input",
        nargs="?",
        default="dow_dataset.csv",
        help="Input CSV file",
    )
    parser.add_argument(
        "-e",
        "--eda",
        default="eda_report.json",
        help="EDA report JSON file",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="dow_processed_dataset.csv",
        help="Output CSV file",
    )
    args = parser.parse_args()

    process_dataset(args.input, args.eda, args.output)


if __name__ == "__main__":
    main()
