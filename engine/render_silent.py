#!/usr/bin/env python3
"""T4 V3 silent renderer — three hybrid cinematic rush-change transitions.

Only the three real cuts receive an effect. Each eight-frame window uses one
full-screen signature selected by the owner: whip-pan, zoom match through the
plate, then whip-zoom opening. Stable shot windows are never decorated.
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
ENGINE_VERSION = "3.0.0-hybrid-cinematic-cuts"
SCENE_RANGES = {
    "S1": (0, 179),
    "S2": (180, 419),
    "S3": (420, 629),
    "S4": (630, 899),
}
SCENE_LENGTHS = {scene: end - start + 1 for scene, (start, end) in SCENE_RANGES.items()}
EXPECTED_CUTS = [180, 420, 630]
EXPECTED_WINDOWS = [[176, 183], [416, 423], [626, 633]]
EXPECTED_FAMILIES = [
    "T4_CINEMATIC_WHIP_PAN",
    "T4_CINEMATIC_ZOOM_MATCH",
    "T4_CINEMATIC_WHIP_ZOOM",
]


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


def smoothstep(value: float) -> float:
    value = clamp01(value)
    return value * value * (3.0 - 2.0 * value)


def concentrated_blend(progress: float) -> float:
    return smoothstep((progress - 0.24) / 0.52)


def mix(first: np.ndarray, second: np.ndarray, alpha: float) -> np.ndarray:
    alpha = clamp01(alpha)
    return cv2.addWeighted(first, 1.0 - alpha, second, alpha, 0.0)


def odd_kernel(value: float, maximum: int) -> int:
    integer = max(1, min(maximum, int(round(value))))
    if integer > 1 and integer % 2 == 0:
        integer += 1 if integer < maximum else -1
    return integer


def directional_blur(frame: np.ndarray, axis: str, kernel_size: int) -> np.ndarray:
    if kernel_size <= 1:
        return frame
    kernel_size = max(3, kernel_size | 1)
    kernel = np.zeros((kernel_size, kernel_size), dtype=np.float32)
    if axis == "vertical":
        kernel[:, kernel_size // 2] = 1.0 / kernel_size
    else:
        kernel[kernel_size // 2, :] = 1.0 / kernel_size
    return cv2.filter2D(frame, -1, kernel, borderType=cv2.BORDER_REFLECT_101)


def warp_full(
    frame: np.ndarray,
    scale: float = 1.0,
    dx: float = 0.0,
    dy: float = 0.0,
    center: tuple[float, float] | None = None,
) -> np.ndarray:
    pivot = center or (W / 2, H / 2)
    matrix = cv2.getRotationMatrix2D(pivot, 0.0, scale)
    matrix[0, 2] += dx
    matrix[1, 2] += dy
    return cv2.warpAffine(
        frame,
        matrix,
        (W, H),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REFLECT_101,
    )


def radial_zoom_blur(
    frame: np.ndarray,
    strength: float,
    center: tuple[float, float],
    samples: int = 4,
) -> np.ndarray:
    if strength <= 0.001:
        return frame
    accumulator = frame.astype(np.float32)
    for index in range(1, samples):
        scale = 1.0 + strength * index / (samples - 1)
        accumulator += warp_full(frame, scale=scale, center=center).astype(np.float32)
    return np.clip(accumulator / samples, 0, 255).astype(np.uint8)


def cinematic_whip_pan(outgoing: np.ndarray, incoming: np.ndarray, progress: float) -> np.ndarray:
    if progress <= 0.0:
        return outgoing.copy()
    if progress >= 1.0:
        return incoming.copy()
    eased = smoothstep(progress)
    envelope = math.sin(math.pi * progress)
    kernel = odd_kernel(1 + 40 * envelope, 41)
    scale = 1.0 + 0.035 * envelope
    outgoing_motion = warp_full(outgoing, scale=scale, dx=-110.0 * eased)
    incoming_motion = warp_full(incoming, scale=scale, dx=110.0 * (1.0 - eased))
    outgoing_motion = directional_blur(outgoing_motion, "horizontal", kernel)
    incoming_motion = directional_blur(incoming_motion, "horizontal", kernel)
    return mix(outgoing_motion, incoming_motion, concentrated_blend(progress))


def cinematic_zoom_match(outgoing: np.ndarray, incoming: np.ndarray, progress: float) -> np.ndarray:
    if progress <= 0.0:
        return outgoing.copy()
    if progress >= 1.0:
        return incoming.copy()
    eased = smoothstep(progress)
    envelope = math.sin(math.pi * progress)
    outgoing_center = (W * 0.52, H * 0.57)
    incoming_center = (W * 0.52, H * 0.34)
    outgoing_scale = 1.0 + 0.34 * eased
    incoming_scale = 1.0 + 0.22 * (1.0 - eased)
    outgoing_zoom = warp_full(outgoing, scale=outgoing_scale, center=outgoing_center)
    incoming_zoom = warp_full(incoming, scale=incoming_scale, center=incoming_center)
    outgoing_zoom = radial_zoom_blur(outgoing_zoom, 0.085 * envelope, outgoing_center, samples=4)
    incoming_zoom = radial_zoom_blur(incoming_zoom, 0.060 * envelope, incoming_center, samples=4)
    return mix(outgoing_zoom, incoming_zoom, concentrated_blend(progress))


def cinematic_whip_zoom(outgoing: np.ndarray, incoming: np.ndarray, progress: float) -> np.ndarray:
    if progress <= 0.0:
        return outgoing.copy()
    if progress >= 1.0:
        return incoming.copy()
    eased = smoothstep(progress)
    envelope = math.sin(math.pi * progress)
    kernel = odd_kernel(1 + 30 * envelope, 31)
    outgoing_motion = warp_full(
        outgoing,
        scale=1.0 + 0.16 * eased,
        dx=-72.0 * eased,
        dy=-10.0 * eased,
        center=(W * 0.52, H * 0.38),
    )
    incoming_motion = warp_full(
        incoming,
        scale=1.0 + 0.24 * (1.0 - eased),
        dx=72.0 * (1.0 - eased),
        dy=8.0 * (1.0 - eased),
        center=(W * 0.50, H * 0.50),
    )
    outgoing_motion = directional_blur(outgoing_motion, "horizontal", kernel)
    incoming_motion = directional_blur(incoming_motion, "horizontal", kernel)
    outgoing_motion = radial_zoom_blur(outgoing_motion, 0.035 * envelope, (W * 0.52, H * 0.38), samples=3)
    incoming_motion = radial_zoom_blur(incoming_motion, 0.035 * envelope, (W * 0.50, H * 0.50), samples=3)
    return mix(outgoing_motion, incoming_motion, concentrated_blend(progress))


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


def scene_for_frame(frame_number: int) -> str:
    for scene_id, (start, end) in SCENE_RANGES.items():
        if start <= frame_number <= end:
            return scene_id
    raise ValueError(frame_number)


def scene_local_frame(scene_id: str, frame_number: int) -> int:
    return frame_number - SCENE_RANGES[scene_id][0]


def read_frame_at(capture: cv2.VideoCapture, frame_index: int, label: str) -> np.ndarray:
    capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ok, frame = capture.read()
    if not ok:
        raise RuntimeError(f"Cannot seek {label} frame {frame_index}")
    if frame.shape[:2] != (H, W):
        frame = cv2.resize(frame, (W, H), interpolation=cv2.INTER_CUBIC)
    return frame


def transition_sources(
    event: dict[str, Any],
    local_event: int,
    random_captures: dict[str, cv2.VideoCapture],
) -> tuple[np.ndarray, np.ndarray]:
    outgoing_id = event["outgoing_scene_id"]
    incoming_id = event["incoming_scene_id"]
    outgoing_length = SCENE_LENGTHS[outgoing_id]
    outgoing_index = outgoing_length - 4 + min(local_event, 3)
    incoming_index = max(0, local_event - 4)
    outgoing = read_frame_at(random_captures[outgoing_id], outgoing_index, outgoing_id)
    incoming = read_frame_at(random_captures[incoming_id], incoming_index, incoming_id)
    return outgoing, incoming


def apply_transition(
    event: dict[str, Any],
    outgoing: np.ndarray,
    incoming: np.ndarray,
    progress: float,
) -> np.ndarray:
    family = event["family"]
    if family == "T4_CINEMATIC_WHIP_PAN":
        return cinematic_whip_pan(outgoing, incoming, progress)
    if family == "T4_CINEMATIC_ZOOM_MATCH":
        return cinematic_zoom_match(outgoing, incoming, progress)
    if family == "T4_CINEMATIC_WHIP_ZOOM":
        return cinematic_whip_zoom(outgoing, incoming, progress)
    raise RuntimeError(f"Unsupported V3 transition family: {family}")


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


def validate_contract(contract: dict[str, Any]) -> list[dict[str, Any]]:
    events = contract["timeline_events"]
    if contract.get("schema_version") != "3.0.0":
        raise SystemExit("Hybrid transition contract schema 3.0.0 is required")
    if len(events) != 3:
        raise SystemExit("T4 V3 must contain exactly three transitions")
    if [event["cut_frame"] for event in events] != EXPECTED_CUTS:
        raise SystemExit("Transitions must be centered on frames 180, 420 and 630")
    if [event["frames"] for event in events] != EXPECTED_WINDOWS:
        raise SystemExit("V3 transition windows must span four frames before and after each cut")
    if [event["family"] for event in events] != EXPECTED_FAMILIES:
        raise SystemExit("The owner-selected hybrid signature order is not respected")
    for event in events:
        if event["duration_frames"] != 8 or event.get("full_frame_only") is not True:
            raise SystemExit(f"Invalid hybrid transition event: {event['event_id']}")
        if event.get("clean_endpoint_frames_required") is not True:
            raise SystemExit(f"Clean transition endpoints are required: {event['event_id']}")
    owner = contract["owner_constraints"]
    required_true = [
        "transitions_only_around_rush_changes_required",
        "full_frame_between_transition_windows_required",
        "three_distinct_cinematic_signatures_required",
        "clean_landing_on_incoming_rush_required",
        "mosaic_forbidden",
        "dynamic_grid_forbidden",
        "multi_panel_forbidden",
        "glitch_forbidden",
        "rgb_split_forbidden",
        "rectangular_block_stutter_forbidden",
        "silent_render_text_forbidden",
        "silent_render_audio_forbidden",
    ]
    if not all(owner.get(key) is True for key in required_true):
        raise SystemExit("Hybrid owner constraints are incomplete")
    return events


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("rushes/manifest.json"))
    parser.add_argument("--contract", type=Path, default=Path("reverse-engineering/T4_TRANSITIONS_HYBRIDES_30S_V3.json"))
    parser.add_argument("--render-job", type=Path, default=Path("demo/render_job_hybrid_v3.json"))
    parser.add_argument("--cache", type=Path, default=Path("rushes/cache"))
    parser.add_argument("--work", type=Path, default=Path(".tmp/t4-hybrid-v3"))
    parser.add_argument("--output-dir", type=Path, default=Path("output/t4-hybrid-v3.0.0"))
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    render_job = json.loads(args.render_job.read_text(encoding="utf-8"))
    if render_job["template_id"] != "RESTAURATION-T4" or render_job.get("template_version") != "3.0.0":
        raise SystemExit("T4 V3 RenderJob is required")
    scenes = manifest["scenes"]
    if [int(scene["duration_seconds"]) for scene in scenes] != [6, 8, 7, 9]:
        raise SystemExit("Scene durations must be 6/8/7/9")
    events = validate_contract(contract)

    event_for_frame: list[dict[str, Any] | None] = [None] * TOTAL
    for event in events:
        start, end = event["frames"]
        for frame_number in range(start, end + 1):
            if event_for_frame[frame_number] is not None:
                raise RuntimeError(f"Event overlap at frame {frame_number}")
            event_for_frame[frame_number] = event
    expected_active = []
    for start, end in EXPECTED_WINDOWS:
        expected_active.extend(range(start, end + 1))
    active_frames = [index for index, event in enumerate(event_for_frame) if event is not None]
    if active_frames != expected_active:
        raise RuntimeError("Transition frames exist outside the three V3 cut windows")
    if any(event_for_frame[frame] is not None for frame in range(810, 900)):
        raise RuntimeError("S4 final 90 frames must remain stable")

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

    output_name = render_job["output"].get("filename", "VIDEO_T4_EXPERIENCE_CLIENT_TRANSITIONS_HYBRIDES_V3_A_VALIDER.mp4")
    if Path(output_name).name != output_name or not output_name.endswith(".mp4"):
        raise SystemExit("Invalid output filename")
    output = args.output_dir / output_name
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

    sequential_captures = {scene_id: cv2.VideoCapture(str(path)) for scene_id, path in intermediates.items()}
    random_captures = {scene_id: cv2.VideoCapture(str(path)) for scene_id, path in intermediates.items()}
    expected_event_counts = {event["event_id"]: event["duration_frames"] for event in events}
    applied_counts = {event["event_id"]: 0 for event in events}
    event_max_delta = {event["event_id"]: 0.0 for event in events}
    endpoint_deltas = {event["event_id"]: {"start": None, "end": None} for event in events}
    sample_hashes: dict[str, dict[str, str]] = {event["event_id"]: {} for event in events}

    try:
        for frame_number in range(TOTAL):
            scene_id = scene_for_frame(frame_number)
            local_scene = scene_local_frame(scene_id, frame_number)
            ok, base = sequential_captures[scene_id].read()
            if not ok:
                raise RuntimeError(f"Cannot read {scene_id} frame {local_scene}")
            if base.shape[:2] != (H, W):
                base = cv2.resize(base, (W, H), interpolation=cv2.INTER_CUBIC)
            event = event_for_frame[frame_number]
            frame = base
            if event is not None:
                start, end = event["frames"]
                local_event = frame_number - start
                duration = end - start + 1
                progress = local_event / (duration - 1)
                outgoing, incoming = transition_sources(event, local_event, random_captures)
                frame = apply_transition(event, outgoing, incoming, progress)
                delta = float(cv2.absdiff(frame, base).mean())
                event_id = event["event_id"]
                event_max_delta[event_id] = max(event_max_delta[event_id], delta)
                applied_counts[event_id] += 1
                if local_event == 0:
                    endpoint_deltas[event_id]["start"] = float(cv2.absdiff(frame, outgoing).mean())
                if local_event == duration - 1:
                    endpoint_deltas[event_id]["end"] = float(cv2.absdiff(frame, incoming).mean())
                markers = {start: "start", (start + end) // 2: "middle", end: "end"}
                if frame_number in markers:
                    sample_hashes[event_id][markers[frame_number]] = hashlib.sha256(frame.tobytes()).hexdigest()
            encoder.stdin.write(np.ascontiguousarray(frame).tobytes())
            if frame_number % 90 == 0:
                print(f"RENDER {frame_number}/{TOTAL}", flush=True)
    finally:
        encoder.stdin.close()
        return_code = encoder.wait()
        for capture in list(sequential_captures.values()) + list(random_captures.values()):
            capture.release()
    if return_code != 0:
        raise RuntimeError(f"FFmpeg failed with code {return_code}")
    if applied_counts != expected_event_counts:
        raise RuntimeError("Hybrid transition coverage mismatch")
    if not all(
        float(values["start"] or 0.0) <= 0.01 and float(values["end"] or 0.0) <= 0.01
        for values in endpoint_deltas.values()
    ):
        raise RuntimeError(f"A transition endpoint is not clean: {endpoint_deltas}")

    contact = args.output_dir / "T4_TRANSITIONS_HYBRIDES_PROOF_V3.jpg"
    samples = [
        0, 120, 174, 175, 176,
        177, 178, 179, 180, 181,
        182, 183, 184, 300, 414,
        415, 416, 417, 418, 419,
        420, 421, 422, 423, 424,
        520, 624, 625, 626, 627,
        628, 629, 630, 631, 632,
        633, 634, 720, 810, 899,
    ]
    make_contact_sheet(output, contact, samples)
    output_hash = sha256(output)
    covered_frames = sum(expected_event_counts.values())
    report = {
        "schema_version": "3.0.0",
        "template_id": "RESTAURATION-T4",
        "engine_version": ENGINE_VERSION,
        "status": "hybrid_cinematic_candidate_v3_pending_owner_review",
        "rendered_on": "github_actions" if os.environ.get("GITHUB_ACTIONS") == "true" else "local_preflight",
        "owner_choice": "approvals/CHOIX_TRANSITIONS_HYBRIDES_V3_2026-11-18.json",
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
        "transition_style": {
            "name": "owner_selected_hybrid_cinematic",
            "transition_count": 3,
            "cut_frames": EXPECTED_CUTS,
            "cut_seconds": [6, 14, 21],
            "windows": EXPECTED_WINDOWS,
            "frames_per_transition": 8,
            "families": EXPECTED_FAMILIES,
            "transitions_only_around_rush_changes": True,
            "full_frame_only": True,
            "clean_endpoint_frames": True,
        },
        "retired_effects": {
            "mosaic": False,
            "dynamic_grid": False,
            "multi_panel": False,
            "rectangular_block_stutter": False,
            "glitch": False,
            "rgb_split": False,
            "solid_color_bar": False,
            "persistent_shake": False,
        },
        "events": [
            {
                "event_id": event["event_id"],
                "family": event["family"],
                "variant": event["variant"],
                "outgoing_scene_id": event["outgoing_scene_id"],
                "incoming_scene_id": event["incoming_scene_id"],
                "cut_frame": event["cut_frame"],
                "frames": event["frames"],
                "expected_frame_count": expected_event_counts[event["event_id"]],
                "applied_frame_count": applied_counts[event["event_id"]],
                "max_mean_absolute_delta_from_timeline_base": round(event_max_delta[event["event_id"]], 6),
                "endpoint_mean_absolute_delta": {
                    key: round(float(value or 0.0), 6)
                    for key, value in endpoint_deltas[event["event_id"]].items()
                },
                "sample_frame_sha256": sample_hashes[event["event_id"]],
            }
            for event in events
        ],
        "all_3_hybrid_transitions_applied": applied_counts == expected_event_counts,
        "all_events_visibly_nonzero": all(value > 1.0 for value in event_max_delta.values()),
        "all_transition_endpoints_clean": all(
            float(value or 0.0) <= 0.01
            for values in endpoint_deltas.values()
            for value in values.values()
        ),
        "stable_full_frame_audit": {
            "transition_frames": covered_frames,
            "stable_full_frame_frames": TOTAL - covered_frames,
            "stable_full_frame_share": round((TOTAL - covered_frames) / TOTAL, 6),
            "transition_share": round(covered_frames / TOTAL, 6),
            "events_outside_rush_change_windows": 0,
        },
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
            "mosaic_or_grid_rendered": False,
            "glitch_or_rgb_split_rendered": False,
            "persistent_shake_rendered": False,
            "rotation_rendered": False,
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
    print(f"T4_HYBRID_RENDER_PASS {output} {output_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
