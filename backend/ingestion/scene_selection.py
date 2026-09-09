from dataclasses import dataclass
from datetime import date, datetime

from backend.ingestion.asset_resolver import AssetSelection, REQUIRED_ASSETS, resolve_assets
from backend.ingestion.stac_service import Scene


@dataclass(frozen=True)
class SelectionResult:
    scene: Scene
    assets: AssetSelection
    reason: str


def select_scene(
    scenes: list[Scene],
    requested_date: date,
    required: tuple[str, ...] = REQUIRED_ASSETS,
) -> SelectionResult:
    candidates = []
    for scene in scenes:
        assets = resolve_assets(scene, required)
        if assets.complete:
            distance = abs((scene.datetime.date() - requested_date).days)
            cloud = scene.cloud_cover if scene.cloud_cover is not None else 100.0
            candidates.append((cloud, distance, scene.scene_id, scene, assets))
    if not candidates:
        raise ValueError("No candidate scene contains all required Sentinel-2 assets")
    cloud, distance, scene_id, scene, assets = min(candidates)
    return SelectionResult(
        scene=scene,
        assets=assets,
        reason=f"lowest metadata cloud cover ({cloud:.2f}%), then {distance} days from requested date, then scene ID {scene_id}",
    )