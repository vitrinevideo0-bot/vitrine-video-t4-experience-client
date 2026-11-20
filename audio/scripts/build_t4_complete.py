#!/usr/bin/env python3
"""Build one complete T4 video with VOIX-B and one rotated Afrobeat track.

The approved hybrid-cinematic H.264 stream is copied bit-for-bit. Audio follows
P1/T1 engineering: music at -3 dB, ducked to -10 dB under speech with 120 ms
attack and 450 ms release, then mastered to -16 LUFS / -2 dBTP.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SR = 48_000
TOTAL_S = 30.0
N = int(SR * TOTAL_S)


def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
    print("RUN", " ".join(command), flush=True)
    return subprocess.run(command, check=True, **kwargs)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def decode(path: Path, channels: int) -> np.ndarray:
    raw = run([
        "ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0", "-t", str(TOTAL_S),
        "-ar", str(SR), "-ac", str(channels), "-f", "f32le", "-",
    ], capture_output=True).stdout
    data = np.frombuffer(raw, dtype="<f4").astype(np.float64)
    return data.reshape(-1, channels) if channels > 1 else data


def write_wav(path: Path, data: np.ndarray, codec: str = "pcm_s24le") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    channels = data.shape[1] if data.ndim == 2 else 1
    process = subprocess.Popen([
        "ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR),
        "-ac", str(channels), "-i", "-", "-map_metadata", "-1", "-c:a", codec, str(path),
    ], stdin=subprocess.PIPE)
    process.communicate(np.asarray(data, dtype="<f4").tobytes())
    if process.returncode:
        raise RuntimeError(f"Cannot write {path}")


def loudness(path: Path, target_i: float, target_tp: float) -> dict[str, Any]:
    result = run([
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a:0",
        "-af", f"loudnorm=I={target_i}:TP={target_tp}:LRA=7:print_format=json",
        "-f", "null", "-",
    ], capture_output=True, text=True)
    blocks = re.findall(r'\{\s*"input_i".*?\}', result.stderr, re.S)
    if not blocks:
        raise RuntimeError(f"No loudness measurement for {path}")
    return json.loads(blocks[-1])


def master(source: Path, target: Path, target_i: float, target_tp: float) -> tuple[dict[str, Any], dict[str, Any]]:
    before = loudness(source, target_i, target_tp)
    audio_filter = (
        f"loudnorm=I={target_i}:TP={target_tp}:LRA=7:"
        f"measured_I={before['input_i']}:measured_LRA={before['input_lra']}:"
        f"measured_TP={before['input_tp']}:measured_thresh={before['input_thresh']}:"
        f"offset={before['target_offset']}:linear=false:print_format=summary"
    )
    run([
        "ffmpeg", "-y", "-v", "error", "-i", str(source), "-map", "0:a:0",
        "-af", audio_filter, "-t", str(TOTAL_S), "-ar", str(SR), "-ac", "2",
        "-map_metadata", "-1", "-c:a", "pcm_s24le", str(target),
    ])
    return before, loudness(target, target_i, target_tp)


def stream_hash(path: Path) -> str:
    result = run([
        "ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0",
        "-c", "copy", "-f", "hash", "-hash", "sha256", "-",
    ], capture_output=True, text=True).stdout.strip()
    return result.split("=", 1)[1].lower()


def probe(path: Path) -> dict[str, Any]:
    return json.loads(run([
        "ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format",
        "-of", "json", str(path),
    ], capture_output=True, text=True).stdout)


def sample_qc(audio: np.ndarray) -> dict[str, Any]:
    peak = float(np.max(np.abs(audio)))
    return {
        "sample_peak_dbfs": round(20 * math.log10(max(peak, 1e-12)), 3),
        "clipped_sample_count": int(np.count_nonzero(np.abs(audio) >= 0.999999)),
        "nan_count": int(np.isnan(audio).sum()),
        "inf_count": int(np.isinf(audio).sum()),
        "dc_offset_max_abs": round(float(np.max(np.abs(np.mean(audio, axis=0)))), 7) if audio.ndim == 2 else round(abs(float(np.mean(audio))), 7),
    }


def duck_envelope(spans: list[tuple[float, float]], attack_s: float, release_s: float) -> np.ndarray:
    envelope = np.zeros(N, dtype=np.float64)
    for start, end in spans:
        attack_start = max(0, int(round((start - attack_s) * SR)))
        full_start = int(round(start * SR))
        full_end = min(N, int(round(end * SR)))
        release_end = min(N, int(round((end + release_s) * SR)))
        if full_start > attack_start:
            envelope[attack_start:full_start] = np.maximum(
                envelope[attack_start:full_start],
                np.linspace(0.0, 1.0, full_start - attack_start, endpoint=False),
            )
        envelope[full_start:full_end] = 1.0
        if release_end > full_end:
            envelope[full_end:release_end] = np.maximum(
                envelope[full_end:release_end],
                np.linspace(1.0, 0.0, release_end - full_end, endpoint=False),
            )
    return envelope


def speech_metrics(voice: np.ndarray, music: np.ndarray, spans: list[tuple[float, float]]) -> dict[str, Any]:
    frame = int(0.020 * SR)
    values: list[float] = []
    voice_powers: list[float] = []
    music_powers: list[float] = []
    by_scene: list[dict[str, Any]] = []
    for scene, (start, end) in enumerate(spans, 1):
        local: list[float] = []
        first = int(start * SR) // frame
        last = min(len(voice) // frame, int(math.ceil(end * SR / frame)))
        for index in range(first, last):
            left, right = index * frame, (index + 1) * frame
            vp = float(np.mean(voice[left:right] ** 2))
            if 10 * math.log10(max(vp, 1e-20)) <= -38.0:
                continue
            mp = float(np.mean(music[left:right] ** 2))
            ratio = 10 * math.log10(max(vp, 1e-20) / max(mp, 1e-20))
            values.append(ratio)
            local.append(ratio)
            voice_powers.append(vp)
            music_powers.append(mp)
        by_scene.append({
            "scene": scene,
            "active_speech_s": round(len(local) * 0.020, 3),
            "median_speech_to_music_db": round(float(np.median(local)), 2),
            "p10_speech_to_music_db": round(float(np.percentile(local, 10)), 2),
        })
    aggregate = 10 * math.log10(np.mean(voice_powers) / np.mean(music_powers))
    return {
        "method": "20 ms frames; active voice above -38 dBFS; pre-master stems",
        "active_speech_s": round(len(values) * 0.020, 3),
        "aggregate_speech_to_music_db": round(float(aggregate), 2),
        "median_speech_to_music_db": round(float(np.median(values)), 2),
        "p10_speech_to_music_db": round(float(np.percentile(values, 10)), 2),
        "scenes": by_scene,
    }


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--silent-video", type=Path, required=True)
    parser.add_argument("--render-job", type=Path, required=True)
    parser.add_argument("--music-config", type=Path, default=ROOT / "config/T4_MUSIC_PACK_V1_0_0.json")
    parser.add_argument("--mix-config", type=Path, default=ROOT / "config/T4_VOICE_MIX_V1_0_0.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output/t4-complete-v4.0.0")
    parser.add_argument(
        "--allow-runtime-visual",
        action="store_true",
        help="accept a freshly rendered customer visual only for a Cloudflare runtime RenderJob",
    )
    args = parser.parse_args()

    job = json.loads(args.render_job.read_text(encoding="utf-8"))
    music_config = json.loads(args.music_config.read_text(encoding="utf-8"))
    mix_config = json.loads(args.mix_config.read_text(encoding="utf-8"))
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    require(job["template_id"] == "RESTAURATION-T4", "T4 RenderJob required")
    require(job["template_version"] == "4.0.0-complete-audio", "Complete T4 RenderJob version required")
    tracks = music_config["tracks"]
    require(len(tracks) == 4, "The T4 music pack must contain exactly four tracks")
    require([track["pixabay_id"] for track in tracks] == [569473, 153058, 573648, 439622], "Unexpected T4 music pool")
    require(all(track["audition_approved_by_owner"] and track["production_eligible"] for track in tracks), "Every T4 music track must be approved")
    require(all(track["content_id_registered"] for track in tracks), "Content ID disclosure missing")
    selected = next((track for track in tracks if track["id"] == job["music"]["selected_music_id"]), None)
    require(selected is not None, "Selected T4 music is outside the approved pool")
    require(job["music"]["state_update_policy"] == "after_completed_qc_pass_only", "Invalid music state policy")
    if job["music"]["last_successful_music_id"] is not None:
        require(job["music"]["selected_music_id"] != job["music"]["last_successful_music_id"], "Immediate music repeat")

    verified_tracks = []
    for track in tracks:
        path = ROOT / track["file"]
        require(path.is_file() and sha256(path) == track["sha256"], f"Music derivative integrity failure: {path}")
        verified_tracks.append({"id": track["id"], "choice": track["choice"], "file": track["file"], "sha256": track["sha256"], "bytes": path.stat().st_size})
    music_path = ROOT / selected["file"]

    voice_config = mix_config["voice"]
    require(voice_config["candidate"] == "VOIX-B" and voice_config["voice_id"] == "voice-07", "Unexpected T4 voice")
    stem_path = ROOT / voice_config["stem_file"]
    require(stem_path.is_file() and sha256(stem_path) == voice_config["stem_sha256"], "Voice stem integrity failure")
    require(len(voice_config["clips"]) == 4, "Exactly four T4 voice placements are required")
    for clip in voice_config["clips"]:
        for key, hash_key in (("source", "source_sha256"), ("processed", "processed_sha256")):
            path = ROOT / clip[key]
            require(path.is_file() and sha256(path) == clip[hash_key], f"Voice clip integrity failure: {path}")

    visual = mix_config["visual_approved"]
    render_contract = job["render"]
    visual_mode = render_contract.get("visual_mode", "approved_master_stream_copy")
    runtime_visual = visual_mode == "runtime_hybrid_render"
    require(
        render_contract["visual_source_sha256"] == visual["file_sha256"]
        and render_contract["visual_video_bitstream_sha256"] == visual["video_bitstream_sha256"],
        "Approved T4 visual reference diverges from the locked contract",
    )
    require(render_contract.get("audio_mux_video_reencode_forbidden") is True, "T4 audio mux must copy the video stream")
    require(args.silent_video.is_file(), "T4 silent visual input missing")
    input_file_hash = sha256(args.silent_video)
    input_stream_hash = stream_hash(args.silent_video)
    silent_probe = probe(args.silent_video)
    silent_video_streams = [s for s in silent_probe["streams"] if s.get("codec_type") == "video"]
    silent_audio_streams = [s for s in silent_probe["streams"] if s.get("codec_type") == "audio"]
    require(len(silent_video_streams) == 1, "T4 silent base must contain one video stream")
    require(len(silent_audio_streams) == 0, "T4 silent base must contain no audio stream")
    silent_video_stream = silent_video_streams[0]
    require((silent_video_stream.get("width"), silent_video_stream.get("height")) == (720, 1280), "T4 silent base dimensions must be 720x1280")
    require(silent_video_stream.get("r_frame_rate") == "30/1", "T4 silent base must be 30 fps")
    require(int(silent_video_stream.get("nb_read_frames", "0")) == 900, "T4 silent base must contain 900 frames")
    require(abs(float(silent_probe["format"]["duration"]) - 30.0) <= 0.001, "T4 silent base must last exactly 30 seconds")
    approved_reference_exact = input_file_hash == visual["file_sha256"] and input_stream_hash == visual["video_bitstream_sha256"]
    if runtime_visual:
        require(args.allow_runtime_visual, "Runtime T4 visual requires --allow-runtime-visual")
        require(job["control_plane"] == "cloudflare_worker", "Runtime T4 visual is restricted to Cloudflare-controlled jobs")
        require(render_contract.get("visual_source_role") == "approved_design_reference", "Runtime visual must retain the approved design reference")
        require(render_contract.get("visual_reencode_forbidden") is False, "Runtime customer captures require an explicit visual rebuild")
        require(render_contract.get("runtime_capture_manifest_required") is True, "Runtime visual requires four capture inputs")
        require(
            set(job.get("captures", {})) == {"S1", "S2", "S3", "S4"}
            and all(isinstance(value, dict) and re.fullmatch(r"[0-9a-f]{64}", str(value.get("sha256", ""))) for value in job["captures"].values()),
            "Runtime visual requires four SHA-256 locked captures",
        )
    else:
        require(visual_mode == "approved_master_stream_copy", "Unknown T4 visual mode")
        require(render_contract.get("visual_source_role") == "approved_render_source", "Approved master must be the render source")
        require(render_contract.get("visual_reencode_forbidden") is True, "Approved master visual re-encoding is forbidden")
        require(render_contract.get("runtime_capture_manifest_required") is False, "Approved master must not require runtime captures")
        require(approved_reference_exact, "Approved T4 visual file or stream hash mismatch")

    voice = decode(stem_path, 1)
    music = decode(music_path, 2)
    require(len(voice) == N, f"Voice stem must decode to {N} samples")
    require(len(music) == N, f"Music derivative must decode to {N} samples")
    spans = [(float(clip["start_s"]), float(clip["end_s"])) for clip in voice_config["clips"]]
    duck = mix_config["mix_contract"]
    envelope = duck_envelope(spans, float(duck["duck_attack_ms"]) / 1000.0, float(duck["duck_release_ms"]) / 1000.0)
    gain_db = float(duck["music_open_gain_db"]) + (
        float(duck["music_under_voice_gain_db"]) - float(duck["music_open_gain_db"])
    ) * envelope
    ducked_music = music * (10 ** (gain_db / 20.0))[:, None]
    premix = ducked_music + np.column_stack((voice, voice))
    intelligibility = speech_metrics(voice, ducked_music, spans)

    final_video = output_dir / job["render"]["output_filename"]
    master_wav = output_dir / "T4_MASTER_AUDIO_VOIX_B_MUSIQUE_ROTATION_30S.wav"
    with tempfile.TemporaryDirectory(prefix="t4-complete-") as temporary:
        raw = Path(temporary) / "T4_PREMASTER.wav"
        write_wav(raw, premix)
        before, _ = master(raw, master_wav, float(duck["master_target_lufs"]), float(duck["master_true_peak_dbtp_max"]))

    run([
        "ffmpeg", "-y", "-v", "error", "-i", str(args.silent_video), "-i", str(master_wav),
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-ar", str(SR), "-ac", "2", "-t", str(TOTAL_S), "-map_metadata", "-1",
        "-movflags", "+faststart", str(final_video),
    ])

    wav_audio = decode(master_wav, 2)
    final_audio = decode(final_video, 2)
    wav_loudness = loudness(master_wav, -16.0, -2.0)
    final_loudness = loudness(final_video, -16.0, -1.0)
    output_probe = probe(final_video)
    video_streams = [s for s in output_probe["streams"] if s.get("codec_type") == "video"]
    audio_streams = [s for s in output_probe["streams"] if s.get("codec_type") == "audio"]
    video_stream = video_streams[0] if video_streams else {}
    audio_stream = audio_streams[0] if audio_streams else {}
    output_stream_hash = stream_hash(final_video)
    wav_qc = sample_qc(wav_audio)
    final_qc = sample_qc(final_audio)

    checks = {
        "four_owner_approved_tracks_verified": len(verified_tracks) == 4,
        "one_rotated_music_selected": selected["id"] == job["music"]["selected_music_id"],
        "no_immediate_music_repeat": job["music"]["last_successful_music_id"] is None or selected["id"] != job["music"]["last_successful_music_id"],
        "content_id_disclosed": selected["content_id_registered"] is True and job["music"]["content_id_registered"] is True,
        "voice_is_owner_selected_B": voice_config["candidate"] == "VOIX-B" and voice_config["voice_id"] == "voice-07",
        "four_voice_placements": [clip["start_s"] for clip in voice_config["clips"]] == [1.2, 6.8, 14.7, 21.8],
        "ducking_minus_3_minus_10_db": duck["music_open_gain_db"] == -3.0 and duck["music_under_voice_gain_db"] == -10.0,
        "ducking_attack_release": duck["duck_attack_ms"] == 120 and duck["duck_release_ms"] == 450,
        "master_duration_samples": len(wav_audio) == N,
        "master_loudness": -16.5 <= float(wav_loudness["input_i"]) <= -15.5,
        "master_true_peak": float(wav_loudness["input_tp"]) <= -1.9,
        "aac_loudness": -16.7 <= float(final_loudness["input_i"]) <= -15.3,
        "aac_true_peak": float(final_loudness["input_tp"]) <= -1.0,
        "no_master_clipping": wav_qc["clipped_sample_count"] == wav_qc["nan_count"] == wav_qc["inf_count"] == 0,
        "no_aac_clipping": final_qc["clipped_sample_count"] == final_qc["nan_count"] == final_qc["inf_count"] == 0,
        "speech_over_music": intelligibility["aggregate_speech_to_music_db"] >= 4.0,
        "one_video_stream": len(video_streams) == 1,
        "one_audio_stream": len(audio_streams) == 1,
        "dimensions_720x1280": (video_stream.get("width"), video_stream.get("height")) == (720, 1280),
        "fps_30": video_stream.get("r_frame_rate") == "30/1",
        "frames_900": int(video_stream.get("nb_read_frames", "0")) == 900,
        "duration_30s": abs(float(output_probe["format"]["duration"]) - 30.0) <= 0.001,
        "aac_stereo_48khz": audio_stream.get("codec_name") == "aac" and int(audio_stream.get("sample_rate", "0")) == SR and int(audio_stream.get("channels", 0)) == 2,
        "visual_mode_contract": (runtime_visual and args.allow_runtime_visual and job["control_plane"] == "cloudflare_worker") or (not runtime_visual and approved_reference_exact),
        "audio_mux_video_stream_bit_exact": output_stream_hash == input_stream_hash,
        "state_not_committed_inside_renderer": True,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    report = {
        "schema_version": "1.0.0", "template_id": "RESTAURATION-T4", "status": status,
        "purpose": "single_complete_GitHub_render_with_owner_selected_voice_and_rotated_music",
        "rendered_on": "github_actions" if os.environ.get("GITHUB_ACTIONS") == "true" else "local_preflight",
        "github": {"repository": os.environ.get("GITHUB_REPOSITORY"), "run_id": os.environ.get("GITHUB_RUN_ID"), "run_number": os.environ.get("GITHUB_RUN_NUMBER"), "sha": os.environ.get("GITHUB_SHA")},
        "render_job": str(args.render_job), "job_id": job["job_id"],
        "verified_music_derivatives": verified_tracks,
        "selection": {
            "id": selected["id"], "choice": selected["choice"], "pixabay_id": selected["pixabay_id"],
            "title": selected["title"], "artist": selected["artist"], "file": selected["file"],
            "sha256": selected["sha256"], "source_sha256": selected["source_sha256"],
            "content_id_registered": selected["content_id_registered"],
            "last_successful_music_id": job["music"]["last_successful_music_id"],
            "state_update_policy": job["music"]["state_update_policy"],
        },
        "voice": {
            "candidate": voice_config["candidate"], "voice_id": voice_config["voice_id"],
            "stem_file": voice_config["stem_file"], "stem_sha256": voice_config["stem_sha256"],
            "placements": [{"scene": c["scene"], "start_s": c["start_s"], "end_s": c["end_s"], "text": c["text"]} for c in voice_config["clips"]],
        },
        "mix_contract": duck,
        "visual": {
            "mode": visual_mode,
            "source_role": render_contract["visual_source_role"],
            "input_file": args.silent_video.name,
            "input_file_sha256": input_file_hash,
            "input_video_bitstream_sha256": input_stream_hash,
            "output_video_bitstream_sha256": output_stream_hash,
            "approved_reference_file_sha256": visual["file_sha256"],
            "approved_reference_video_bitstream_sha256": visual["video_bitstream_sha256"],
            "approved_reference_exact": approved_reference_exact,
            "audio_mux_bitstream_copy": output_stream_hash == input_stream_hash,
        },
        "pre_master": {"integrated_lufs": float(before["input_i"]), "true_peak_dbtp": float(before["input_tp"])},
        "master_wav": {"file": master_wav.name, "sha256": sha256(master_wav), "bytes": master_wav.stat().st_size, "duration_samples": len(wav_audio), "integrated_lufs": float(wav_loudness["input_i"]), "true_peak_dbtp": float(wav_loudness["input_tp"]), **wav_qc},
        "final_video": {"file": final_video.name, "sha256": sha256(final_video), "bytes": final_video.stat().st_size, "duration_s": float(output_probe["format"]["duration"]), "frames": int(video_stream.get("nb_read_frames", "0")), "width": video_stream.get("width"), "height": video_stream.get("height"), "fps": video_stream.get("r_frame_rate"), "video_codec": video_stream.get("codec_name"), "pixel_format": video_stream.get("pix_fmt"), "audio_codec": audio_stream.get("codec_name"), "audio_sample_rate": int(audio_stream.get("sample_rate", "0")), "audio_channels": int(audio_stream.get("channels", 0)), "integrated_lufs": float(final_loudness["input_i"]), "true_peak_dbtp": float(final_loudness["input_tp"]), **final_qc},
        "intelligibility": intelligibility,
        "checks": [{"check": key, "status": "PASS" if value else "FAIL"} for key, value in checks.items()],
        "summary": {"passed": sum(checks.values()), "failed": len(checks) - sum(checks.values()), "total": len(checks)},
    }
    report_path = output_dir / "T4_COMPLETE_RENDER_REPORT.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    capture_hashes = {slot: value.get("sha256") for slot, value in job.get("captures", {}).items() if isinstance(value, dict) and value.get("sha256")}
    result = {
        "schema_version": "1.0.0", "status": "COMPLETED" if status == "PASS" else "FAILED",
        "job_id": job["job_id"], "idempotency_key": job["idempotency_key"],
        "template_id": job["template_id"], "template_version": job["template_version"],
        "profile_used": "T4_GITHUB_ACTIONS_COMPLETE_V1", "control_plane": job["control_plane"],
        "output": {"uri": f"output/runtime/{job['job_id']}/{final_video.name}", "file": final_video.name, "sha256": sha256(final_video), "bytes": final_video.stat().st_size},
        "quality": {"status": status, "report": report_path.name, "passed": report["summary"]["passed"], "total": report["summary"]["total"]},
        "inputs": {"music_source_sha256": selected["source_sha256"], "music_derivative_sha256": selected["sha256"], "voice_stem_sha256": voice_config["stem_sha256"], "visual_video_bitstream_sha256": input_stream_hash, "approved_visual_reference_bitstream_sha256": visual["video_bitstream_sha256"], "capture_sha256": capture_hashes},
        "music_state_commit_allowed": status == "PASS",
    }
    result_path = output_dir / "T4_RENDER_RESULT.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    files = [final_video, master_wav, report_path, result_path]
    (output_dir / "SHA256SUMS.txt").write_text("".join(f"{sha256(path)}  {path.name}\n" for path in files), encoding="utf-8")
    print(json.dumps({"status": status, "output": str(final_video), "sha256": sha256(final_video), "music": selected["id"], "checks": report["summary"]}, ensure_ascii=False, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
