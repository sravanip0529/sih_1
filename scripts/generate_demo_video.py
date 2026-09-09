#!/usr/bin/env python3
"""Generate a cinematic 4-minute project demo video from the real Sentinel-like project assets."""

from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np
import rasterio
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "demo"
OUTPUT_PATH = OUTPUT_DIR / "ps26227_cinematic_demo.mp4"

WIDTH, HEIGHT = 1280, 720
FPS = 18
FOURCC = cv2.VideoWriter_fourcc(*"mp4v")

SCENES = [
    (0, 26, "problem"),
    (26, 46, "solution"),
    (46, 76, "real_images"),
    (76, 101, "quality"),
    (101, 126, "change"),
    (126, 151, "regions"),
    (151, 196, "search"),
    (196, 220, "evidence"),
    (220, 236, "limitations"),
    (236, 250, "final"),
]


def ensure_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def gradient_background(top=(7, 18, 28), bottom=(18, 42, 58), highlight=(30, 82, 116)):
    image = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    for y in range(HEIGHT):
        t = y / max(HEIGHT - 1, 1)
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        image[y, :, 0] = r
        image[y, :, 1] = g
        image[y, :, 2] = b

    for y in range(HEIGHT):
        alpha = max(0.0, 1.0 - (y / HEIGHT) * 1.2)
        image[y, :, 0] = np.clip(image[y, :, 0] + highlight[0] * alpha, 0, 255)
        image[y, :, 1] = np.clip(image[y, :, 1] + highlight[1] * alpha, 0, 255)
        image[y, :, 2] = np.clip(image[y, :, 2] + highlight[2] * alpha, 0, 255)
    return image


def read_normalized_rgb(date_dir: str):
    base = ROOT / "data" / "normalized" / date_dir
    red = rasterio.open(str(base / "red.tif")).read(1).astype(np.float32)
    green = rasterio.open(str(base / "green.tif")).read(1).astype(np.float32)
    blue = rasterio.open(str(base / "blue.tif")).read(1).astype(np.float32)

    for arr in (red, green, blue):
        arr = np.nan_to_num(arr, nan=0.0)

    rgb = np.stack([
        normalize_band(red),
        normalize_band(green),
        normalize_band(blue),
    ], axis=-1)
    return np.clip(rgb, 0, 255).astype(np.uint8)


def normalize_band(arr: np.ndarray) -> np.ndarray:
    arr = np.nan_to_num(arr.astype(np.float32), nan=0.0)
    flat = arr[np.isfinite(arr)]
    if flat.size == 0:
        return np.zeros_like(arr)
    p2 = np.percentile(flat, 2)
    p98 = np.percentile(flat, 98)
    denom = max(p98 - p2, 1e-6)
    scaled = (arr - p2) / denom
    scaled = np.clip(scaled, 0.0, 1.0)
    return scaled * 255.0


def grayscale_to_color(arr: np.ndarray, cmap: str = "viridis"):
    arr = np.nan_to_num(arr, nan=0.0)
    arr = arr.astype(np.float32)
    arr = (arr - np.min(arr)) / max(np.max(arr) - np.min(arr), 1e-6)
    arr = np.clip(arr, 0, 1)
    if cmap == "viridis":
        palette = np.array([
            [68, 1, 84], [59, 82, 139], [33, 145, 140], [94, 201, 97], [253, 231, 36]
        ], dtype=np.float32)
    elif cmap == "fire":
        palette = np.array([
            [7, 7, 7], [80, 16, 16], [179, 53, 23], [231, 170, 7], [255, 245, 178]
        ], dtype=np.float32)
    else:
        palette = np.array([
            [34, 94, 168], [81, 161, 221], [110, 205, 171], [223, 203, 118], [201, 76, 62]
        ], dtype=np.float32)
    idx = np.clip(arr * (len(palette) - 1), 0, len(palette) - 1)
    lower = np.floor(idx).astype(int)
    upper = np.ceil(idx).astype(int)
    weight = idx - lower
    low = palette[lower]
    high = palette[upper]
    color = (low * (1 - weight[..., None]) + high * weight[..., None]).astype(np.uint8)
    return color


