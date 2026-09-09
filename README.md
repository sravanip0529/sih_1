# Satellite Semantic Retrieval and Multi-Temporal Change Analysis System

PS26227 - Semantic Retrieval and Multi-Temporal Change Analysis of Satellite Imagery.

## Phase 0 constraints

The initial development environment was inspected on 2026-09-09:

- OS: Ubuntu 24.04.4 LTS
- CPU: 2 vCPUs
- Memory: approximately 8 GiB RAM, no swap
- Storage: approximately 19 GiB available in the workspace
- Python: 3.14.2
- Node.js: 24.20.0
- Docker: 29.7.2 with Compose v5.5.0
- GPU: no NVIDIA GPU detected
- Backend Python baseline: 3.11 (container image: `python:3.11-slim`)

This is suitable for API, database, ingestion, and small sample-data work. Heavy embedding and change-detection inference should use CPU-compatible checkpoints, a machine with more memory, or a separate GPU workstation. Keep the local demo dataset small; reserve at least 20 GiB additional storage for staged imagery and model weights on a fuller development machine.

## Phase 2 status

The backend foundation uses Python 3.11, which has broad wheel support for PyTorch, Rasterio/GDAL, GeoPandas, and FastAPI. Lightweight API, database, vector-store, STAC, numeric, image-processing, and geospatial dependencies are installed; model packages, checkpoints, and datasets are intentionally excluded.

Required dependencies are listed in `backend/requirements.txt`. Sentinel-2 cloud masking is isolated in `backend/requirements-optional.txt` and is not installed yet. Future Open-CD, Clay, CLIP-RSICD, and other model dependencies will be selected only after checkpoint and license verification.

CPU-only development supports API work, metadata handling, small raster operations, vector operations, and lightweight tests. Deep change detection and remote-sensing embedding generation may be slow on CPU and should use an NVIDIA GPU, external GPU machine, or cloud inference for larger experiments.

Run the environment import check with:

```bash
docker compose run --rm backend python /app/scripts/verify_backend_environment.py
```

The detailed service check is available at `http://localhost:8000/health/detailed` and reports PostgreSQL and Qdrant connectivity independently.

## Phase 1 status

This repository currently contains the project structure and runnable service skeleton only. No model checkpoint or remote dataset is downloaded yet. The two embedding spaces remain separate by design:

- `semantic`: CLIP-RSICD-compatible vectors for text/image retrieval
- `spectral`: Clay-compatible vectors for multispectral analysis

Model checkpoints, licenses, and dimensions must be verified before implementation in a later phase.

## Phase status overview

The project has progressed through the full workflow in a scientific, phase-based sequence. The current implementation status is summarized below.

| Phase | Focus | Status | Notes |
|---|---|---|---|
| Phase 0 | Environment and constraints | Complete | Host and container baseline verified; tooling and limits documented. |
| Phase 1 | Repository and service foundation | Complete | Core project structure and backend/frontend scaffolding ready. |
| Phase 2 | Backend dependency and service foundation | Complete | Python, API, Qdrant/Postgres runtime setup validated. |
| Phase 3 | Sentinel-2/STAC sample acquisition | Complete | Real sample scenes acquired and provenance recorded. |
| Phase 4 | Raster preparation and common grid | Complete | Real Sentinel-2 bands reprojected and prepared on a common 10 m grid. |
| Phase 5 | Quality and cloud masking | Complete | Cloud/no-data quality masks generated and used in analysis. |
| Phase 6 | Geometric alignment and temporal registration | Complete | Alignment workflow and validation implemented for the project dataset. |
| Phase 7 | Radiometric normalization | Complete | Normalized output prepared for consistent cross-date comparison. |
| Phase 8 | Change detection | Complete | Change magnitude and masks computed from multi-date spectral differences. |
| Phase 9 | Region extraction and metadata generation | Complete | Connected change evidence converted into region-level artifacts. |
| Phase 10 | Region embeddings and vector indexing | Complete | Region metadata embedded and stored in Qdrant. |
| Phase 11 | Semantic retrieval over real indexed regions | Complete | Natural-language query execution over the real region index validated. |
| Phase 12 | Retrieval-grounded evidence interpretation | Complete | Retrieved results resolved back to region metadata with cautious interpretation. |
| Phase 13 | Retrieval API and backend integration | Complete | FastAPI endpoints expose the validated retrieval workflow. |
| Phase 14 | Frontend retrieval interface and visualization | Complete | Retrieval UI is connected to the backend and presents evidence-backed results. |

