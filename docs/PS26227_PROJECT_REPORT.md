# PS26227 — Semantic Retrieval and Multi-Temporal Change Analysis of Satellite Imagery

## 1. Executive Summary

This project creates a complete pipeline that transforms multi-temporal satellite imagery into structured, searchable, and evidence-based change information. Instead of requiring analysts to inspect thousands of pixels manually, the system prepares the imagery, filters unreliable observations, detects spectral change, groups the most meaningful changes into spatial regions, embeds those regions semantically, and supports natural-language retrieval over the detected results.

The system is designed to remain scientifically careful. It does not confuse semantic similarity with verified classification or probability. Instead, it preserves traceability to the underlying raster evidence, the region metadata, and the retrieval outputs.

## 2. Core Problem

Monitoring environmental and urban change across time is essential for planning, environmental management, disaster response, and infrastructure analysis. However, multi-temporal Earth observation data is large, noisy, and difficult to interpret by manual inspection alone.

Typical challenges include:

- repeated satellite imagery over large areas
- cloud contamination and missing values
- varying sensor conditions and geometry
- the need to isolate meaningful change from noise
- difficulty searching large collections of detected changes using human language

This project addresses those issues by converting raw image differences into structured change regions that can be searched semantically and inspected with measurable evidence.

## 3. Project Goal

The project aims to:

- process real multi-temporal Sentinel-2 observations
- remove unreliable pixels using quality and cloud masks
- detect spectral change across dates
- convert change pixels into contiguous regions
- generate region-level metadata and summaries
- encode region meaning through embeddings
- allow user-friendly natural-language queries over the region index
- present evidence-backed, traceable outputs through an API and UI

## 4. System Architecture Overview

The architecture follows a scientific workflow:

Satellite imagery -> quality-aware processing -> change detection -> change regions -> embeddings -> semantic search -> evidence output

This is implemented across the project’s core modules:

- backend ingestion and geospatial preparation
- cloud and quality masking
- raster and spectral processing
- region extraction and summarization
- vector search and retrieval
- interpretation and API integration
- frontend visualization

## 5. Module-by-Module Explanation

### 5.1 Data Ingestion and STAC Access

Relevant modules:

- [backend/ingestion/aoi.py](../backend/ingestion/aoi.py)
- [backend/ingestion/asset_resolver.py](../backend/ingestion/asset_resolver.py)
- [backend/ingestion/downloader.py](../backend/ingestion/downloader.py)
- [backend/ingestion/stac_service.py](../backend/ingestion/stac_service.py)
- [backend/ingestion/provenance.py](../backend/ingestion/provenance.py)

This stage acquires the satellite data and metadata. It identifies the target area, searches the STAC catalog, resolves the required Sentinel-2 assets, and records provenance information about the source scene selection and download process.

Why it matters:

- keeps the workflow reproducible
- tracks source and acquisition date information
- validates that the right imagery is retrieved before analysis
- allows downstream processing to remain traceable

### 5.2 Raster Preparation and Harmonization

Relevant modules:

- [backend/processing/grid.py](../backend/processing/grid.py)
- [backend/processing/raster_harmonizer.py](../backend/processing/raster_harmonizer.py)
- [backend/processing/rgb_preview.py](../backend/processing/rgb_preview.py)

After downloading the data, the system prepares the imagery on a common spatial grid. This ensures that pixels from different dates line up consistently enough for comparison in the same coordinate system.

The pipeline uses a shared reference grid, reprojects the imagery, and aligns the required bands to the same resolution and CRS. A preview generation step also creates visualization outputs for human interpretation without altering scientific data.

Why it matters:

- reduces false differences caused by geometry mismatches
- standardizes raster resolution and projection
- creates consistent inputs for subsequent change detection

### 5.3 Quality and Cloud Masking

Relevant modules:

- [backend/processing/cloud/input_builder.py](../backend/processing/cloud/input_builder.py)
- [backend/processing/cloud/provider.py](../backend/processing/cloud/provider.py)
- [backend/processing/cloud/quality_mask.py](../backend/processing/cloud/quality_mask.py)
- [backend/processing/cloud/s2cloudless_service.py](../backend/processing/cloud/s2cloudless_service.py)
- [backend/processing/cloud/scl_provider.py](../backend/processing/cloud/scl_provider.py)
- [backend/quality](../backend/quality)

