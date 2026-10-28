"""Create and verify the three required ClearML Dataset versions.

Credentials and server addresses are read exclusively from the user's ClearML SDK
configuration. This script never stores them in the repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

# Some VPN/proxy configurations block GET requests with a JSON body. ClearML
# officially supports POST for API requests for exactly this situation.
os.environ.setdefault("CLEARML_API_DEFAULT_REQ_METHOD", "POST")

import pandas as pd
from clearml.backend_api.session.session import Session
from clearml.backend_interface.base import InterfaceBase
from clearml import Dataset

import prepare_data

# The hosted API can take longer than ClearML's 3-second initial timeout when
# the machine is connected through a VPN/tunnel.  Later SDK requests already
# use a much larger timeout, so only make the first authentication request
# equally tolerant.
Session._session_initial_timeout = (30.0, 30.0)
Session._session_timeout = (30.0, 30.0)


def configure_clearml_session() -> None:
    """Use bounded retries so a network problem fails instead of hanging for hours."""
    session = Session(
        initialize_logging=False,
        http_retries_config={
            "total": 3,
            "connect": 3,
            "read": 3,
            "redirect": 3,
            "status": 3,
            "backoff_factor": 1.0,
            "backoff_max": 5.0,
        },
    )
    InterfaceBase._set_default_session(session)


ROOT = Path(__file__).resolve().parent
DOWNLOADS = ROOT.parent / "clearml-downloads-puchkova"
PROJECT = "MIIT/MLOps/practice_3/puchkova"
NAME = "sklearn-tabular-puchkova"
IDS_FILE = ROOT / "clearml_ids.json"


def create_dataset(version: str, description: str, tags: list[str], parents: list[str]) -> Dataset:
    dataset = Dataset.create(
        dataset_project=PROJECT,
        dataset_name=NAME,
        dataset_version=version,
        description=description,
        parent_datasets=parents,
        use_current_task=False,
    )
    dataset.add_tags(tags)
    return dataset


def create_all() -> dict[str, str]:
    original_data_dir = prepare_data.DATA_DIR
    try:
        with tempfile.TemporaryDirectory(prefix="clearml-puchkova-") as temporary:
            root = Path(temporary)
            base_dir = root / "base"
            prepare_data.DATA_DIR = base_dir
            prepare_data.prepare_base()
            base = create_dataset("1.0.0", "Contains the original Iris dataset.", ["base"], [])
            base.add_files(path=str(base_dir / "iris.csv"))
            base.upload()
            base.finalize()

            wine_dir = root / "wine"
            shutil.copytree(base_dir, wine_dir)
            prepare_data.DATA_DIR = wine_dir
            prepare_data.prepare_wine()
            wine = create_dataset(
                "1.1.0", "Adds Wine to the original Iris dataset.", ["wine"], [base.id]
            )
            wine.add_files(path=str(wine_dir / "wine.csv"))
            wine.upload()
            wine.finalize()

            features_dir = root / "iris_features"
            shutil.copytree(base_dir, features_dir)
            prepare_data.DATA_DIR = features_dir
            prepare_data.prepare_iris_features()
            iris_features = create_dataset(
                "2.0.0",
                "Adds sepal_area and petal_area to Iris; branched from base.",
                ["iris-features"],
                [base.id],
            )
            iris_features.add_files(path=str(features_dir / "iris.csv"))
            iris_features.upload()
            iris_features.finalize()
    finally:
        prepare_data.DATA_DIR = original_data_dir

    ids = {
        "BASE_ID": base.id,
        "WINE_ID": wine.id,
        "IRIS_FEATURES_ID": iris_features.id,
    }
    IDS_FILE.write_text(json.dumps(ids, indent=2) + "\n", encoding="utf-8")
    return ids


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_all(ids: dict[str, str]) -> dict[str, object]:
    if DOWNLOADS.exists():
        shutil.rmtree(DOWNLOADS)
    DOWNLOADS.mkdir(parents=True)
    result: dict[str, object] = {}
    for label, dataset_id in ids.items():
        dataset = Dataset.get(dataset_id=dataset_id)
        target = DOWNLOADS / label.lower()
        local = Path(dataset.get_mutable_local_copy(target_folder=str(target), overwrite=False))
        files = sorted(path.relative_to(local).as_posix() for path in local.rglob("*") if path.is_file())
        tables = {}
        for relative in files:
            path = local / relative
            frame = pd.read_csv(path)
            tables[relative] = {
                "sha256": sha256(path),
                "shape": list(frame.shape),
                "columns": list(frame.columns),
            }
        result[label] = {
            "id": dataset.id,
            "version": dataset.version,
            "dependency_graph": dataset.get_dependency_graph(),
            "files": files,
            "added": sorted(dataset.list_added_files()),
            "modified": sorted(dataset.list_modified_files()),
            "removed": sorted(dataset.list_removed_files()),
            "tables": tables,
        }
    output = ROOT / "clearml_verification.json"
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main() -> None:
    configure_clearml_session()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "verify", "all"))
    args = parser.parse_args()
    ids = create_all() if args.action in {"create", "all"} else json.loads(IDS_FILE.read_text(encoding="utf-8"))
    if args.action in {"verify", "all"}:
        print(json.dumps(inspect_all(ids), indent=2, ensure_ascii=False))
    else:
        print(json.dumps(ids, indent=2))


if __name__ == "__main__":
    main()