### Current project boundary

The project is currently validated through the end-to-end retrieval stack: Sentinel imagery -> processing -> change detection -> region extraction -> embeddings -> Qdrant retrieval -> evidence interpretation -> API -> frontend interface.

The system intentionally preserves scientific caution: retrieval similarity is treated as similarity evidence, not a probability or ground-truth classification.

## Repository layout

```text
backend/       FastAPI service and domain modules
frontend/      React + Vite dashboard
database/      SQL initialization and migrations
docker/        Container build files
data/          Raw, staging, processed, aligned, masks, changes, embeddings, and model data
configs/       Versioned model and runtime configuration
evaluation/    Retrieval and change-detection evaluation code
scripts/       Offline staging and operational scripts
tests/         Unit and integration tests
```

## Start the foundation

1. Copy `.env.example` to `.env` and adjust credentials if needed.
2. Validate the Compose file:

	```bash
	docker compose config
	```

3. Start the database, vector store, API, and frontend:

	```bash
	docker compose up --build
	```

4. Verify:

	```bash
	curl http://localhost:8000/health
	curl http://localhost:6333/healthz
	```

The API is available at `http://localhost:8000/docs` and the dashboard at `http://localhost:5173`.

## Data contract

```text
data/
├── raw/sentinel/   source Sentinel scenes or COGs
├── raw/samples/    small committed test assets only
├── staging/        transient ingestion staging
├── processed/      normalized and tiled imagery
├── aligned/        registered image pairs
├── masks/          cloud and change masks
├── changes/        change evidence and summaries
├── embeddings/     generated vector artifacts
├── evaluation/     local evaluation inputs and outputs
├── temp/            disposable processing files
└── models/         locally staged model files
```

Large imagery, model weights, generated artifacts, and temporary files are ignored by Git. Do not commit satellite scenes or checkpoints; only small, redistributable sample assets should be placed under `data/raw/samples/`.

## Configuration

`.env.example` documents application, database, Qdrant, STAC, processing, and storage settings. The typed configuration is centralized in `backend/settings.py`; modules should not read environment variables directly. `configs/processing.yaml` contains engineering defaults that must be validated against real data before scientific use, while `configs/model_versions.yaml` is configuration-only until model licenses and checkpoints are verified.

## Native frontend setup

```bash
cd frontend
npm install
npm run dev
```

## Native backend setup

Python 3.11 is the recommended local version for the eventual geospatial and ML dependency set. The host currently has Python 3.14, so use Python 3.11 before installing model dependencies. The Docker backend already provides Python 3.11.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

Run service checks with:

```bash
./scripts/check_services.sh
```

## Phase 3: Sentinel-2/STAC sample workflow

The reproducible Phase 3 workflow is implemented in `scripts/run_sample_workflow.py`:

```text
AOI -> STAC search -> metadata cloud filter -> deterministic scene selection
		-> required asset validation -> atomic download -> provenance sidecar
```

The default provider is Earth Search by Element 84:

- STAC API: `https://earth-search.aws.element84.com/v1`
- Collection: `sentinel-2-l2a`
- Asset mapping: `blue`=`B02`, `green`=`B03`, `red`=`B04`, `nir`=`B08`, `swir16`=`B11`
- Provider assets are public Sentinel-2 COGs and require no credentials in this sample.

Run discovery without downloading files:

```bash
docker run --rm --network host \
	-e STAC_API_URL=https://earth-search.aws.element84.com/v1 \
	-e STAC_COLLECTION=sentinel-2-l2a \
	-v "$PWD/data:/app/data" \
	sih_1-backend python /app/scripts/run_sample_workflow.py --metadata-only
```

Run the full sample download using the same command without `--metadata-only`. The sample configuration is [configs/sample_sentinel.yaml](configs/sample_sentinel.yaml), with a small Berlin bbox and June 2023/June 2024 windows. Assets are stored under `data/raw/sentinel/<acquisition-date>/<scene-id>/assets/`, with a `metadata.json` provenance sidecar.

