import importlib.metadata

import numpy as np


def generate_probability(model_input: np.ndarray, threshold: float) -> tuple[np.ndarray, dict[str, object]]:
    if model_input.ndim != 4 or model_input.shape[-1] != 10:
        raise ValueError("s2cloudless input must have shape (1, height, width, 10)")
    from s2cloudless import S2PixelCloudDetector

    version = importlib.metadata.version("s2cloudless")
    detector = S2PixelCloudDetector(threshold=threshold, all_bands=False, average_over=1, dilation_size=0)
    probability = detector.get_cloud_probability_maps(model_input)[0].astype("float32")
    if np.nanmin(probability) < 0 or np.nanmax(probability) > 1:
        raise ValueError("s2cloudless produced probability values outside [0, 1]")
    return probability, {"model": "s2cloudless", "version": version, "threshold": threshold, "dilation_size": 0}