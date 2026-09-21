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

---

## Phase 4: Drift & Attribution Pipeline (`scripts/drift/`)

Phase 4 connects satellite detections with ocean physics to forecast slick movement and back-trace candidate spill sources:

1. **Lagrangian Transport Model**:
   $$\vec{v}_{\text{particle}} = \vec{v}_{\text{current}} + c_w \cdot \vec{v}_{\text{wind}}$$
   where $\vec{v}_{\text{current}}$ is ocean surface current $(u_o, v_o)$, $\vec{v}_{\text{wind}}$ is 10m wind vector $(u_{10}, v_{10})$, and $c_w \approx 0.03$ (3% leeway factor).

2. **Forward & Backward Trajectory Simulation**:
   - **Forward Drift**: Forecasts slick dispersion over $+24$ to $+72$ hours.
   - **Backward Drift**: Backtracks slick motion over $-48$ hours to delineate an **estimated possible source region**.

3. **Monte Carlo Particle Ensemble**:
   - Perturbs initial position ($\sigma \sim 300\text{ m}$) and windage leeway ($c_w \sim \mathcal{N}(0.03, 0.005)$).
   - Generates empirical 95% dispersion radius, bounding box, and convex hull polygon.

4. **AIS Track Correlation & Phase 3 Scoring**:
   - Correlates vessel AIS tracks with the backward drift trajectory and estimated source region.
   - Extracts trajectory proximity, temporal offset, speed anomalies, and drift-corrected distance.
   - Scores candidate vessels using the Phase 3 XGBoost attribution model.

### Phase 4 CLI Usage
```bash
# Execute end-to-end drift and vessel attribution
python scripts/run_drift_attribution.py --event wakashio

# Custom simulation parameters
python scripts/run_drift_attribution.py --event wakashio --forward-hours 48 --backward-hours 72 --particles 50
```

### Phase 4 Output Artifacts
Structured data outputs are written to `data/drift/` and `data/attribution/`:
- `data/drift/<event>/processed/forward_trajectory.csv`
- `data/drift/<event>/processed/backward_trajectory.csv`
- `data/drift/<event>/processed/ensemble_trajectories.csv`
- `data/drift/<event>/processed/source_region.json`
- `data/drift/<event>/processed/drift_metadata.json`
- `data/attribution/<event>/processed/vessel_features.csv`
- `data/attribution/<event>/processed/vessel_candidates.json`
- `data/attribution/<event>/processed/attribution_metadata.json`

---

## Phase 5: FastAPI Backend & Orchestration Service (`api/`)

Phase 5 exposes the OceanEye intelligence pipeline through high-performance REST and GeoJSON endpoints, powering the evidence dashboard frontend.

### Architecture

```
api/
├── main.py                  # Application entry point, CORS, and global error handlers
├── config.py                # Operational settings, safety thresholds, and legal disclaimers
├── dependencies.py          # Shared dependencies and structured logger
├── schemas/                 # Pydantic validation models
│   ├── common.py            # GeoJSON geometries, status, and health models
│   ├── events.py            # Event summaries and detail models
│   ├── detection.py         # Sentinel-1 SAR metadata and detection models
│   ├── drift.py             # Trajectory, polygon, and simulation schemas
│   └── attribution.py       # Ranked vessel candidate models
├── routes/                  # Modular endpoint routers
│   ├── root.py              # GET / and GET /health
│   ├── events.py            # GET /api/events, GET /api/events/{event_id}
│   ├── detection.py         # GET /api/events/{event_id}/detection
│   ├── drift.py             # GET /api/events/{event_id}/drift, POST /api/drift/simulate
│   └── attribution.py       # GET /api/events/{event_id}/attribution
├── services/                # Business logic and data layer
│   ├── event_service.py     # Dynamic event resolution
│   ├── detection_service.py # Sentinel metadata & strict null geometry enforcement
│   ├── drift_service.py     # Stored outputs and on-demand Lagrangian simulations
│   └── attribution_service.py # Suspect vessel prioritization retrieval
└── utils/
    └── geojson.py           # RFC 7946 GeoJSON converters ([lon, lat] coordinate ordering)
```

