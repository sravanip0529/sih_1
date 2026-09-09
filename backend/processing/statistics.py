from pathlib import Path

import numpy as np
import rasterio


def raster_statistics(path: Path, nodata: float | int | None) -> dict[str, float | int | None]:
    with rasterio.open(path) as dataset:
        values = dataset.read(1, masked=True).astype("float64")
        if nodata is not None:
            values = np.ma.masked_equal(values, nodata)
        valid = values.compressed()
    if valid.size == 0:
        return {"minimum": None, "maximum": None, "mean": None, "stddev": None, "valid_pixel_count": 0, "nodata_pixel_count": int(values.size)}
    return {
        "minimum": float(valid.min()), "maximum": float(valid.max()), "mean": float(valid.mean()),
        "stddev": float(valid.std()), "valid_pixel_count": int(valid.size),
        "nodata_pixel_count": int(values.size - valid.size),
    }