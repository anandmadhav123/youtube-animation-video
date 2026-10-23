import warnings
warnings.filterwarnings("ignore")

import json
import re
from typing import Dict, Any, List
import config

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

PLANNER_SYSTEM_PROMPT = """You are an elite cinematic film director and AI video prompt engineer specializing in Google Veo / Google Flow video generation.

Given a user's master story or combined video prompt (intended for a 2-3 minute video):
1. Break down the story into a sequence of scenes.
2. Each scene represents strictly 8 seconds of continuous video (the exact limit for Google Flow).
3. For a 2.5 minute video, generate around 18-20 scenes.
4. CRITICAL: Maintain strict visual consistency across scenes:
   - Identify the main subjects/characters and specify exact visual descriptors (clothing, hair, facial features) in every prompt where they appear.
   - Maintain the same artistic style, lighting, color grading (e.g. "cinematic 35mm, warm golden hour, photorealistic, 8k resolution, smooth camera movement").
5. Write each scene prompt in vivid English visual descriptions optimized for AI video generators (clear subject, action, camera motion, atmosphere).
6. Also generate metadata for YouTube (engaging title, detailed description with timestamps/summary, and 15 relevant tags).

Output strictly valid JSON with this structure:
{
  "title": "Compelling YouTube Video Title",
  "description": "Engaging description with overview, highlights and hashtags #tag1 #tag2",
  "tags": ["tag1", "tag2", "tag3"],
  "total_scenes": 18,
  "estimated_duration_seconds": 144,
  "scenes": [
    {
      "scene_number": 1,
      "duration": 8,
      "visual_prompt": "Cinematic wide establishing shot of...",
      "narration_or_concept": "Short note about what happens here"
    }
  ]
}
"""

def generate_scene_plan(master_prompt: str, target_minutes: float = 2.5) -> Dict[str, Any]:
    """
    Takes a combined story prompt and returns a structured plan of 8-second scenes.
    """
    total_seconds = int(target_minutes * 60)
    target_scene_count = max(5, round(total_seconds / config.SCENE_DURATION_SECONDS))

    if config.GEMINI_API_KEY and HAS_GENAI:
        try:
            client = genai.Client(api_key=config.GEMINI_API_KEY)
            user_message = f"""
MASTER PROMPT:
{master_prompt}

Target total video duration: {target_minutes} minutes ({total_seconds} seconds).
Required number of 8-second scenes: approximately {target_scene_count} scenes.
Ensure visual style continuity across all scenes.
"""
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=PLANNER_SYSTEM_PROMPT,
                    response_mime_type="application/json"
                )
            )
            data = json.loads(response.text.strip())
            print("[SCENE-PLANNER] Successfully generated scene breakdown using Gemini API.")
            return data
        except Exception as e:
            # Detect corporate proxy / network restriction (e.g. Zscaler)
            err_msg = str(e)
            if "Zscaler" in err_msg or "Blocked" in err_msg or "Forbidden" in err_msg:
                print("[SCENE-PLANNER] Corporate network proxy blocked direct API endpoint. Using Intelligent Beat Splitter.")
            else:
                print(f"[SCENE-PLANNER] API connection note ({e}). Using Intelligent Beat Splitter.")

    return _intelligent_beat_split(master_prompt, target_scene_count)


def _intelligent_beat_split(master_prompt: str, scene_count: int) -> Dict[str, Any]:
    """
    Advanced semantic beat splitter that breaks the master story into narrative beats
    with cinematic camera movements and styling. Runs 100% offline.
    """
    clean_prompt = master_prompt.strip().replace("\r\n", "\n")
    # Split by sentences or punctuation
    sentences = [s.strip() for s in re.split(r'[.!?।\n]+', clean_prompt) if len(s.strip()) > 5]
    if not sentences:
        sentences = [clean_prompt]

    camera_angles = [
        "Cinematic wide establishing shot, slow drone push-in",
        "Eye-level medium tracking shot following the subject",
        "Dramatic low-angle cinematic perspective with volumetric light rays",
        "Intimate close-up with shallow depth of field and beautiful bokeh",
        "High-angle sweeping panoramic shot showing the environment scale",
        "Side profile tracking shot moving smoothly through the space",
        "Over-the-shoulder perspective with cinematic atmosphere and fog",
        "Dynamic slow-motion orbit shot around the central action"
    ]

    cinematic_modifiers = (
        "photorealistic, cinematic lighting, hyper-detailed textures, 35mm film grain, "
        "atmospheric depth, 8k resolution, smooth motion, high-end production quality, 8s clip"
    )

    scenes = []
    for i in range(1, scene_count + 1):
        # Pick relevant sentence beat
        s_idx = (i - 1) % len(sentences)
        beat_text = sentences[s_idx]
        camera = camera_angles[(i - 1) % len(camera_angles)]

        visual_prompt = f"{camera}. {beat_text}. Visual style: {cinematic_modifiers}."

        scenes.append({
            "scene_number": i,
            "duration": config.SCENE_DURATION_SECONDS,
            "visual_prompt": visual_prompt,
            "narration_or_concept": f"Scene {i}/{scene_count}: {beat_text[:60]}"
        })

    title = f"Cinematic Journey: {sentences[0][:50]}"
    description = (
        f"{clean_prompt}\n\n"
        f"Generated automatically with Google Flow & Gemini Video Automation Pipeline.\n"
        f"Total Scenes: {scene_count} (8s each)\n"
        f"#AIVideo #GoogleFlow #GoogleVeo #CinematicAI"
    )
    tags = [
        "Google Flow", "Google Veo", "AI Video Generation", "Cinematic AI",
        "AI Film", "Text to Video", "Automation", "Sci-Fi", "Storytelling"
    ]

    return {
        "title": title,
        "description": description,
        "tags": tags,
        "total_scenes": scene_count,
        "estimated_duration_seconds": scene_count * config.SCENE_DURATION_SECONDS,
        "scenes": scenes
    }


if __name__ == "__main__":
    test_prompt = """
    In a futuristic neon-lit city, an undercover agent races through rainy alleyways. 
    He reaches a hidden cybernetics laboratory deep underground. 
    Inside, glowing holograms reveal an ancient star chart leading beyond known space. 
    He activates his ship's hyperdrive and launches into the cosmos toward an unknown nebula.
    """
    plan = generate_scene_plan(test_prompt, target_minutes=1.5)
    print(json.dumps(plan, indent=2, ensure_ascii=False))
