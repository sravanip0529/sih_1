from pathlib import Path

import numpy as np
import rasterio


def create_rgb_preview(red: Path, green: Path, blue: Path, destination: Path, low: float = 2.0, high: float = 98.0) -> None:
    with rasterio.open(red) as r, rasterio.open(green) as g, rasterio.open(blue) as b:
        arrays = [r.read(1, masked=True), g.read(1, masked=True), b.read(1, masked=True)]
        profile = r.profile.copy()
        output = []
        for array in arrays:
            valid = array.compressed()
            if valid.size == 0:
                raise ValueError("Cannot create RGB preview from an empty raster")
            lo, hi = np.percentile(valid, [low, high])
            output.append(np.clip((array.filled(lo) - lo) / max(hi - lo, 1e-6) * 255, 0, 255).astype("uint8"))
        profile.update(driver="GTiff", dtype="uint8", count=3, nodata=0, compress="deflate")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(destination, "w", **profile) as target:
            target.write(np.stack(output))