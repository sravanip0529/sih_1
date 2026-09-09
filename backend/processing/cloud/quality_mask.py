import numpy as np


def create_masks(probability: np.ndarray, nodata: np.ndarray, threshold: float, valid_value: int = 0, cloud_value: int = 1, nodata_value: int = 2) -> tuple[np.ndarray, np.ndarray]:
    cloud = probability >= threshold
    cloud_mask = np.where(nodata, nodata_value, cloud.astype("uint8"))
    quality = np.where(nodata, nodata_value, np.where(cloud, cloud_value, valid_value)).astype("uint8")
    return cloud_mask, quality


def statistics(quality: np.ndarray, probability: np.ndarray, nodata_value: int = 2) -> dict[str, object]:
    total = int(quality.size)
    nodata = int(np.count_nonzero(quality == nodata_value))
    cloud = int(np.count_nonzero(quality == 1))
    valid = int(np.count_nonzero(quality == 0))
    if valid + cloud + nodata != total:
        raise ValueError("Quality mask classes do not account for every pixel")
    valid_probability = probability[quality != nodata_value]
    return {
        "total_pixels": total,
        "valid_pixels": valid,
        "valid_percentage": valid / total * 100,
        "cloud_pixels": cloud,
        "cloud_percentage": cloud / total * 100,
        "nodata_pixels": nodata,
        "nodata_percentage": nodata / total * 100,
        "probability_minimum": float(valid_probability.min()) if valid_probability.size else None,
        "probability_maximum": float(valid_probability.max()) if valid_probability.size else None,
        "probability_mean": float(valid_probability.mean()) if valid_probability.size else None,
    }