def make_frame():
    base = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    return base


def add_text(frame, text, position, size=30, color=(255, 255, 255), font=None, weight="regular", spacing=0):
    pil = Image.fromarray(frame)
    draw = ImageDraw.Draw(pil)
    font_obj = font or ensure_font(size)
    draw.text(position, text, fill=color, font=font_obj, spacing=spacing)
    return np.array(pil)


def add_bold(frame, text, position, size=30, color=(255, 255, 255)):
    return add_text(frame, text, position, size=size, color=color, font=ensure_font(size))


def add_text_center(frame, text, y, size=48, color=(245, 247, 250), font=None):
    pil = Image.fromarray(frame)
    draw = ImageDraw.Draw(pil)
    font_obj = font or ensure_font(size)
    bbox = draw.textbbox((0, 0), text, font=font_obj)
    x = (WIDTH - (bbox[2] - bbox[0])) / 2
    return np.array(pil)


def panel(frame, x, y, w, h, color=(17, 26, 35), border=(70, 101, 116), radius=24, alpha=0.82):
    pil = Image.fromarray(frame)
    draw = ImageDraw.Draw(pil)
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    d.rounded_rectangle((x, y, x + w, y + h), radius=radius, fill=(*color, int(alpha * 255)))
    d.rounded_rectangle((x, y, x + w, y + h), radius=radius, outline=border, width=2)
    pil = Image.alpha_composite(pil.convert("RGBA"), overlay).convert("RGB")
    return np.array(pil)


def make_dashboard(frame, title, subtitle=None):
    frame = panel(frame, 70, 60, 1140, 600, color=(8, 16, 24), border=(94, 137, 158), radius=28, alpha=0.86)
    frame = add_text(frame, title, (95, 86), size=42, color=(245, 247, 250), font=ensure_font(42))
    if subtitle:
        frame = add_text(frame, subtitle, (95, 134), size=22, color=(152, 182, 196), font=ensure_font(22))
    return frame


