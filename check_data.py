"""Validate and describe CSV states produced by prepare_data.py."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal
from sklearn.datasets import load_iris, load_wine


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
FEATURES = ("sepal_area", "petal_area")
STATES = {
    "base": {"iris.csv"},
    "wine": {"iris.csv", "wine.csv"},
    "iris_features": {"iris.csv"},
    "merged": {"iris.csv", "wine.csv"},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sorted_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.sort_values(
        by=list(frame.columns), kind="mergesort", ignore_index=True
    )


def validate_common(path: Path, frame: pd.DataFrame, expected_rows: int) -> None:
    unnamed = [str(column) for column in frame.columns if str(column).startswith("Unnamed:")]
    if unnamed:
        raise ValueError(f"{path.name}: unnamed index columns found: {unnamed}")
    if len(frame) != expected_rows:
        raise ValueError(
            f"{path.name}: expected {expected_rows} rows, found {len(frame)}"
        )
    if int(frame.isna().sum().sum()) != 0:
        raise ValueError(f"{path.name}: missing values found")


def validate_iris(frame: pd.DataFrame, expect_features: bool) -> None:
    source = sorted_frame(load_iris(as_frame=True).frame)
    expected_columns = list(source.columns)
    if expect_features:
        expected_columns.extend(FEATURES)
    if list(frame.columns) != expected_columns:
        raise ValueError(f"iris.csv: wrong columns: {list(frame.columns)}")
    validate_common(DATA_DIR / "iris.csv", frame, len(source))
    assert_frame_equal(
        frame[list(source.columns)], source, check_dtype=False, atol=1e-9, rtol=1e-9
    )
    if expect_features:
        expected_sepal = frame["sepal length (cm)"] * frame["sepal width (cm)"]
        expected_petal = frame["petal length (cm)"] * frame["petal width (cm)"]
        if not frame["sepal_area"].equals(expected_sepal):
            raise ValueError("iris.csv: incorrect sepal_area values")
        if not frame["petal_area"].equals(expected_petal):
            raise ValueError("iris.csv: incorrect petal_area values")


def validate_wine(frame: pd.DataFrame) -> None:
    source = sorted_frame(load_wine(as_frame=True).frame)
    if list(frame.columns) != list(source.columns):
        raise ValueError(f"wine.csv: wrong columns: {list(frame.columns)}")
    validate_common(DATA_DIR / "wine.csv", frame, len(source))
    assert_frame_equal(frame, source, check_dtype=False, atol=1e-9, rtol=1e-9)


def main() -> None:
    global DATA_DIR
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state", choices=tuple(STATES))
    parser.add_argument(
        "--data-dir", type=Path, default=DATA_DIR, help="directory containing CSV files"
    )
    args = parser.parse_args()

    DATA_DIR = args.data_dir.resolve()
    actual = {path.name for path in DATA_DIR.glob("*.csv")} if DATA_DIR.is_dir() else set()
    expected = STATES[args.state]
    if actual != expected:
        raise FileNotFoundError(
            f"expected CSV files {sorted(expected)}, found {sorted(actual)} in {DATA_DIR}"
        )

    expect_features = args.state in {"iris_features", "merged"}
    for name in sorted(expected):
        path = DATA_DIR / name
        frame = pd.read_csv(path)
        if name == "iris.csv":
            validate_iris(frame, expect_features)
        else:
            validate_wine(frame)
        print(f"path: {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")
        print(f"sha256: {sha256(path)}")
        print(f"shape: {frame.shape[0]} rows x {frame.shape[1]} columns")
        print(f"columns: {list(frame.columns)}")
        print(f"missing_values: {int(frame.isna().sum().sum())}")


if __name__ == "__main__":
    main()