The validated run selected:

- Date A: `S2A_33UUU_20230605_0_L2A`, acquisition `2023-06-05T10:26:14Z`, 4 candidates, metadata cloud cover `0.629341%`.
- Date B: `S2A_32UQD_20240626_0_L2A`, acquisition `2024-06-26T10:16:17Z`, 6 candidates, metadata cloud cover `1.671969%`.

The ranking policy is lowest metadata cloud cover, then closest acquisition date to the requested date, then stable scene ID. The sample downloaded 10 full COG assets, approximately 1.9 GB total. Full COG downloads were used because the provider exposes public COG URLs but no configured server-side AOI subset; later preprocessing can read windows without duplicating the source files.

STAC cloud cover is metadata-level filtering only. It does not remove clouds or establish pixel-level cloud-free imagery. Pixel masking, alignment, radiometric normalization, indices, change detection, embeddings, vector indexing, and map visualization remain deferred.

## Phase 4: Sentinel-2 asset preparation and raster validation

Run the real Phase 4 workflow with:

```bash
docker compose run --rm backend python /app/scripts/run_raster_preparation.py
```

The workflow reads the Phase 3 raw COGs window-by-window, transforms the AOI into each source CRS, and reprojects each required band directly onto one common AOI grid. The default grid is `EPSG:32633`, 10 m pixels, with zero buffer. EPSG:32633 is the UTM zone containing the AOI centroid and is suitable for metric pixel operations. Date B is transformed from EPSG:32632; no AROSICS registration or sub-pixel alignment is performed.

Required bands are `blue`, `green`, `red`, `nir`, and `swir16`. B02/B03/B04/B08 source bands are approximately 10 m; B11 is approximately 20 m. All are written to the common 10 m grid with bilinear resampling. Source values and scaling are preserved; no radiometric normalization is applied.

Prepared outputs are written separately from immutable raw data:

```text
data/processed/sentinel/
├── 2023-06-05/
│   ├── blue.tif ... swir16.tif
│   ├── rgb_preview.tif
│   └── metadata.json
├── 2024-06-26/
│   ├── blue.tif ... swir16.tif
│   ├── rgb_preview.tif
│   └── metadata.json
└── preparation_report.json
```

The validated sample grid is 140 x 171 pixels with transform origin `(390380, 5820110)` and bounds `(390380, 5818400, 391780, 5820110)`. The preparation report contains source metadata, AOI/grid details, nodata policy, band statistics, preview normalization, and exact cross-date grid validation.

RGB previews use a reproducible 2nd-98th percentile stretch for visualization only. Scientific prepared rasters are not modified by preview normalization.

Phase 4 establishes a common CRS, resolution, and raster grid. It does not claim geometric registration, sub-pixel alignment, radiometric comparability, or readiness for reliable pixel-level change detection.

## Phase 5.1 status: cloud-mask provider resolution

The Phase 5 cloud-mask architecture and tests are present in `backend/processing/cloud/` and `scripts/run_cloud_mask_workflow.py`. The validated `s2cloudless` 1.7.0 model initializes and runs CPU inference on synthetic ten-band input. It requires the exact bands B01, B02, B04, B05, B08, B8A, B09, B10, B11, and B12, with model-only scaling from stored Sentinel values to reflectance fractions.

Phase 5.1 selects the provider-native Sentinel-2 Scene Classification Layer (`sentinel_scl`) for the exact L2A observations. It requires no B10 substitution and executes locally after the small SCL COGs are staged. SCL classes 0/1 are nodata, classes 3/8/9/10 are mapped to the conservative excluded quality class 1, and classes 4/5/6/7/11 remain valid. The provider comparison is recorded in `configs/cloud_provider_matrix.yaml`.

The real two-date workflow generated categorical SCL, cloud-mask, and quality-mask outputs. It does not fabricate a cloud probability raster because the selected provider is categorical rather than probabilistic. The original s2cloudless path remains available by explicit configuration and fallback remains disabled.

## Scope boundary

Phase 5.1 intentionally does not claim geometric registration, sub-pixel alignment, radiometric normalization, NDVI, NDWI, change detection, embeddings, Qdrant indexing, or frontend visualization.

The next boundary is Phase 6: geometric registration and temporal alignment.