No image comparison is reliable unless invalid or obstructed pixels are excluded. These modules build masks for clouds, no-data regions, and other unreliable observations. The system distinguishes valid pixels from cloud-covered or missing regions before computing change measures.

Why it matters:

- prevents false change detections near cloud cover
- improves confidence in the resulting signal
- keeps the analysis focused on jointly valid observations

### 5.4 Change Detection

Relevant modules:

- [backend/processing/change_detection.py](../backend/processing/change_detection.py)
- [backend/processing/statistics.py](../backend/processing/statistics.py)

This is the measurement stage. The system compares the reference and moving images across bands such as blue, green, red, near-infrared, and SWIR. It computes signed differences and combines them into a change magnitude map that indicates where the signal deviates most strongly between the dates.

This stage produces spectral difference evidence rather than a final classification of land-cover change.

Why it matters:

- identifies where change is strongest in the image pair
- maintains a measurable, interpretable signal for every region
- creates the basis for later region grouping and retrieval

### 5.5 Region Extraction and Spatial Grouping

Relevant modules:

- [backend/processing/regions.py](../backend/processing/regions.py)

Once a change magnitude map is built, the system groups nearby changed pixels into connected regions. Each region receives a unique identity, footprint, pixel count, area estimate, centroid, and change statistics such as mean, median, and maximum magnitude.

This step turns raw pixel-level evidence into interpretable spatial objects. Instead of analyzing a huge mask as thousands of independent points, the workflow works with coherent regions.

Why it matters:

- simplifies downstream analysis
- preserves spatial structure
- generates human-readable region summaries
- supports natural-language and evidence-based search

### 5.6 Embeddings and Semantic Retrieval

Relevant modules:

- [backend/embeddings/region_embeddings.py](../backend/embeddings/region_embeddings.py)
- [backend/processing/retrieval/query.py](../backend/processing/retrieval/query.py)
- [backend/query](../backend/query)

The region metadata is transformed into vector representations. These embeddings capture the semantic meaning of each region based on its spectral and descriptive attributes. A user can then search for concepts such as:

- vegetation-related spectral change
- urban expansion patterns
- water or moisture-related changes
- disturbed land areas

The retrieval layer encodes the user query using a sentence-transformer model, searches the region-index database, and returns the most relevant regions.

Why it matters:

- enables natural-language exploration of large change datasets
- moves beyond manual visual inspection
- supports domain queries without requiring image-by-image review

### 5.7 Vector Store and Search Index

Relevant modules:

- [backend/database/qdrant_client.py](../backend/database/qdrant_client.py)
- [backend/database/postgres_client.py](../backend/database/postgres_client.py)

The vector database stores the region embeddings and allows vector similarity search. In this project, Qdrant is used for the region index. The backend can query the index for the nearest semantic matches and then resolve those matches back to the original region metadata.

This gives the system its retrieval behavior: query text -> embedding -> nearest regions -> evidence retrieval.

Why it matters:

- efficient similarity search over many region vectors
- scalable retrieval for high-volume Earth observation analysis
- clean separation between data storage and application logic

### 5.8 Interpretation and Evidence Resolution

Relevant modules:

- [backend/processing/interpretation/result_resolver.py](../backend/processing/interpretation/result_resolver.py)
- [backend/processing/interpretation/evidence_builder.py](../backend/processing/interpretation/evidence_builder.py)
- [backend/processing/interpretation/provenance.py](../backend/processing/interpretation/provenance.py)
- [backend/processing/interpretation/spectral_interpreter.py](../backend/processing/interpretation/spectral_interpreter.py)

The retrieval layer returns indices and similarity scores, but the project resolves each match back to actual region metadata to build a scientifically honest evidence record. This includes spectral summaries, area, pixel counts, and cautious interpretation language.

The module emphasizes that these outputs are not land-cover classifications. They are evidence-based descriptions generated from measured image signals.

Why it matters:

