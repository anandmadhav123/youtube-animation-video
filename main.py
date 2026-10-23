import os
import sys
import json
import argparse
import asyncio
from pathlib import Path

import config
from scene_planner import generate_scene_plan
from flow_automator import GoogleFlowAutomator
from video_stitcher import stitch_clips
from youtube_uploader import upload_video_to_youtube


async def run_pipeline(
    master_prompt: str,
    target_minutes: float = config.TOTAL_VIDEO_TARGET_MINUTES,
    skip_flow: bool = False,
    skip_upload: bool = False
):
    print("=" * 65)
    print(" 🎬 GOOGLE FLOW & YOUTUBE AI VIDEO AUTOMATION PIPELINE")
    print("=" * 65)
    print(f"Target Duration: {target_minutes} minutes")
    print(f"Google Flow Project: {config.FLOW_PROJECT_URL}\n")

    # -------------------------------------------------------------
    # Step 1: Break down master prompt into 8-second scenes
    # -------------------------------------------------------------
    print("--- [STEP 1/4] Generating Scene Breakdown (Gemini AI) ---")
    plan = generate_scene_plan(master_prompt, target_minutes=target_minutes)
    
    plan_file = config.OUTPUT_DIR / "current_scene_plan.json"
    with open(plan_file, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)
    
    scenes = plan.get("scenes", [])
    print(f"Total 8-second Scenes Planned: {len(scenes)}")
    print(f"Video Title: {plan.get('title')}")
    print(f"Plan saved to: {plan_file}\n")

    for s in scenes:
        print(f"  [Scene {s['scene_number']}] {s['visual_prompt'][:85]}...")

    # -------------------------------------------------------------
    # Step 2: Google Flow Generation via Browser Automation
    # -------------------------------------------------------------
    print("\n--- [STEP 2/4] Generating Scenes in Google Flow ---")
    if not skip_flow:
        automator = GoogleFlowAutomator()
        try:
            await automator.connect()
            for scene in scenes:
                await automator.generate_scene(
                    scene_number=scene["scene_number"],
                    visual_prompt=scene["visual_prompt"],
                    duration=scene.get("duration", 8)
                )
            print("[FLOW-AGENT] All scenes submitted to Google Flow.")
            print("[FLOW-AGENT] Now downloading all generated clips...")
            downloaded_clips = await automator.export_or_download_clips()
            print(f"[FLOW-AGENT] Downloaded {len(downloaded_clips)} clips ready for stitching.")
        finally:
            await automator.close()
    else:
        print("[INFO] Skipping Google Flow generation (--skip-flow enabled).")

    # -------------------------------------------------------------
    # Step 3: Combine / Stitch Clips into Final 2-3 Minute Video
    # -------------------------------------------------------------
    print("\n--- [STEP 3/4] Combining 8-second Clips (FFmpeg) ---")
    final_video = None
    try:
        final_video = stitch_clips(output_filename="final_story_video.mp4")
    except Exception as e:
        print(f"[WARN] Stitching note: {e}")
        # Look if already stitched video exists
        candidate = config.FINAL_VIDEO_DIR / "final_story_video.mp4"
        if candidate.exists():
            final_video = candidate

    # -------------------------------------------------------------
    # Step 4: YouTube Upload
    # -------------------------------------------------------------
    print("\n--- [STEP 4/4] Uploading to YouTube ---")
    if not skip_upload:
        if final_video and final_video.exists():
            video_url = ""
            try:
                from youtube_browser_uploader import upload_via_youtube_studio
                video_url = await upload_via_youtube_studio(
                    video_file_path=final_video,
                    title=plan.get("title", "AI Generated Video from Google Flow"),
                    description=plan.get("description", "Automated AI video generated via Google Flow pipeline."),
                    privacy_status=config.YOUTUBE_PRIVACY_STATUS or "unlisted"
                )
            except Exception as e:
                print(f"[WARN] Browser uploader note ({e}). Trying API uploader...")
                try:
                    video_url = upload_video_to_youtube(
                        video_file_path=final_video,
                        title=plan.get("title", "AI Generated Video from Google Flow"),
                        description=plan.get("description", "Automated AI video generated via Google Flow pipeline."),
                        tags=plan.get("tags", []),
                        privacy_status=config.YOUTUBE_PRIVACY_STATUS
                    )
                except Exception as api_err:
                    print(f"[ERROR] API upload note: {api_err}")

            print(f"\n🎉 Pipeline Finished Successfully!")
            if video_url:
                print(f"📺 Watch YouTube Video: {video_url}")
        else:
            print("[ERROR] Final video file does not exist. Cannot upload to YouTube.")
    else:
        print("[INFO] Skipping YouTube upload (--skip-upload enabled).")


def main():
    parser = argparse.ArgumentParser(description="Google Flow 2-3 Min AI Video Pipeline")
    parser.add_argument(
        "--prompt", "-p",
        type=str,
        help="Combined master prompt for 2-3 min video"
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="Path to text file containing master prompt"
    )
    parser.add_argument(
        "--minutes", "-m",
        type=float,
        default=config.TOTAL_VIDEO_TARGET_MINUTES,
        help="Target video duration in minutes (default: 2.5)"
    )
    parser.add_argument(
        "--skip-flow",
        action="store_true",
        help="Skip browser generation (e.g. if clips are already downloaded)"
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Skip YouTube upload step"
    )

    args = parser.parse_args()

    # Determine prompt
    master_prompt = args.prompt
    if args.file:
        master_prompt = Path(args.file).read_text(encoding="utf-8")
    
    if not master_prompt:
        print("\n=== ENTER YOUR COMBINED MASTER PROMPT (2-3 MINUTE STORY) ===")
        print("(Press Enter twice or Ctrl+D when finished):\n")
        lines = []
        try:
            while True:
                line = input()
                if not line and lines and not lines[-1]:
                    break
                lines.append(line)
        except EOFError:
            pass
        master_prompt = "\n".join(lines).strip()

    if not master_prompt:
        print("[ERROR] No prompt provided. Exiting.")
        sys.exit(1)

    asyncio.run(
        run_pipeline(
            master_prompt=master_prompt,
            target_minutes=args.minutes,
            skip_flow=args.skip_flow,
            skip_upload=args.skip_upload
        )
    )


if __name__ == "__main__":
    main()
