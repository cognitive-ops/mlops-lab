"""
Validate the generated nnU-Net dataset.

Checks:
  - Required directories exist
  - dataset.json is present and has required keys
  - Every training image has a matching label (same spatial dimensions)
  - Label values are within the declared class set
  - Voxel spacings are consistent across all files

Usage:
    python validate_dataset.py
"""

import json
import logging
import sys

import nibabel as nib
import numpy as np

from config import DATASET_DIR, IMAGES_TR_DIR, IMAGES_TS_DIR, LABELS, LABELS_TR_DIR

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

REQUIRED_JSON_KEYS = {
    "name",
    "channel_names",
    "labels",
    "numTraining",
    "file_ending",
    "training",
}


# ── Checks ────────────────────────────────────────────────────────────────────

def check_directories() -> bool:
    ok = True
    for d in [DATASET_DIR, IMAGES_TR_DIR, LABELS_TR_DIR, IMAGES_TS_DIR]:
        if not d.exists():
            log.error("Missing directory: %s", d)
            ok = False
        else:
            log.info("[OK] %s", d)
    return ok


def check_dataset_json() -> dict | None:
    json_path = DATASET_DIR / "dataset.json"
    if not json_path.exists():
        log.error("dataset.json not found: %s", json_path)
        return None

    with open(json_path, encoding="utf-8") as fh:
        data = json.load(fh)

    missing = REQUIRED_JSON_KEYS - data.keys()
    if missing:
        log.error("dataset.json missing required keys: %s", missing)
        return None

    declared_train = data["numTraining"]
    actual_train = len(list(IMAGES_TR_DIR.glob("*.nii.gz")))
    if declared_train != actual_train:
        log.warning(
            "numTraining mismatch: dataset.json says %d, found %d files",
            declared_train,
            actual_train,
        )

    log.info("[OK] dataset.json — %d training, %d test", declared_train, len(data.get("test", [])))
    return data


def _load_meta(path) -> tuple[tuple, tuple]:
    """Return (shape, zooms) for a NIfTI file without loading the full array."""
    img = nib.load(str(path))
    return tuple(img.shape), tuple(float(z) for z in img.header.get_zooms()[:3])


def check_image_label_pairs() -> bool:
    images = sorted(IMAGES_TR_DIR.glob("*.nii.gz"))
    if not images:
        log.error("No training images found in %s", IMAGES_TR_DIR)
        return False

    ok = True
    spacings_seen: list[tuple] = []

    for img_path in images:
        # Derive case ID by stripping _0000 channel suffix
        stem = img_path.stem
        if stem.endswith(".nii"):
            stem = stem[:-4]
        case_id = stem.removesuffix("_0000")

        lbl_path = LABELS_TR_DIR / f"{case_id}.nii.gz"
        if not lbl_path.exists():
            log.error("No label for %s", case_id)
            ok = False
            continue

        img_shape, img_zooms = _load_meta(img_path)
        lbl_shape, lbl_zooms = _load_meta(lbl_path)

        if img_shape != lbl_shape:
            log.error("%s: shape mismatch image=%s label=%s", case_id, img_shape, lbl_shape)
            ok = False
        else:
            log.info("[OK] %s  shape=%s  spacing=%s mm", case_id, img_shape, img_zooms)

        spacings_seen.append(img_zooms)

    # Warn if spacings are inconsistent
    unique_spacings = set(spacings_seen)
    if len(unique_spacings) > 1:
        log.warning("Inconsistent voxel spacings found: %s", unique_spacings)

    return ok


def check_label_values() -> bool:
    """Sample the first training label and verify its values are within LABELS."""
    labels_files = sorted(LABELS_TR_DIR.glob("*.nii.gz"))
    if not labels_files:
        return True

    sample_path = labels_files[0]
    arr = nib.load(str(sample_path)).get_fdata(dtype=np.float32).astype(np.int32)
    unique_vals = set(np.unique(arr).tolist())
    allowed_vals = set(LABELS.values())

    unexpected = unique_vals - allowed_vals
    if unexpected:
        log.error("Unexpected label values in %s: %s", sample_path.name, unexpected)
        return False

    log.info("[OK] Label values %s in %s", sorted(unique_vals), sample_path.name)
    return True


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    results: list[bool] = []

    print("\n── Directory check ──────────────────────────────────────────")
    results.append(check_directories())

    print("\n── dataset.json check ───────────────────────────────────────")
    json_data = check_dataset_json()
    results.append(json_data is not None)

    print("\n── Image / label pairing & spacing check ────────────────────")
    results.append(check_image_label_pairs())

    print("\n── Label value check ────────────────────────────────────────")
    results.append(check_label_values())

    print("\n" + "=" * 60)
    if all(results):
        log.info("All checks passed.  Dataset is ready for nnU-Net preprocessing.")
    else:
        log.error("Some checks FAILED. Fix the errors above before running nnU-Net.")
        sys.exit(1)


if __name__ == "__main__":
    main()
