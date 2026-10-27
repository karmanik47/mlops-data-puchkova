"""Create deterministic CSV versions for the data-versioning practice."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sklearn.datasets import load_iris, load_wine


DATA_DIR = Path(__file__).resolve().parent / "data"
CSV_OPTIONS = {"index": False, "lineterminator": "\n", "float_format": "%.10g"}


def sorted_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a stable row ordering while preserving the column order."""
    return frame.sort_values(
        by=list(frame.columns), kind="mergesort", ignore_index=True
    )


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sorted_frame(frame).to_csv(path, **CSV_OPTIONS)


def prepare_base() -> None:
    """Create the base Iris-only state."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    wine_path = DATA_DIR / "wine.csv"
    if wine_path.exists():
        wine_path.unlink()
    write_csv(load_iris(as_frame=True).frame, DATA_DIR / "iris.csv")


def prepare_wine() -> None:
    """Add Wine without touching the existing Iris file."""
    iris_path = DATA_DIR / "iris.csv"
    if not iris_path.is_file():
        raise FileNotFoundError("data/iris.csv is required; run mode 'base' first")
    write_csv(load_wine(as_frame=True).frame, DATA_DIR / "wine.csv")


def prepare_iris_features() -> None:
    """Replace Iris with a version containing two deterministic features."""
    iris = load_iris(as_frame=True).frame.copy()
    iris["sepal_area"] = iris["sepal length (cm)"] * iris["sepal width (cm)"]
    iris["petal_area"] = iris["petal length (cm)"] * iris["petal width (cm)"]
    write_csv(iris, DATA_DIR / "iris.csv")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("base", "wine", "iris_features"))
    args = parser.parse_args()
    {
        "base": prepare_base,
        "wine": prepare_wine,
        "iris_features": prepare_iris_features,
    }[args.mode]()


if __name__ == "__main__":
    main()

