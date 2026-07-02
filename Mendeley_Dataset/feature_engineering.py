#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Feature engineering for the DoW dataset.

Input:
    dow_raw_dataset.csv

Output:
    dow_dataset.csv
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


def add_ip_rolling_features(df):
    df = df.sort_values(by=["IP", "timestamp"]).reset_index(drop=True)
    df = df.set_index("timestamp")

    df["ipMin"] = (
        df.groupby("IP")["IP"]
        .rolling("1min")
        .count()
        .reset_index(level=0, drop=True)
    )
    df["ipHour"] = (
        df.groupby("IP")["IP"]
        .rolling("1h")
        .count()
        .reset_index(level=0, drop=True)
    )

    return df.reset_index()


def engineer_features(df_raw):
    df = df_raw.copy()

    df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601", utc=True)
    df["hourOfDay"] = df["timestamp"].dt.hour
    df["dayOfWeek"] = df["timestamp"].dt.dayofweek

    df = add_ip_rolling_features(df)

    df["FunctionId"] = df["FunctionId"].astype("category")

    encoded = pd.get_dummies(
        df[["functionTrigger", "vmcategory"]],
        columns=["functionTrigger", "vmcategory"],
        prefix=["functionTrigger", "vmcategory"],
        dtype=int,
    )

    df = pd.concat([df, encoded], axis=1)
    df = df.drop(columns=["IP", "timestamp", "functionTrigger", "vmcategory"])

    return df


def process_file(input_path, output_path):
    input_path = resolve_path(input_path)
    output_path = Path(output_path)
    if not output_path.is_absolute():
        output_path = SCRIPT_DIR / output_path

    print(f"[INFO] Reading dataset: {input_path}")
    df_raw = pd.read_csv(input_path)

    print("[INFO] Engineering features")
    df = engineer_features(df_raw)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"[OK] Feature-engineered dataset saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Feature engineering for DoW dataset")
    parser.add_argument(
        "input",
        nargs="?",
        default="raw_dataset.csv",
        help="Input raw CSV file",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="dow_dataset.csv",
        help="Output feature-engineered CSV file",
    )
    args = parser.parse_args()

    process_file(args.input, args.output)


if __name__ == "__main__":
    main()
