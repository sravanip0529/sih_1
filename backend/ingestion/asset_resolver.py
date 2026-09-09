from dataclasses import dataclass

from backend.ingestion.stac_service import Scene


REQUIRED_ASSETS = ("blue", "green", "red", "nir", "swir16")


@dataclass(frozen=True)
class AssetSelection:
    assets: dict[str, str]
    missing: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not self.missing


def resolve_assets(scene: Scene, required: tuple[str, ...] = REQUIRED_ASSETS) -> AssetSelection:
    assets = {key: scene.assets[key] for key in required if key in scene.assets}
    return AssetSelection(assets=assets, missing=tuple(key for key in required if key not in assets))