"""
Generate synthetic lumbar-spine CT volumes in NIfTI format.

Each case contains:
  - A 3-D CT-like volume (float32, Hounsfield-unit range)
  - A matching integer segmentation mask (labels 0-5 → background + L1-L5)

Usage:
    python generate_synthetic_data.py
"""

import logging
import random

import nibabel as nib
import numpy as np
from scipy.ndimage import gaussian_filter

from config import (
    FIRST_VERTEBRA_Z,
    HU_BONE_MEAN,
    HU_BONE_STD,
    HU_NOISE_STD,
    HU_SOFT_TISSUE_MEAN,
    HU_SOFT_TISSUE_STD,
    LABELS,
    NUM_TEST_CASES,
    NUM_TRAIN_CASES,
    VERTEBRA_HEIGHT_Z,
    VERTEBRA_RADIUS_XY,
    VERTEBRA_SPACING_Z,
    VOLUME_SHAPE,
    VOXEL_SPACING,
    IMAGES_TR_DIR,
    IMAGES_TS_DIR,
    LABELS_TR_DIR,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)


# ── Geometry helpers ──────────────────────────────────────────────────────────

def _ellipsoid_mask(
    shape: tuple[int, int, int],
    center: tuple[float, float, float],
    radii: tuple[float, float, float],
) -> np.ndarray:
    """Return a boolean mask where the ellipsoid is True."""
    x, y, z = np.ogrid[: shape[0], : shape[1], : shape[2]]
    cx, cy, cz = center
    rx, ry, rz = radii
    dist = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 + ((z - cz) / rz) ** 2
    return dist <= 1.0


def _build_vertebra_mask(
    shape: tuple[int, int, int],
    label_idx: int,
    cx: float,
    cy: float,
    cz: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Create a single vertebra mask with slight random shape perturbation so each
    generated case looks subtly different.
    """
    rx = VERTEBRA_RADIUS_XY + rng.uniform(-1.5, 1.5)
    ry = VERTEBRA_RADIUS_XY + rng.uniform(-1.5, 1.5)
    rz = VERTEBRA_HEIGHT_Z / 2 + rng.uniform(-1.0, 1.0)

    ellipsoid = _ellipsoid_mask(shape, (cx, cy, cz), (rx, ry, rz))
    mask = np.zeros(shape, dtype=np.uint8)
    mask[ellipsoid] = label_idx
    return mask


# ── Volume factory ────────────────────────────────────────────────────────────

def generate_case(
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate one synthetic CT volume and its ground-truth segmentation.

    Returns
    -------
    image : float32 array (X, Y, Z)
    label : uint8 array  (X, Y, Z)
    """
    shape = VOLUME_SHAPE

    # --- Background (soft-tissue HU with spatially correlated noise) ----------
    base = rng.normal(HU_SOFT_TISSUE_MEAN, HU_SOFT_TISSUE_STD, shape).astype(np.float32)
    base = gaussian_filter(base, sigma=1.5)

    # Random position jitter for the whole spine column
    cx = shape[0] / 2 + rng.uniform(-4, 4)
    cy = shape[1] / 2 + rng.uniform(-4, 4)

    segmentation = np.zeros(shape, dtype=np.uint8)

    for vertebra_name, label_idx in LABELS.items():
        if label_idx == 0:
            continue  # skip background

        # L1 is at FIRST_VERTEBRA_Z; each subsequent vertebra is lower
        cz = FIRST_VERTEBRA_Z + (label_idx - 1) * VERTEBRA_SPACING_Z

        vert_mask = _build_vertebra_mask(shape, label_idx, cx, cy, cz, rng)
        is_bone = vert_mask > 0

        # Add bone HU values into the volume
        bone_hu = rng.normal(HU_BONE_MEAN, HU_BONE_STD, shape).astype(np.float32)
        base[is_bone] = bone_hu[is_bone]

        # Update segmentation mask (later vertebrae may partially overlap earlier ones)
        segmentation[is_bone] = label_idx

    # Gaussian smooth the volume to mimic partial-volume effect, then add noise
    image = gaussian_filter(base, sigma=0.8)
    image += rng.normal(0, HU_NOISE_STD, shape).astype(np.float32)
    image = image.astype(np.float32)

    return image, segmentation


# ── NIfTI I/O ─────────────────────────────────────────────────────────────────

def _make_affine(spacing: tuple[float, float, float]) -> np.ndarray:
    """Diagonal affine matrix from isotropic voxel spacing."""
    sx, sy, sz = spacing
    return np.diag([sx, sy, sz, 1.0])


def save_nifti(array: np.ndarray, path, spacing: tuple[float, float, float]) -> None:
    affine = _make_affine(spacing)
    img = nib.Nifti1Image(array, affine)
    img.header.set_data_dtype(array.dtype)
    nib.save(img, str(path))


# ── Main ──────────────────────────────────────────────────────────────────────

def generate_split(
    n_cases: int,
    start_idx: int,
    images_dir,
    labels_dir,
    save_labels: bool,
    seed_offset: int = 0,
) -> list[str]:
    """Generate *n_cases* NIfTI volumes, return list of case IDs."""
    case_ids: list[str] = []

    for i in range(n_cases):
        case_idx = start_idx + i
        case_id = f"spine_{case_idx:03d}"
        rng = np.random.default_rng(seed=case_idx + seed_offset)

        image, label = generate_case(rng)

        # nnU-Net v2 naming: <case_id>_<channel>.nii.gz (single CT channel → _0000)
        img_path = images_dir / f"{case_id}_0000.nii.gz"
        save_nifti(image, img_path, VOXEL_SPACING)

        if save_labels:
            lbl_path = labels_dir / f"{case_id}.nii.gz"
            save_nifti(label, lbl_path, VOXEL_SPACING)
            log.info("  %s  image=%s  label=%s", case_id, img_path.name, lbl_path.name)
        else:
            log.info("  %s  image=%s  (no label — test set)", case_id, img_path.name)

        case_ids.append(case_id)

    return case_ids


def main() -> None:
    for d in [IMAGES_TR_DIR, LABELS_TR_DIR, IMAGES_TS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    log.info("Generating %d training cases …", NUM_TRAIN_CASES)
    generate_split(
        n_cases=NUM_TRAIN_CASES,
        start_idx=1,
        images_dir=IMAGES_TR_DIR,
        labels_dir=LABELS_TR_DIR,
        save_labels=True,
    )

    log.info("Generating %d test cases …", NUM_TEST_CASES)
    generate_split(
        n_cases=NUM_TEST_CASES,
        start_idx=NUM_TRAIN_CASES + 1,
        images_dir=IMAGES_TS_DIR,
        labels_dir=LABELS_TR_DIR,  # unused when save_labels=False
        save_labels=False,
        seed_offset=1000,
    )

    log.info("Done — files written to %s", IMAGES_TR_DIR.parent)


if __name__ == "__main__":
    main()
