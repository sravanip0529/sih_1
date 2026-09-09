from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = "postgresql://satellite:change-me-for-local-use@localhost:5432/satellite"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    service_timeout_seconds: float = 2.0
    stac_api_url: str = "https://earth-search.aws.element84.com/v1"
    stac_collection: str = "sentinel-2-l2a"
    stac_provider: str = "Earth Search by Element 84"
    processing_resolution_m: int = 10
    processing_target_crs: str = "EPSG:32633"
    aoi_buffer_meters: float = 0.0
    continuous_resampling_method: str = "bilinear"
    output_nodata: float = 0.0
    rgb_preview_enabled: bool = True
    rgb_preview_percentile_low: float = 2.0
    rgb_preview_percentile_high: float = 98.0
    cloud_coverage_threshold: float = 20.0
    cloud_probability_threshold: float = 0.4
    cloud_model: str = "s2cloudless"
    cloud_provider: str = "sentinel_scl"
    cloud_allow_fallback: bool = False
    cloud_mask_refinement_enabled: bool = False
    cloud_mask_dilation_pixels: int = 0
    cloud_mask_erosion_pixels: int = 0
    quality_mask_valid_value: int = 0
    quality_mask_cloud_value: int = 1
    quality_mask_nodata_value: int = 2
    quality_output_nodata: int = 255
    stac_search_timeout_seconds: float = 30.0
    download_timeout_seconds: float = 120.0
    max_download_bytes: int = 500_000_000
    raw_data_directory: Path = Path("data/raw")
    sentinel_data_directory: Path = Path("data/raw/sentinel")
    staging_data_directory: Path = Path("data/staging")
    data_directory: Path = Path("data")
    processed_data_directory: Path = Path("data/processed")
    model_directory: Path = Path("data/models")
    temp_data_directory: Path = Path("data/temp")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_cloud_configuration(self) -> "Settings":
        if not 0 <= self.cloud_probability_threshold <= 1:
            raise ValueError("CLOUD_PROBABILITY_THRESHOLD must be between 0 and 1")
        if self.cloud_mask_dilation_pixels < 0 or self.cloud_mask_erosion_pixels < 0:
            raise ValueError("Cloud mask morphology sizes must not be negative")
        classes = (self.quality_mask_valid_value, self.quality_mask_cloud_value, self.quality_mask_nodata_value)
        if len(set(classes)) != 3:
            raise ValueError("Quality mask class values must be distinct")
        if self.cloud_model != "s2cloudless":
            raise ValueError("Only the validated s2cloudless cloud model is supported")
        if self.cloud_provider not in {"sentinel_scl", "s2cloudless"}:
            raise ValueError("CLOUD_PROVIDER must be sentinel_scl or s2cloudless")
        return self


settings = Settings()