### Installation & Server Execution

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start FastAPI Development Server**:
   ```bash
   uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
   ```

3. **Interactive OpenAPI / Swagger Documentation**:
   - Swagger UI: `http://127.0.0.1:8000/docs`
   - ReDoc UI: `http://127.0.0.1:8000/redoc`

### API Endpoints

| Method | Endpoint | Description | Key Response Fields |
|---|---|---|---|
| `GET` | `/` | System landing & service status | `status`, `app_name`, `version`, `docs_url` |
| `GET` | `/health` | Health check endpoint | `status`, `version`, `timestamp` |
| `GET` | `/api/events` | List all configured incidents | `event_id`, `name`, `latitude`, `longitude`, `radius_km` |
| `GET` | `/api/events/{event_id}` | Event details & data availability | `bounding_box`, `data_availability` |
| `GET` | `/api/events/{event_id}/detection` | Sentinel-1 SAR metadata & detection | `geometry: null`, `footprint_polygon`, `platform`, `sensor_mode` |
| `GET` | `/api/events/{event_id}/drift` | Stored forward/backward trajectories & source region | GeoJSON `LineString` & `Polygon` features (`[lon, lat]`) |
| `GET` | `/api/events/{event_id}/attribution` | Suspect vessel prioritization ranks | Ranked candidates, `responsibility_confirmed: false`, features |
| `POST` | `/api/drift/simulate` | On-demand Lagrangian drift simulation | Forward/backward GeoJSON `LineString`, source `Polygon` |

### Example Requests & Responses

#### 1. On-Demand Drift Simulation (`POST /api/drift/simulate`)
```bash
curl -X POST http://127.0.0.1:8000/api/drift/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": -19.79856,
    "longitude": 57.88786,
    "timestamp": "2020-08-10T01:37:55Z",
    "forward_duration_hours": 12.0,
    "backward_duration_hours": 12.0,
    "timestep_seconds": 1800,
    "windage": 0.03,
    "particle_count": 10,
    "event_id": "wakashio"
  }'
```

**Response**:
```json
{
  "is_simulation": true,
  "simulation_type": "on_demand_simulation",
  "forward_trajectory": {
    "type": "Feature",
    "geometry": {
      "type": "LineString",
      "coordinates": [[57.88786, -19.79856], [57.87113, -19.7858]]
    },
    "properties": {"steps": 25, "duration_hours": 12.0}
  },
  "backward_trajectory": {
    "type": "Feature",
    "geometry": {
      "type": "LineString",
      "coordinates": [[57.88786, -19.79856], [57.9039, -19.8118]]
    }
  },
  "source_region": {
    "type": "Feature",
    "geometry": {
      "type": "Polygon",
      "coordinates": [[[57.9659, -19.8844], [57.9857, -19.8922], [57.9659, -19.8844]]]
    }
  },
  "summary": {
    "dispersion_radius_95_km": 1.24
  }
}
```

### Operational Limitations & Legal Notice

> [!IMPORTANT]
> - **Detection Geometry Contract**: In the current version, satellite scene footprint bounds indicate sensor image boundaries and do not constitute a pixel-level oil slick segmentation. The detection endpoint strictly returns `geometry: null` until verified pixel segmentation is generated.
> - **Prioritization Is Not Proof of Responsibility**: All prioritization scores represent statistical spatio-temporal and kinematic correlations. Candidate ranks and scores **DO NOT** constitute legal proof, evidence of liability, or confirmation of oil discharge.
> - **Synthetic Benchmark Notice**: When real AIS or labeled SAR training annotations are unavailable, the pipeline operates in synthetic benchmark mode for pipeline verification.
