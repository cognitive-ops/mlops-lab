"""
Build the nnU-Net v2 dataset.json and verify the directory layout.

Run this after generate_synthetic_data.py:
    python prepare_dataset.py

The script:
  1. Counts training images / labels and validates they are paired.
  2. Writes dataset.json in the nnU-Net v2 schema.
  3. Prints a summary of every case found.
"""

import json
import logging
import sys

from config import (
    DATASET_DESCRIPTION,
    DATASET_DIR,
    DATASET_NAME,
    IMAGES_TR_DIR,
    IMAGES_TS_DIR,
    LABELS,
    LABELS_TR_DIR,
    VOXEL_SPACING,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _stem(path) -> str:
    """Return the case ID from a NIfTI filename, e.g. spine_001_0000 → spine_001."""
    name = path.stem  # removes .gz
    if name.endswith(".nii"):
        name = name[:-4]  # removes .nii
    # Remove trailing _0000 channel suffix if present
    if name.endswith("_0000"):
        name = name[:-5]
    return name


def collect_training_cases() -> list[dict]:
    """
    Pair every image file in imagesTr with its label in labelsTr.
    Returns a list of {"image": "...", "label": "..."} dicts expected by nnU-Net.
    """
    images = sorted(IMAGES_TR_DIR.glob("*.nii.gz"))
    labels = sorted(LABELS_TR_DIR.glob("*.nii.gz"))

    image_ids = {_stem(p): p for p in images}
    label_ids = {_stem(p): p for p in labels}

    paired: list[dict] = []
    errors: list[str] = []

    for case_id, img_path in sorted(image_ids.items()):
        if case_id not in label_ids:
            errors.append(f"Missing label for {case_id}")
            continue
        paired.append(
            {
                "image": f"./imagesTr/{img_path.name}",
                "label": f"./labelsTr/{label_ids[case_id].name}",
            }
        )

    for case_id in label_ids:
        if case_id not in image_ids:
            errors.append(f"Orphan label (no matching image) for {case_id}")

    if errors:
        for err in errors:
            log.error(err)
        sys.exit(1)

    return paired


# ── dataset.json ──────────────────────────────────────────────────────────────

def build_dataset_json(training_cases: list[dict]) -> dict:
    """
    Construct the dataset.json payload for nnU-Net v2.

    Reference: https://github.com/MIC-DKFZ/nnUNet/blob/master/documentation/dataset_format.md
    """
    test_images = sorted(IMAGES_TS_DIR.glob("*.nii.gz"))

    return {
        "name": DATASET_NAME,
        "description": DATASET_DESCRIPTION,
        "tensorImageSize": "3D",
        "reference": "Synthetic demo dataset — not real patient data",
        "licence": "CC-BY 4.0",
        "release": "1.0",
        # channel_names: channel index → modality name
        "channel_names": {"0": "CT"},
        # labels: name → integer class index
        "labels": LABELS,
        # numTraining: total number of training cases
        "numTraining": len(training_cases),
        # file_ending: extension used for all NIfTI files
        "file_ending": ".nii.gz",
        # training: list of {image, label} relative paths
        "training": training_cases,
        # test: list of image relative paths (no labels)
        "test": [f"./imagesTs/{p.name}" for p in test_images],
        # oversampling_foreground_p: nnU-Net parameter (optional, included for completeness)
        "oversampling_foreground_p": 0.33,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if not DATASET_DIR.exists():
        log.error(
            "Dataset directory not found: %s\n"
            "Run generate_synthetic_data.py first.",
            DATASET_DIR,
        )
        sys.exit(1)

    log.info("Collecting training cases from %s …", IMAGES_TR_DIR)
    training_cases = collect_training_cases()
    log.info("  Found %d paired training cases.", len(training_cases))

    test_count = len(list(IMAGES_TS_DIR.glob("*.nii.gz")))
    log.info("  Found %d test images.", test_count)

    dataset_json = build_dataset_json(training_cases)

    out_path = DATASET_DIR / "dataset.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(dataset_json, fh, indent=2)

    log.info("Wrote %s", out_path)

    # ── Pretty summary ────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"  Dataset : {DATASET_NAME}")
    print(f"  Training: {len(training_cases)} cases")
    print(f"  Test    : {test_count} cases")
    print(f"  Labels  : {list(LABELS.keys())}")
    print(f"  Spacing : {VOXEL_SPACING} mm")
    print(f"  Output  : {DATASET_DIR}")
    print("=" * 60)
    print("\nTo start nnU-Net preprocessing:")
    print(
        f"  export nnUNet_raw={DATASET_DIR.parent}\n"
        f"  nnUNetv2_plan_and_preprocess -d {DATASET_NAME.split('_')[0][7:]} --verify_dataset_integrity"
    )


if __name__ == "__main__":
    main()
