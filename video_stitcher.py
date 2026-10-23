import os
import subprocess
from pathlib import Path
from typing import List, Optional
import config

try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = "ffmpeg"


def stitch_clips(
    clip_paths: Optional[List[Path]] = None,
    output_filename: str = "final_combined_video.mp4",
    add_audio_path: Optional[Path] = None
) -> Path:
    """
    Concatenates individual 8-second video clips into a single continuous video.
    Uses FFmpeg concat demuxer for lossless & instant stitching.
    """
    if clip_paths is None or len(clip_paths) == 0:
        # Search clips directory for mp4 files
        clip_paths = sorted(list(config.CLIPS_DIR.glob("scene_*.mp4")))

    if not clip_paths:
        raise ValueError(f"No video clips found in {config.CLIPS_DIR} to stitch.")

    output_path = config.FINAL_VIDEO_DIR / output_filename
    concat_list_file = config.OUTPUT_DIR / "concat_list.txt"

    print(f"\n[STITCHER] Found {len(clip_paths)} clips to combine.")

    # Write concat manifest
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for p in clip_paths:
            # Escape single quotes for ffmpeg
            escaped_path = str(p.resolve()).replace("'", "'\\''")
            f.write(f"file '{escaped_path}'\n")

    # Command 1: Fast lossless stream copy concat
    print(f"[STITCHER] Stitching clips using ffmpeg ({FFMPEG_EXE})...")
    cmd_copy = [
        FFMPEG_EXE,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_file),
        "-c", "copy",
        str(output_path)
    ]

    result = subprocess.run(cmd_copy, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # If stream copy fails (e.g. slight codec/timebase mismatch), re-encode with high quality
    if result.returncode != 0:
        print("[STITCHER] Stream copy failed. Re-encoding with libx264...")
        cmd_reencode = [
            FFMPEG_EXE,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list_file),
            "-c:v", "libx264",
            "-crf", "18",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            str(output_path)
        ]
        res_reencode = subprocess.run(cmd_reencode, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res_reencode.returncode != 0:
            err = res_reencode.stderr.decode("utf-8", errors="ignore")
            raise RuntimeError(f"FFmpeg stitching failed: {err}")

    # Optional: Mix with background music or voiceover if provided
    if add_audio_path and add_audio_path.exists():
        print(f"[STITCHER] Overlaying audio track from {add_audio_path}...")
        final_with_audio = config.FINAL_VIDEO_DIR / f"audio_{output_filename}"
        cmd_audio = [
            FFMPEG_EXE,
            "-y",
            "-i", str(output_path),
            "-i", str(add_audio_path),
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            str(final_with_audio)
        ]
        res_audio = subprocess.run(cmd_audio, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res_audio.returncode == 0:
            output_path = final_with_audio

    print(f"[SUCCESS] Final video stitched successfully: {output_path}")
    print(f"[INFO] Size: {output_path.stat().st_size / (1024*1024):.2f} MB")
    return output_path


if __name__ == "__main__":
    try:
        out = stitch_clips()
        print(f"Stitched video saved to: {out}")
    except Exception as e:
        print(f"Stitcher error: {e}")
