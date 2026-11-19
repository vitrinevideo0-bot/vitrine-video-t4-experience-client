#!/usr/bin/env python3
"""T4 silent renderer — 30 s, 720×1280, 30 fps, 900 frames.

The renderer adapts the owner-approved A+B+C+D transition grammar:
A structures tile reveals, B reconfigures multi-plan grids, C supplies short
impact shakes and media blocks, and D supplies one-to-three-frame glitches.
It never uses CapCut media, text, palettes, watermarks or audio.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, TOTAL = 720, 1280, 30, 900
# Compact temporal proxies keep peak memory below GitHub/sandbox limits. They are
# used only inside tiles and panels; full-screen stable frames stay 720×1280.
PREVIEW_W, PREVIEW_H = 180, 320
ENGINE_VERSION = "1.0.0-a-b-c-d-borderless"
SCENE_RANGES = {
    "S1": (0, 179),
    "S2": (180, 419),
    "S3": (420, 629),
    "S4": (630, 899),
}
SCENE_ORDER = ["S1", "S2", "S3", "S4"]
SCENE_LENGTHS = {scene_id: end - start + 1 for scene_id, (start, end) in SCENE_RANGES.items()}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ffmpeg_binary() -> str:
    found = os.environ.get("FFMPEG_BIN") or shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg  # type: ignore
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # pragma: no cover
        raise SystemExit("FFmpeg is required") from exc


def run(command: list[str]) -> None:
    print("RUN", " ".join(command), flush=True)
    subprocess.run(command, check=True)


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def smooth(value: float) -> float:
    value = clamp01(value)
    return value * value * (3.0 - 2.0 * value)


def ease_out(value: float) -> float:
    value = clamp01(value)
    return 1.0 - (1.0 - value) ** 3


def mix(first: np.ndarray, second: np.ndarray, alpha: float) -> np.ndarray:
    return cv2.addWeighted(first, 1.0 - clamp01(alpha), second, clamp01(alpha), 0.0)


def transform(frame: np.ndarray, scale: float = 1.0, angle: float = 0.0, dx: float = 0.0, dy: float = 0.0) -> np.ndarray:
    matrix = cv2.getRotationMatrix2D((W / 2, H / 2), angle, scale)
    matrix[0, 2] += dx
    matrix[1, 2] += dy
    return cv2.warpAffine(frame, matrix, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT_101)


def preprocess_scene(ffmpeg: str, source: Path, destination: Path, scene: dict[str, Any]) -> None:
    frames = int(scene["duration_seconds"] * FPS)
    bias = float(scene.get("crop_x_bias", 0.0))
    x_expr = f"(iw-ow)/2+({bias:.6f})*(iw-ow)/2"
    vf = (
        "scale=720:1280:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop=720:1280:{x_expr}:(ih-oh)/2,"
        "fps=30,"
        "eq=contrast=1.035:saturation=1.06:brightness=0.006,"
        "unsharp=5:5:0.28:5:5:0.0,"
        "setpts=PTS-STARTPTS"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    run([
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{float(scene['trim_start_seconds']):.6f}",
        "-i",
        str(source),
        "-vf",
        vf,
        "-frames:v",
        str(frames),
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "15",
        "-pix_fmt",
        "yuv420p",
        str(destination),
    ])
    capture = cv2.VideoCapture(str(destination))
    actual = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    capture.release()
    if (actual, width, height) != (frames, W, H):
        raise RuntimeError(f"Invalid intermediate {destination}: {(actual, width, height)}")


def load_preview_frames(path: Path, expected: int) -> list[np.ndarray]:
    capture = cv2.VideoCapture(str(path))
    frames: list[np.ndarray] = []
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        frames.append(cv2.resize(frame, (PREVIEW_W, PREVIEW_H), interpolation=cv2.INTER_AREA))
    capture.release()
    if len(frames) != expected:
        raise RuntimeError(f"Preview frame count mismatch for {path}: {len(frames)} != {expected}")
    return frames


def scene_for_frame(frame_number: int) -> str:
    for scene_id, (start, end) in SCENE_RANGES.items():
        if start <= frame_number <= end:
            return scene_id
    raise ValueError(frame_number)


def scene_local_frame(scene_id: str, frame_number: int) -> int:
    return frame_number - SCENE_RANGES[scene_id][0]


def previous_scene(scene_id: str) -> str | None:
    index = SCENE_ORDER.index(scene_id)
    return SCENE_ORDER[index - 1] if index > 0 else None


def temporal_preview(previews: dict[str, list[np.ndarray]], scene_id: str, local_frame: int, offset: int = 0) -> np.ndarray:
    sequence = previews[scene_id]
    index = max(0, min(len(sequence) - 1, local_frame + offset))
    return sequence[index]


def temporal_full(previews: dict[str, list[np.ndarray]], scene_id: str, local_frame: int, offset: int = 0) -> np.ndarray:
    return cv2.resize(temporal_preview(previews, scene_id, local_frame, offset), (W, H), interpolation=cv2.INTER_CUBIC)


def cover_panel(frame: np.ndarray, width: int, height: int) -> np.ndarray:
    source_h, source_w = frame.shape[:2]
    scale = max(width / source_w, height / source_h)
    resized_w = max(width, int(round(source_w * scale)))
    resized_h = max(height, int(round(source_h * scale)))
    resized = cv2.resize(frame, (resized_w, resized_h), interpolation=cv2.INTER_CUBIC)
    x = (resized_w - width) // 2
    y = (resized_h - height) // 2
    return resized[y:y + height, x:x + width]


def tile_reveal(
    base: np.ndarray,
    scene_id: str,
    local_frame: int,
    progress: float,
    event: dict[str, Any],
    previews: dict[str, list[np.ndarray]],
) -> np.ndarray:
    variant = event["variant"]
    rows, columns = (8, 5) if variant == "checker_reveal" else (6, 4)
    rng = np.random.default_rng(int(event["seed"]))
    order = list(rng.permutation(rows * columns))
    offsets = [12, 24, 39, 57]
    alternate = [temporal_full(previews, scene_id, local_frame, offset) for offset in offsets]
    previous = previous_scene(scene_id)

    if variant == "previous_scene_to_current" and previous is not None:
        previous_index = SCENE_LENGTHS[previous] - 1 - min(20, int((1.0 - progress) * 20))
        canvas = temporal_full(previews, previous, previous_index, 0)
        count = int(round(smooth(progress) * rows * columns))
        selected = set(order[:count])
        settle_alpha = smooth((progress - 0.78) / 0.22) if progress > 0.78 else 0.0
    else:
        if variant in {"future_windows_open", "settle_to_stable_tail"}:
            intensity = 1.0 - smooth(progress)
        else:
            intensity = math.sin(math.pi * progress)
        count = int(round((5 + 11 * intensity)))
        selected = set(order[:max(0, min(rows * columns, count))])
        canvas = base.copy()
        settle_alpha = 0.0

    face_safe = "face_safe" in variant
    x_edges = np.linspace(0, W, columns + 1, dtype=int)
    y_edges = np.linspace(0, H, rows + 1, dtype=int)
    for cell in range(rows * columns):
        if cell not in selected:
            continue
        row, column = divmod(cell, columns)
        x0, x1 = x_edges[column], x_edges[column + 1]
        y0, y1 = y_edges[row], y_edges[row + 1]
        center_x = (x0 + x1) / (2 * W)
        center_y = (y0 + y1) / (2 * H)
        if face_safe and 0.18 <= center_x <= 0.84 and 0.08 <= center_y <= 0.72:
            continue
        source = alternate[(cell + int(event["seed"])) % len(alternate)]
        # Use distinct temporal content; no colored borders or synthetic separators.
        canvas[y0:y1, x0:x1] = source[y0:y1, x0:x1]
    if settle_alpha:
        canvas = mix(canvas, base, settle_alpha)
    return canvas


def grid_boxes(layout: str, progress: float) -> list[tuple[int, int, int, int]]:
    wave = math.sin(progress * math.pi * 2.0)
    if layout == "three_columns":
        split1 = int(W * 0.33 + wave * 26)
        split2 = int(W * 0.67 - wave * 22)
        gap = 3
        return [
            (0, 0, max(1, split1 - gap), H),
            (split1 + gap, 0, max(1, split2 - split1 - 2 * gap), H),
            (split2 + gap, 0, max(1, W - split2 - gap), H),
        ]
    if layout == "offset_2x2":
        split_x = int(W * 0.5 + wave * 32)
        split_y = int(H * 0.5 + math.cos(progress * math.pi * 2.0) * 54)
        gap = 3
        return [
            (0, 0, split_x - gap, split_y - gap),
            (split_x + gap, 0, W - split_x - gap, split_y - gap),
            (0, split_y + gap, split_x - gap, H - split_y - gap),
            (split_x + gap, split_y + gap, W - split_x - gap, H - split_y - gap),
        ]
    if layout == "face_safe_satellites":
        return [
            (0, 0, 122, 455),
            (12, 936, 220, 325),
            (250, 972, 220, 289),
            (488, 922, 220, 339),
        ]
    # central_dominant
    shift = int(wave * 24)
    return [
        (92 + shift, 116, 536, 720),
        (14, 28, 212, 260),
        (494, 30, 212, 260),
        (16, 948, 226, 300),
        (478, 920, 226, 328),
    ]


def dynamic_grid(
    base: np.ndarray,
    scene_id: str,
    local_frame: int,
    progress: float,
    event: dict[str, Any],
    previews: dict[str, list[np.ndarray]],
) -> np.ndarray:
    layout = event["variant"]
    if layout == "face_safe_satellites":
        canvas = np.clip(base.astype(np.float32) * 0.74, 0, 255).astype(np.uint8)
    else:
        blurred = cv2.GaussianBlur(base, (0, 0), 18)
        canvas = np.clip(blurred.astype(np.float32) * 0.28, 0, 255).astype(np.uint8)
    boxes = grid_boxes(layout, progress)
    offsets = [12, 24, 39, 57, -18, 72, -33]
    for index, (x, y, width, height) in enumerate(boxes):
        if width <= 1 or height <= 1:
            continue
        source = temporal_preview(previews, scene_id, local_frame, offsets[index % len(offsets)])
        panel = cover_panel(source, width, height)
        canvas[y:y + height, x:x + width] = panel
    edge = min(smooth(progress / 0.24), smooth((1.0 - progress) / 0.24))
    return mix(base, canvas, edge)


def shake_impact(base: np.ndarray, progress: float, event: dict[str, Any]) -> np.ndarray:
    face_safe = "face_safe" in event["variant"]
    multiplier = 0.62 if face_safe else 1.0
    # Damped alternating impulse with overscan; it always returns toward center.
    envelope = (1.0 - progress) ** 1.35
    sign = -1.0 if int(progress * 6.0) % 2 else 1.0
    dx = sign * 13.0 * envelope * multiplier
    dy = -sign * 7.0 * envelope * multiplier
    angle = sign * 0.58 * envelope * multiplier
    scale = 1.05 - 0.018 * progress
    return transform(base, scale=scale, angle=angle, dx=dx, dy=dy)


def rectangular_stutter(
    base: np.ndarray,
    scene_id: str,
    local_frame: int,
    progress: float,
    event: dict[str, Any],
    previews: dict[str, list[np.ndarray]],
) -> np.ndarray:
    rng = np.random.default_rng(int(event["seed"]))
    alternate = temporal_full(previews, scene_id, local_frame, 27)
    canvas = base.copy()
    intensity = math.sin(math.pi * progress)
    block_count = 5
    heights = rng.integers(28, 92, size=block_count)
    positions = rng.integers(35, H - 120, size=block_count)
    for index, (y, height) in enumerate(zip(positions, heights)):
        y0 = int(max(0, min(H - 1, y)))
        y1 = int(max(y0 + 1, min(H, y0 + int(height))))
        shift = int(((-1) ** index) * (12 + 24 * intensity))
        segment = np.roll(alternate[y0:y1], shift, axis=1)
        alpha = 0.48 + 0.38 * intensity
        canvas[y0:y1] = cv2.addWeighted(canvas[y0:y1], 1.0 - alpha, segment, alpha, 0.0)
    return canvas


def micro_glitch(
    base: np.ndarray,
    scene_id: str,
    local_frame: int,
    local_event_frame: int,
    event: dict[str, Any],
    previews: dict[str, list[np.ndarray]],
) -> np.ndarray:
    rng = np.random.default_rng(int(event["seed"]) * 97 + local_event_frame)
    alternate = temporal_full(previews, scene_id, local_frame, 19 + local_event_frame * 7)
    canvas = base.copy()
    face_safe = "face_safe" in event["variant"]
    slices = 5 if not face_safe else 4
    for index in range(slices):
        height = int(rng.integers(12, 36))
        if face_safe:
            if index % 2:
                y0 = int(rng.integers(0, max(1, int(H * 0.10) - height)))
            else:
                y0 = int(rng.integers(int(H * 0.76), H - height))
        else:
            y0 = int(rng.integers(0, H - height))
        y1 = y0 + height
        dx = int(rng.integers(-18, 19))
        source = alternate[y0:y1].copy()
        source = np.roll(source, dx, axis=1)
        rgb_shift = int(rng.integers(2, 8))
        source[:, :, 2] = np.roll(source[:, :, 2], rgb_shift, axis=1)
        source[:, :, 0] = np.roll(source[:, :, 0], -rgb_shift, axis=1)
        alpha = 0.62 if index % 2 else 0.78
        canvas[y0:y1] = cv2.addWeighted(canvas[y0:y1], 1.0 - alpha, source, alpha, 0.0)
    return canvas


def vignette_mask() -> np.ndarray:
    yy, xx = np.mgrid[0:H, 0:W]
    nx = (xx - W / 2) / (W / 2)
    ny = (yy - H / 2) / (H / 2)
    radius = np.sqrt(nx * nx + ny * ny)
    return np.clip(1.02 - 0.15 * np.maximum(0, radius - 0.36), 0.80, 1.0).astype(np.float32)[..., None]


def apply_vignette(frame: np.ndarray, mask: np.ndarray) -> np.ndarray:
    return np.clip(frame.astype(np.float32) * mask, 0, 255).astype(np.uint8)


def event_progress(event: dict[str, Any], frame_number: int) -> tuple[int, float]:
    start, end = event["frames"]
    local = frame_number - start
    length = end - start + 1
    return local, 0.0 if length <= 1 else local / (length - 1)


def font_path() -> str:
    candidates = [
        Path("assets/fonts/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    raise RuntimeError("DejaVu Sans Bold not found")


def make_contact_sheet(video: Path, destination: Path, samples: list[int]) -> None:
    capture = cv2.VideoCapture(str(video))
    thumbs: list[Image.Image] = []
    label_font = ImageFont.truetype(font_path(), 18)
    for frame_number in samples:
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ok, frame = capture.read()
        if not ok:
            raise RuntimeError(f"Cannot read frame {frame_number}")
        thumb = cv2.resize(frame, (180, 320), interpolation=cv2.INTER_AREA)
        image = Image.fromarray(cv2.cvtColor(thumb, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 179, 29), fill=(0, 0, 0))
        draw.text((6, 4), f"f{frame_number} · {frame_number / FPS:.2f}s", font=label_font, fill="white")
        thumbs.append(image)
    columns = 5
    rows = math.ceil(len(thumbs) / columns)
    board = Image.new("RGB", (columns * 180, rows * 320), (18, 14, 12))
    for index, image in enumerate(thumbs):
        board.paste(image, ((index % columns) * 180, (index // columns) * 320))
    destination.parent.mkdir(parents=True, exist_ok=True)
    board.save(destination, quality=92)
    capture.release()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("rushes/manifest.json"))
    parser.add_argument("--contract", type=Path, default=Path("reverse-engineering/T4_TRANSITIONS_30S.json"))
    parser.add_argument("--render-job", type=Path, default=Path("demo/render_job_silent_demo.json"))
    parser.add_argument("--cache", type=Path, default=Path("rushes/cache"))
    parser.add_argument("--work", type=Path, default=Path(".tmp/t4-silent"))
    parser.add_argument("--output-dir", type=Path, default=Path("output/t4-silent-v1.0.0"))
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    render_job = json.loads(args.render_job.read_text(encoding="utf-8"))
    if render_job["template_id"] != "RESTAURATION-T4":
        raise SystemExit("Wrong template_id in RenderJob")
    scenes = manifest["scenes"]
    if [int(scene["duration_seconds"]) for scene in scenes] != [6, 8, 7, 9]:
        raise SystemExit("Scene durations must be 6/8/7/9")
    events = contract["timeline_events"]
    if len(events) != 48:
        raise SystemExit("T4 transition contract must contain exactly 48 events")
    if contract["owner_constraints"]["silent_render_text_forbidden"] is not True:
        raise SystemExit("Silent render must forbid text")
    if contract["owner_constraints"]["silent_render_audio_forbidden"] is not True:
        raise SystemExit("Silent render must forbid audio")

    event_for_frame: list[dict[str, Any] | None] = [None] * TOTAL
    for event in events:
        start, end = event["frames"]
        for frame_number in range(start, end + 1):
            if event_for_frame[frame_number] is not None:
                raise RuntimeError(f"Event overlap at frame {frame_number}")
            event_for_frame[frame_number] = event
    if any(event_for_frame[frame] is not None for frame in range(810, 900)):
        raise RuntimeError("S4 final 90 frames must be effect-free")

    args.work.mkdir(parents=True, exist_ok=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = ffmpeg_binary()
    intermediates: dict[str, Path] = {}
    for scene in scenes:
        source = args.cache / scene["cache_filename"]
        if not source.exists():
            raise SystemExit(f"Missing rush: {source}; run tools/fetch_rushes.py")
        if source.stat().st_size != int(scene["expected_bytes"]) or sha256(source) != scene["sha256"]:
            raise SystemExit(f"Invalid cached rush: {source}")
        destination = args.work / f"{scene['scene']}_base.mp4"
        preprocess_scene(ffmpeg, source, destination, scene)
        intermediates[scene["scene"]] = destination

    print("PRELOAD temporal previews", flush=True)
    previews = {
        scene_id: load_preview_frames(intermediates[scene_id], SCENE_LENGTHS[scene_id])
        for scene_id in SCENE_ORDER
    }
    output = args.output_dir / "VIDEO_T4_EXPERIENCE_CLIENT_SILENCIEUSE_V1_A_VALIDER.mp4"
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "bgr24",
        "-s:v",
        f"{W}x{H}",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-an",
        "-frames:v",
        str(TOTAL),
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output),
    ]
    encoder = subprocess.Popen(command, stdin=subprocess.PIPE)
    if encoder.stdin is None:
        raise RuntimeError("FFmpeg stdin unavailable")

    captures = {scene_id: cv2.VideoCapture(str(path)) for scene_id, path in intermediates.items()}
    vignette = vignette_mask()
    expected_event_counts = {event["event_id"]: event["duration_frames"] for event in events}
    applied_counts = {event["event_id"]: 0 for event in events}
    event_max_delta = {event["event_id"]: 0.0 for event in events}
    sample_hashes: dict[str, dict[str, str]] = {event["event_id"]: {} for event in events}
    family_frame_counts: dict[str, int] = {}

    try:
        for frame_number in range(TOTAL):
            scene_id = scene_for_frame(frame_number)
            local_scene = scene_local_frame(scene_id, frame_number)
            ok, base = captures[scene_id].read()
            if not ok:
                raise RuntimeError(f"Cannot read {scene_id} frame {local_scene}")
            if base.shape[:2] != (H, W):
                base = cv2.resize(base, (W, H), interpolation=cv2.INTER_CUBIC)
            event = event_for_frame[frame_number]
            frame = base
            if event is not None:
                local_event, progress = event_progress(event, frame_number)
                family = event["family"]
                if family == "T4_TILE_REVEAL":
                    frame = tile_reveal(base, scene_id, local_scene, progress, event, previews)
                elif family == "T4_DYNAMIC_GRID_RECONFIG":
                    frame = dynamic_grid(base, scene_id, local_scene, progress, event, previews)
                elif family == "T4_SHAKE_IMPACT":
                    frame = shake_impact(base, progress, event)
                elif family == "T4_RECTANGULAR_BLOCK_STUTTER":
                    frame = rectangular_stutter(base, scene_id, local_scene, progress, event, previews)
                elif family == "T4_MICRO_GLITCH":
                    frame = micro_glitch(base, scene_id, local_scene, local_event, event, previews)
                else:
                    raise RuntimeError(f"Unsupported family {family}")
                delta = float(cv2.absdiff(frame, base).mean())
                event_max_delta[event["event_id"]] = max(event_max_delta[event["event_id"]], delta)
                applied_counts[event["event_id"]] += 1
                family_frame_counts[family] = family_frame_counts.get(family, 0) + 1
            frame = apply_vignette(frame, vignette)
            if event is not None:
                start, end = event["frames"]
                markers = {start: "start", (start + end) // 2: "middle", end: "end"}
                if frame_number in markers:
                    sample_hashes[event["event_id"]][markers[frame_number]] = hashlib.sha256(frame.tobytes()).hexdigest()
            encoder.stdin.write(np.ascontiguousarray(frame).tobytes())
            if frame_number % 90 == 0:
                print(f"RENDER {frame_number}/{TOTAL}", flush=True)
    finally:
        encoder.stdin.close()
        return_code = encoder.wait()
        for capture in captures.values():
            capture.release()
    if return_code != 0:
        raise RuntimeError(f"FFmpeg failed with code {return_code}")
    if applied_counts != expected_event_counts:
        raise RuntimeError("Event coverage mismatch")

    contact = args.output_dir / "T4_TRANSITION_PROOF_V1.jpg"
    samples = [
        0, 7, 18, 38, 60, 81, 105, 140, 179,
        180, 187, 210, 244, 272, 320, 363, 415, 419,
        420, 436, 466, 515, 549, 580, 611, 629,
        630, 660, 704, 736, 783, 809, 810, 840, 899,
    ]
    make_contact_sheet(output, contact, samples)
    output_hash = sha256(output)
    report = {
        "schema_version": "1.0.0",
        "template_id": "RESTAURATION-T4",
        "engine_version": ENGINE_VERSION,
        "status": "silent_candidate_v1_pending_owner_review",
        "rendered_on": "github_actions" if os.environ.get("GITHUB_ACTIONS") == "true" else "local_preflight",
        "output": {
            "file": output.name,
            "bytes": output.stat().st_size,
            "sha256": output_hash,
            "width": W,
            "height": H,
            "fps": FPS,
            "total_frames": TOTAL,
            "duration_seconds": 30,
            "audio_streams_expected": 0,
            "burned_text_expected": False,
        },
        "source_manifest_sha256": sha256(args.manifest),
        "transition_contract_sha256": sha256(args.contract),
        "render_job_sha256": sha256(args.render_job),
        "contact_sheet_file": contact.name,
        "creative_fusion": {
            "A": "tile_reveal_structural_core",
            "B": "multi_plan_grid_reconfiguration",
            "C": "impact_shake_and_rectangular_media_blocks",
            "D": "one_to_three_frame_micro_glitch"
        },
        "events": [
            {
                "event_id": event["event_id"],
                "scene_id": event["scene_id"],
                "family": event["family"],
                "variant": event["variant"],
                "frames": event["frames"],
                "expected_frame_count": expected_event_counts[event["event_id"]],
                "applied_frame_count": applied_counts[event["event_id"]],
                "max_mean_absolute_delta_from_base": round(event_max_delta[event["event_id"]], 6),
                "sample_frame_sha256": sample_hashes[event["event_id"]],
            }
            for event in events
        ],
        "family_frame_counts": dict(sorted(family_frame_counts.items())),
        "all_48_events_applied": applied_counts == expected_event_counts,
        "all_events_visibly_nonzero": all(value > 0.15 for value in event_max_delta.values()),
        "s4_final_stable_tail": {
            "frames": [810, 899],
            "effect_event_count": 0,
            "duration_frames": 90,
            "duration_seconds": 3.0,
        },
        "visual_policy": {
            "text_rendered": False,
            "watermark_rendered": False,
            "solid_color_transition_bars_rendered": False,
            "blue_cyan_separator_lines_rendered": False,
            "persistent_vhs_noise_rendered": False,
        },
        "audio_policy": {
            "voice_over": False,
            "music": False,
            "capture_audio": False,
            "output_audio_streams_expected": 0,
        },
        "sources": [
            {
                "scene": scene["scene"],
                "pexels_id": scene["pexels_id"],
                "page_url": scene["page_url"],
                "sha256": scene["sha256"],
                "raw_published": False,
            }
            for scene in scenes
        ],
        "raw_rushes_embedded_as_standalone_assets": False,
        "owner_approval_required": True,
    }
    report_path = args.output_dir / "T4_SILENT_RENDER_REPORT.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sums = args.output_dir / "SHA256SUMS.txt"
    files = [output, report_path, contact]
    sums.write_text("".join(f"{sha256(path)}  {path.name}\n" for path in files), encoding="utf-8")
    print(f"T4_SILENT_RENDER_PASS {output} {output_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
