# OceanEye

OceanEye is an AI-powered maritime intelligence platform that detects oil spills using satellite imagery, traces their origin and movement using ocean data, and correlates AIS vessel tracking data to identify and rank potentially responsible vessels, providing authorities with an evidence-based dashboard for faster investigation.

---

## System Architecture

```
DATA INGESTION (Phase 2)
  ├── Sentinel-1 SAR (CDSE OData)
  ├── AIS Vessel Tracking (MarineTraffic / AISHub)
  ├── CMEMS Ocean Currents (Global reanalysis / physics)
  └── CMEMS Wind Vectors (10m hourly)
            │
            ▼
DATA PROCESSING & NORMALIZATION
  ├── scripts/process_data.py
  └── scripts/processing/
            │
            ▼
AI & MACHINE LEARNING LAYER (Phase 3)
  ├── 1. SAR Oil-Spill Candidate Segmentation (PyTorch U-Net)
  ├── 2. Look-Alike vs Real Spill Classifier (XGBoost)
  └── 3. Vessel Attribution & Prioritization Ranker (XGBoost)
            │
            ▼
DOWNSTREAM PIPELINE
  ├── Lagrangian Drift Trajectory Modeling (Phase 4)
  └── Evidence Dashboard & FastAPI Service (Phase 5)
```

---

## Phase 3: AI Model Suite

### 1. SAR Spill Segmentation (`scripts/models/segmentation/`)
- **Model**: PyTorch U-Net with skip connections, configurable base filters, and composite Binary Cross Entropy + Soft Dice loss (`BCEDiceLoss`).
- **Input**: Sentinel-1 SAR imagery (amplitude or decibel intensity) normalized to `[0.0, 1.0]`.
- **Output**: Pixel-level binary mask and continuous probability map of low-backscatter candidate regions.
- **Metrics**: IoU (Jaccard Index), Dice coefficient (F1), Precision, Recall.

### 2. Look-Alike Classifier (`scripts/models/classification/`)
- **Model**: XGBoost Gradient-Boosted Decision Trees (`XGBClassifier`).
- **Input**: Radiometric features (mean, min, max, variance, skewness), geometric morphology (area, perimeter, compactness, aspect ratio), boundary contrast ratios, and oceanographic context (local wind speed and surface current velocity).
- **Output**: Probabilistic classification distinguishing true mineral oil slicks from natural look-alikes (low-wind calm seas, biogenic/algal films, internal waves).

### 3. Vessel Prioritization & Ranking (`scripts/models/ranking/`)
- **Model**: XGBoost attribution and ranking model.
- **Input**: Spatio-temporal proximity (Haversine distance, temporal offset), trajectory proximity score, kinematic anomalies (speed variance, sudden speed drops), heading deviation, and oceanographic drift-corrected origin distance.
- **Output**: Ranked prioritization score for each candidate vessel.

---

## Operational & Legal Disclaimers

> [!IMPORTANT]
> - **Dark SAR formations are not automatically oil spills**: Surface tension phenomena, biogenic sheens, rain cells, and wind shadows (< 3 m/s) produce low radar backscatter look-alikes. Detections must be screened by the look-alike classifier and validated with oceanographic context.
> - **Vessel ranking scores are NOT legal proof**: Prioritization scores indicate spatio-temporal and kinematic correlation with the estimated spill origin. A high rank is an **investigative prioritization metric** to direct authority inspections, not evidence of causation or guilt.

---

## CLI Usage

### Train All Models (Pipeline Verification)
```bash
python scripts/train_models.py --model all --use-synthetic
```

### Train Individual Models
```bash
# SAR Segmentation U-Net
python scripts/train_models.py --model segmentation --use-synthetic --epochs 5

# Look-Alike Classifier
python scripts/train_models.py --model classification --use-synthetic

# Vessel Ranking Model
python scripts/train_models.py --model ranking --use-synthetic
```

### Model Artifact Registry
Trained checkpoints and standardized metadata are written to `models/`:
- `models/segmentation/sar_unet_weights.pt` & `segmentation_metadata.json`
- `models/classification/sar_lookalike_classifier.json` & `classification_metadata.json`
- `models/ranking/vessel_ranking_model.json` & `ranking_metadata.json`