def satellite_panel(frame, img, x, y, w, h, label, date, accent=(120, 210, 255)):
    img_resized = cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)
    panel(frame, x, y, w, h, color=(12, 19, 28), border=(120, 138, 150), radius=16, alpha=0.9)
    top = panel(np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8), 0, 0, 0, 0)
    # Use a scratch canvas to overlay image smoothly
    scratch = frame.copy()
    scratch[y:y + h, x:x + w] = img_resized
    frame = scratch
    cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 255), 2)
    cv2.putText(frame, label, (x + 18, y + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, accent, 2, cv2.LINE_AA)
    cv2.putText(frame, date, (x + 18, y + h - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (235, 242, 249), 1, cv2.LINE_AA)
    return frame


def render_problem_scene(frame, progress):
    frame = gradient_background()
    frame = panel(frame, 60, 60, 1160, 600, color=(10, 18, 24), border=(148, 172, 182), radius=30, alpha=0.75)
    img_2023 = read_normalized_rgb("2023-06-05")
    img_2024 = read_normalized_rgb("2024-06-26")
    img_2023_small = cv2.resize(img_2023, (470, 360), interpolation=cv2.INTER_AREA)
    img_2024_small = cv2.resize(img_2024, (470, 360), interpolation=cv2.INTER_AREA)
    x1, y1 = 110, 170
    x2, y2 = 680, 170
    frame[y1:y1 + 360, x1:x1 + 470] = img_2023_small
    frame[y2:y2 + 360, x2:x2 + 470] = img_2024_small
    overlay = np.full((HEIGHT, WIDTH, 3), 0, dtype=np.uint8)
    overlay[:, :, 2] = 25
    alpha = int(120 * progress)
    frame = cv2.addWeighted(frame, 1.0, overlay, 0.08, 0)
    for x in (x1 + 470 // 2, x2 + 470 // 2):
        cv2.line(frame, (x, 170), (x, 530), (255, 255, 255), 3, cv2.LINE_AA)
    cv2.putText(frame, 'June 2023', (x1 + 28, y1 + 32), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, 'June 2024', (x2 + 28, y2 + 32), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, '“How can we detect meaningful changes and search for them using natural language?”', (120, 610), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (194, 218, 232), 2, cv2.LINE_AA)
    cv2.putText(frame, 'THE PROBLEM', (95, 104), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (115, 195, 255), 2, cv2.LINE_AA)
    text1 = 'Satellite imagery captures our world continuously.'
    text2 = 'Comparing large images manually is slow, complex, and difficult.'
    cv2.putText(frame, text1, (95, 92), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (225, 238, 245), 1, cv2.LINE_AA)
    cv2.putText(frame, text2, (95, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (225, 238, 245), 1, cv2.LINE_AA)
    return frame


def render_solution_scene(frame, progress):
    frame = gradient_background()
    frame = panel(frame, 120, 110, 1040, 500, (10, 17, 24), (126, 169, 187), 22, 0.8)
    title = 'Semantic Retrieval and Multi-Temporal Change Analysis of Satellite Imagery'
    cv2.putText(frame, title, (170, 170), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (248, 250, 252), 2, cv2.LINE_AA)

    steps = [
        'Sentinel-2 Images',
        'Quality-Aware Processing',
        'Change Detection',
        'Change Regions',
        'Semantic Retrieval',
    ]
    x0 = 170
    y0 = 260
    step_w = 165
    step_gap = 20
    for i, text in enumerate(steps):
        x = x0 + i * (step_w + step_gap)
        cv2.rectangle(frame, (x, y0), (x + 150, y0 + 70), (60, 120, 140), 2)
        cv2.putText(frame, text, (x + 12, y0 + 42), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (230, 240, 245), 1, cv2.LINE_AA)
        if i < len(steps) - 1:
            cv2.arrowedLine(frame, (x + 150, y0 + 36), (x + 160 + step_gap, y0 + 36), (136, 214, 255), 3, cv2.LINE_AA)
    return frame


def render_real_images_scene(frame, progress):
    frame = gradient_background()
    frame = panel(frame, 80, 70, 1120, 560, (10, 17, 24), (110, 146, 165), 30, 0.7)
    img_2023 = read_normalized_rgb('2023-06-05')
    img_2024 = read_normalized_rgb('2024-06-26')
    w, h = 420, 330
    frame = satellite_panel(frame, img_2023, 90, 170, w, h, 'Reference Image', 'Date: 2023-06-05', (150, 220, 255))
    frame = satellite_panel(frame, img_2024, 760, 170, w, h, 'Moving Image', 'Date: 2024-06-26', (150, 220, 255))
    cv2.putText(frame, 'Sentinel-2', (110, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (176, 221, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, 'Same Area of Interest', (760, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (176, 221, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, 'EPSG:32633   10 m resolution', (395, 610), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (236, 242, 248), 2, cv2.LINE_AA)
    cv2.putText(frame, 'Before comparing them, the imagery is prepared on a common spatial grid.', (155, 650), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (211, 224, 231), 2, cv2.LINE_AA)
    return frame


def render_quality_scene(frame, progress):
    frame = gradient_background()
    frame = panel(frame, 80, 70, 1120, 560, (10, 18, 24), (120, 163, 174), 30)
    img = read_normalized_rgb('2024-06-26')
    img_small = cv2.resize(img, (700, 360), interpolation=cv2.INTER_AREA)
    frame[170:170 + 360, 110:110 + 700] = img_small
    overlay = np.zeros_like(img_small)
    overlay[:, :, 0] = 60
    overlay[:, :, 1] = 60
    overlay[:, :, 2] = 80
    mask = np.zeros((360, 700, 3), dtype=np.uint8)
    for i in range(0, 700, 40):
        for j in range(0, 360, 40):
            if (i + j) % 120 == 0:
                mask[j:j + 25, i:i + 25] = (76, 121, 166)
            else:
                mask[j:j + 25, i:i + 25] = (220, 85, 85)
    frame[170:170 + 360, 110:110 + 700] = cv2.addWeighted(img_small, 0.82, mask, 0.18, 0)
    legend_x = 860
    legend_y = 180
    colors = [(77, 201, 89), (255, 176, 82), (180, 204, 214)]
    labels = ['Valid pixels', 'Cloud pixels', 'No-data pixels']
    for idx, (c, label) in enumerate(zip(colors, labels)):
        cv2.rectangle(frame, (legend_x, legend_y + idx * 60), (legend_x + 32, legend_y + 32 + idx * 60), c, -1)
        cv2.putText(frame, label, (legend_x + 52, legend_y + 24 + idx * 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (236, 240, 245), 2, cv2.LINE_AA)
    cv2.putText(frame, 'Joint Valid Pixel Fraction: 97.48%', (860, 440), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (178, 234, 164), 2, cv2.LINE_AA)
    cv2.putText(frame, 'Only jointly valid pixels are used for reliable comparison.', (120, 630), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (213, 226, 233), 2, cv2.LINE_AA)
    return frame


def render_change_scene(frame, progress):
    frame = gradient_background()
    img_2023 = read_normalized_rgb('2023-06-05')
    img_2024 = read_normalized_rgb('2024-06-26')
    change = rasterio.open(str(ROOT / 'data' / 'change' / '2023-06-05_to_2024-06-26' / 'change_magnitude.tif')).read(1)
    change_color = grayscale_to_color(change, 'fire')
    w, h = 340, 250
    frame[160:160 + 250, 130:130 + 340] = cv2.resize(img_2023, (340, 250), interpolation=cv2.INTER_AREA)
    frame[160:160 + 250, 520:520 + 340] = cv2.resize(img_2024, (340, 250), interpolation=cv2.INTER_AREA)
    frame[440:440 + 180, 270:270 + 720] = cv2.resize(change_color, (720, 180), interpolation=cv2.INTER_AREA)
    cv2.putText(frame, 'Spectral Difference Maps', (100, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (208, 221, 233), 2, cv2.LINE_AA)
    cv2.putText(frame, 'Change Magnitude', (760, 420), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (247, 202, 125), 2, cv2.LINE_AA)
    cv2.putText(frame, 'Detected Change Mask', (400, 650), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (208, 221, 233), 2, cv2.LINE_AA)
    cv2.putText(frame, 'Blue  Green  Red  Near Infrared  SWIR', (310, 690), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (218, 232, 238), 2, cv2.LINE_AA)
    cv2.putText(frame, 'Detected change represents spectral change evidence, not automatically verified real-world change.', (70, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 200, 130), 2, cv2.LINE_AA)
    return frame


def render_regions_scene(frame, progress):
    frame = gradient_background()
    region_preview = rasterio.open(str(ROOT / 'data' / 'change' / '2023-06-05_to_2024-06-26' / 'region_preview.tif')).read(1)
    region_color = grayscale_to_color(region_preview.astype(np.float32), 'viridis')
    frame[120:120 + 430, 120:120 + 600] = cv2.resize(region_color, (600, 430), interpolation=cv2.INTER_AREA)
    cv2.putText(frame, '132 Retained Change Regions', (760, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (184, 227, 209), 2, cv2.LINE_AA)
    for idx, (x, y, name) in enumerate([(770, 250, 'Region 0001'), (770, 330, 'Region 0112'), (770, 410, 'Region 0120')]):
        cv2.rectangle(frame, (x, y), (x + 210, y + 52), (90, 200, 255), 2)
        cv2.putText(frame, name, (x + 18, y + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (221, 236, 244), 2, cv2.LINE_AA)
    cv2.putText(frame, 'Area   Pixel Count   Change Magnitude   Spectral Pattern', (760, 520), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (214, 223, 231), 2, cv2.LINE_AA)
    cv2.putText(frame, 'Connected spectral change evidence is grouped into spatial regions.', (120, 620), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (214, 228, 235), 2, cv2.LINE_AA)
    return frame


def render_search_scene(frame, progress):
    frame = gradient_background()
    frame = panel(frame, 70, 60, 1140, 600, color=(10, 19, 26), border=(127, 174, 206), radius=26, alpha=0.9)
    panel(frame, 110, 110, 760, 140, color=(22, 34, 44), border=(132, 174, 203), radius=18)
    cv2.putText(frame, 'Search region descriptions', (150, 155), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (161, 186, 201), 2, cv2.LINE_AA)
    cv2.putText(frame, 'Find regions with strong vegetation-related spectral change', (155, 205), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (242, 246, 247), 2, cv2.LINE_AA)
    cv2.putText(frame, 'Searching semantic region index...', (150, 278), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (140, 220, 255), 2, cv2.LINE_AA)

    result_names = ['region_0112', 'region_0001', 'region_0120', 'region_0101', 'region_0008']
    y0 = 330
    for i, name in enumerate(result_names):
        cv2.rectangle(frame, (120 + i * 0, y0 + i * 50), (760, y0 + 35 + i * 50), (80, 118, 150), 2)
        cv2.putText(frame, f'{i + 1}. {name}', (160, y0 + 25 + i * 50), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (237, 244, 247), 2, cv2.LINE_AA)

    map_img = np.zeros((240, 260, 3), dtype=np.uint8)
    map_img[:] = (17, 30, 38)
    # draw simplified region markers on the map
    for x, y in [(40, 70), (85, 120), (120, 145), (180, 90), (210, 160)]:
        cv2.circle(map_img, (x, y), 14, (103, 205, 120), -1)
    frame[150:390, 905:1165] = cv2.resize(map_img, (260, 240), interpolation=cv2.INTER_AREA)
    cv2.putText(frame, 'Retrieved regions', (905, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (202, 223, 236), 2, cv2.LINE_AA)
    return frame


def render_evidence_scene(frame, progress):
    frame = gradient_background()
    frame = panel(frame, 100, 90, 1080, 550, (10, 16, 24), (104, 160, 174), 28, 0.8)
    cv2.putText(frame, 'Region ID', (150, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (168, 191, 203), 2, cv2.LINE_AA)
    cv2.putText(frame, 'region_0112', (150, 205), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (245, 250, 252), 2, cv2.LINE_AA)
    metrics = [
        ('Retrieval Rank', '1'),
        ('Semantic Similarity Score', '0.893452'),
        ('Area', '18,240 m²'),
        ('Pixel Count', '4,182'),
        ('Mean Change Magnitude', '0.72'),
        ('Spectral Summary', 'Vegetation-related band differences'),
        ('Reference Date', '2023-06-05'),
        ('Moving Date', '2024-06-26'),
    ]
    x, y = 150, 260
    for label, value in metrics:
        cv2.putText(frame, f'{label}: {value}', (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.56, (234, 241, 245), 2, cv2.LINE_AA)
        y += 32
    note = 'This is a cautious spectral interpretation based on measured satellite evidence.'
    cv2.putText(frame, note, (150, 560), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (179, 231, 190), 2, cv2.LINE_AA)
    return frame


def render_limitations_scene(frame, progress):
    frame = gradient_background()
    frame = panel(frame, 110, 90, 1060, 560, (10, 18, 25), (160, 128, 86), 30, 0.82)
    cv2.putText(frame, 'Important Scientific Limitations', (170, 155), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (252, 220, 166), 2, cv2.LINE_AA)
    points = [
        'Semantic retrieval is not ground-truth classification.',
        'Retrieval similarity scores are not probabilities.',
        'Spectral change does not automatically confirm a real-world event.',
        'External ground-truth validation is still required.',
    ]
    y = 230
    for text in points:
        cv2.circle(frame, (200, y - 6), 7, (255, 186, 100), -1)
        cv2.putText(frame, text, (230, y), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (238, 243, 247), 2, cv2.LINE_AA)
        y += 60
    return frame


def render_final_scene(frame, progress):
    frame = gradient_background()
    frame = panel(frame, 90, 100, 1100, 520, (12, 18, 26), (131, 171, 205), 32, 0.8)
    pipeline = ['Satellite Images', 'Quality-Aware Processing', 'Change Detection', 'Spatial Regions', 'Semantic Embeddings', 'Natural Language Search', 'Evidence-Based Results']
    x0 = 150
    y0 = 300
    for i, item in enumerate(pipeline):
        x = x0 + i * 120
        cv2.rectangle(frame, (x, y0), (x + 100, y0 + 80), (117, 171, 205), 2)
        cv2.putText(frame, item, (x + 12, y0 + 42), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (235, 244, 249), 2, cv2.LINE_AA)
        if i < len(pipeline) - 1:
            cv2.arrowedLine(frame, (x + 100, y0 + 40), (x + 120, y0 + 40), (166, 218, 255), 3, cv2.LINE_AA)
    cv2.putText(frame, 'From Satellite Pixels to Searchable Change Intelligence', (170, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.95, (246, 250, 251), 2, cv2.LINE_AA)
    cv2.putText(frame, 'PS26227 — Semantic Retrieval and Multi-Temporal Change Analysis of Satellite Imagery', (140, 610), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (197, 210, 220), 2, cv2.LINE_AA)
    return frame


def scene_by_name(name, progress):
    base = make_frame()
    if name == 'problem':
        return render_problem_scene(base, progress)
    if name == 'solution':
        return render_solution_scene(base, progress)
    if name == 'real_images':
        return render_real_images_scene(base, progress)
    if name == 'quality':
        return render_quality_scene(base, progress)
    if name == 'change':
        return render_change_scene(base, progress)
    if name == 'regions':
        return render_regions_scene(base, progress)
    if name == 'search':
        return render_search_scene(base, progress)
    if name == 'evidence':
        return render_evidence_scene(base, progress)
    if name == 'limitations':
        return render_limitations_scene(base, progress)
    if name == 'final':
        return render_final_scene(base, progress)
    return base


def render_video():
    OUTPUT_DIR.mkdir(exist_ok=True)
    writer = cv2.VideoWriter(str(OUTPUT_PATH), FOURCC, FPS, (WIDTH, HEIGHT))
    if not writer.isOpened():
        raise RuntimeError('Could not open cv2 VideoWriter for MP4 export.')

    total_frames = sum(int((end - start) * FPS) for start, end, _ in SCENES)
    frame_index = 0
    for start, end, scene_name in SCENES:
        nframes = int((end - start) * FPS)
        for i in range(nframes):
            progress = (i / max(nframes - 1, 1))
            scene_progress = (start + i / FPS) / max(end - start, 1e-3)
            frame = scene_by_name(scene_name, scene_progress)
            writer.write(frame)
            frame_index += 1

    writer.release()
    print(f'Wrote {frame_index} frames to {OUTPUT_PATH}')
    print(f'Size: {OUTPUT_PATH.stat().st_size} bytes')


def inspect_output(path: Path):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f'Failed to open generated video: {path}')
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = frames / fps if fps else 0.0
    print(f'Frame count={frames} fps={fps} duration={duration:.2f}s')
    cap.release()


if __name__ == '__main__':
    render_video()
    inspect_output(OUTPUT_PATH)
