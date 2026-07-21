# nnU-Net Healthcare Training Data Demo

End-to-end demo for generating and preparing synthetic lumbar-spine CT data in the **nnU-Net v2** dataset format.

## What it creates

```
nnUNet_raw/
└── Dataset001_Spine/
    ├── dataset.json          ← nnU-Net v2 metadata (labels, channels, case list)
    ├── imagesTr/             ← 20 training CT volumes  (*_0000.nii.gz)
    ├── labelsTr/             ← 20 ground-truth segmentation masks (*.nii.gz)
    └── imagesTs/             ← 5 test CT volumes (no labels)
```

Each volume is a synthetic 80×80×120 voxel CT (1.5 mm isotropic) containing five
lumbar vertebrae (L1–L5) embedded in a soft-tissue background.  Shape and position
are randomly perturbed per case so the dataset is not trivially identical.

**Labels**

| Index | Structure |
|-------|-----------|
| 0     | Background |
| 1     | L1 |
| 2     | L2 |
| 3     | L3 |
| 4     | L4 |
| 5     | L5 |

---

## Quick start

```bash
# 1. Install dependencies (Python 3.10+)
pip install -r requirements.txt

# 2. Generate synthetic NIfTI volumes
python generate_synthetic_data.py

# 3. Write dataset.json and print summary
python prepare_dataset.py

# 4. Validate the dataset
python validate_dataset.py
```

---

## Using with real nnU-Net

After validation, point nnU-Net at the raw directory and run planning:

```bash
export nnUNet_raw=$(pwd)/nnUNet_raw
export nnUNet_preprocessed=$(pwd)/nnUNet_preprocessed
export nnUNet_results=$(pwd)/nnUNet_results

# Install nnU-Net v2
pip install nnunetv2

# Plan + preprocess (auto-configures patch size, batch size, network topology)
nnUNetv2_plan_and_preprocess -d 1 --verify_dataset_integrity

# Train 2D/3D_fullres/3D_lowres (fold 0)
nnUNetv2_train 1 3d_fullres 0

# Inference on test set
nnUNetv2_predict -i nnUNet_raw/Dataset001_Spine/imagesTs \
                 -o predictions/ \
                 -d 1 -c 3d_fullres -f 0
```

---

## Adapting to real data

To use real DICOM/NIfTI data instead of synthetic volumes:

1. **Convert DICOM → NIfTI** with `SimpleITK` or `dcm2niix`:
   ```bash
   dcm2niix -o imagesTr/ -f "%i_%s_0000" /path/to/dicom/
   ```

2. **Provide segmentation masks** in the same NIfTI space as the images.

3. **Re-run** `prepare_dataset.py` and `validate_dataset.py`.

4. Adjust `config.py` (`LABELS`, `DATASET_NAME`, `VOXEL_SPACING`) to match your anatomy.

---

## Files

| File | Purpose |
|------|---------|
| `config.py` | All tunable parameters (case counts, label map, geometry) |
| `generate_synthetic_data.py` | Synthetic CT + mask generation |
| `prepare_dataset.py` | Write `dataset.json`, print nnU-Net instructions |
| `validate_dataset.py` | Sanity-check the full dataset before training |
| `requirements.txt` | Python dependencies |