- provides traceability to original region artifacts
- keeps scientific interpretation grounded in data
- supports transparent, explainable retrieval outputs

### 5.9 Backend API Layer

Relevant modules:

- [backend/main.py](../backend/main.py)
- [backend/api/retrieval.py](../backend/api/retrieval.py)
- [backend/settings.py](../backend/settings.py)

The FastAPI application exposes endpoints for health checking and retrieval. The search API accepts a user query, validates the request, executes the retrieval pipeline, and returns region-level results in a structured format. It also includes metadata such as dates, model name, collection name, and scientific limitations.

Why it matters:

- turns the retrieval workflow into a usable service
- supports frontend integration and external tooling
- exposes a clean contract for downstream applications

### 5.10 Frontend Visualization Interface

Relevant modules:

- [frontend/src/App.jsx](../frontend/src/App.jsx)
- [frontend/src/main.jsx](../frontend/src/main.jsx)
- [frontend/src/styles.css](../frontend/src/styles.css)

The frontend provides a simple search experience where users can enter a natural-language prompt such as “Find regions with strong vegetation-related spectral change,” adjust the number of returned results, and inspect the evidence behind each match.

Why it matters:

- makes the project accessible to non-experts
- shows how change regions are represented and queried
- keeps the system understandable while preserving scientific caution

## 6. End-to-End Workflow

The project operates as follows:

1. Acquire Sentinel-2 scene pairs for the same area at different dates.
2. Validate and prepare the data on a common grid.
3. Apply quality and cloud masks to remove unreliable pixels.
4. Compare bands and compute spectral change magnitude.
5. Separate change pixels from non-change pixels using a threshold.
6. Group connected changed pixels into spatial regions.
7. Compute region statistics and generate semantic summaries.
8. Create embeddings for each region.
9. Index the embeddings in Qdrant.
10. Accept user query text and search the region index.
11. Resolve retrieved results back to the regional evidence.
12. Return interpretable outputs through the API and frontend.

## 7. Real-World Applications

### 7.1 Agriculture and Crop Monitoring

- detect vegetation stress patterns across seasons
- compare crop health before and after extreme weather events
- identify anomalous growth or seasonal changes

### 7.2 Urban Growth and Land Use Change

- monitor urban expansion, impervious surface changes, and informal development
- support planning decisions and resource allocation
- enable evidence-based review of land transformation patterns

### 7.3 Environmental Monitoring and Forest Change

- detect disturbed forest areas, canopy change, and vegetation loss
- support ecological assessment and conservation planning
- help monitor areas affected by fire, drought, or deforestation

### 7.4 Water and Wetland Management

- track changes in water extent, moisture anomalies, and wetlands
- detect shifts in aquatic habitats and hydrological stress
- support planning for drought and flood response

### 7.5 Disaster Response and Infrastructure Planning

- identify affected zones after storms, floods, or landscape disturbance
- support rapid situational awareness
- assist damage assessment workflows by narrowing areas of interest

## 8. Scientific Responsibilities and Limitations

The project is intentionally careful about what it claims. It does not present semantic similarity as certainty, and it does not claim that a spectral change automatically equals a verified real-world event.

Important constraints:

- semantic retrieval is not ground-truth classification
- retrieval similarity score is not a probability
- spectral change evidence requires domain validation and contextual review
- external ground-truth data may be needed for operational deployment

This makes the project stronger, not weaker: it is honest about evidence, traceability, and uncertainty.

## 9. Why This Project Matters

This project bridges the gap between raw Earth observation data and actionable, searchable information. It demonstrates how satellite imagery can move from passive observation into an evidence-driven analysis system capable of natural-language interpretation.

This is valuable for:

- public-sector decision making
- environmental monitoring
- research workflows
- geospatial intelligence systems
- scalable remote sensing applications

## 10. Conclusion

PS26227 demonstrates a practical and scientifically grounded approach to multi-temporal satellite analysis. It does not simply compare two images. Instead, it builds a pipeline that converts spectral change into structured regions, indexes those regions semantically, and makes them searchable through natural language while preserving evidence and uncertainty.

This makes the project highly relevant for real-world remote sensing challenges where interpretability, traceability, and usability matter as much as detection performance.
