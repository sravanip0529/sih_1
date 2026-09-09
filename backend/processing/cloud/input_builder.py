from pathlib import Path

import numpy as np
import rasterio


S2CLOUDLESS_BANDS = ("B01", "B02", "B04", "B05", "B08", "B8A", "B09", "B10", "B11", "B12")
LOGICAL_BANDS = {"B01": "b01", "B02": "blue", "B04": "red", "B05": "b05", "B08": "nir", "B8A": "b8a", "B09": "b09", "B10": "b10", "B11": "swir16", "B12": "b12"}


def build_model_input(paths: dict[str, Path], scale_factor: float = 10000.0) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    missing = [band for band in S2CLOUDLESS_BANDS if band not in paths]
    if missing:
        raise ValueError(f"Missing s2cloudless input bands: {missing}")
    arrays: list[np.ndarray] = []
    nodata_mask = None
    signature = None
    for band in S2CLOUDLESS_BANDS:
        with rasterio.open(paths[band]) as dataset:
            current = dataset.read(1).astype("float32")
            current_nodata = current == (dataset.nodata if dataset.nodata is not None else 0)
            nodata_mask = current_nodata if nodata_mask is None else nodata_mask | current_nodata
            current_signature = (dataset.crs.to_string(), tuple(dataset.transform), dataset.width, dataset.height, tuple(dataset.res), tuple(dataset.bounds))
            if signature is None:
                signature = current_signature
            elif current_signature != signature:
                raise ValueError(f"Cloud input grid mismatch for {band}")
            arrays.append(current / scale_factor)
    stack = np.stack(arrays, axis=-1)
    stack[nodata_mask] = 0.0
    return stack[np.newaxis, ...], nodata_mask, {"bands": list(S2CLOUDLESS_BANDS), "scale_factor": scale_factor, "shape": list(stack.shape), "grid": signature}