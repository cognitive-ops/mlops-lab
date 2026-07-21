"""
Dataset and generation configuration for the nnU-Net spine demo.
"""
from pathlib import Path

# ── Dataset identity ──────────────────────────────────────────────────────────
DATASET_ID = "001"
DATASET_NAME = f"Dataset{DATASET_ID}_Spine"
DATASET_DESCRIPTION = (
    "Synthetic lumbar-spine CT segmentation dataset for nnU-Net v2 demo. "
    "Images contain five lumbar vertebrae (L1-L5) embedded in soft-tissue background."
)

# ── Output paths ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
NNUNET_RAW_DIR = BASE_DIR / "nnUNet_raw"
DATASET_DIR = NNUNET_RAW_DIR / DATASET_NAME

IMAGES_TR_DIR = DATASET_DIR / "imagesTr"
LABELS_TR_DIR = DATASET_DIR / "labelsTr"
IMAGES_TS_DIR = DATASET_DIR / "imagesTs"

# ── Split ─────────────────────────────────────────────────────────────────────
NUM_TRAIN_CASES = 20
NUM_TEST_CASES = 5

# ── Segmentation labels ───────────────────────────────────────────────────────
LABELS: dict[str, int] = {
    "background": 0,
    "L1": 1,
    "L2": 2,
    "L3": 3,
    "L4": 4,
    "L5": 5,
}

# ── Image generation parameters ───────────────────────────────────────────────
VOLUME_SHAPE = (80, 80, 120)   # (X, Y, Z) voxels  — small for fast demo
VOXEL_SPACING = (1.5, 1.5, 1.5)  # mm isotropic

# Hounsfield-unit ranges (CT context)
HU_SOFT_TISSUE_MEAN = 50
HU_SOFT_TISSUE_STD = 20
HU_BONE_MEAN = 700
HU_BONE_STD = 80
HU_NOISE_STD = 15

# Vertebra geometry (voxels)
VERTEBRA_RADIUS_XY = 9      # approx transverse radius
VERTEBRA_HEIGHT_Z = 10      # approx superior-inferior height
VERTEBRA_SPACING_Z = 14     # center-to-center distance along Z
FIRST_VERTEBRA_Z = 20       # Z center of L1
