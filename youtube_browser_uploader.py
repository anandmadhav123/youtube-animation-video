import os
import time
import json
import asyncio
from pathlib import Path
from typing import List, Optional
import config
from playwright.async_api import async_playwright, Page, BrowserContext

DEBUG_DIR = config.OUTPUT_DIR / "debug"
DEBUG_DIR.mkdir(parents=True, exist_ok=True)
PROFILE_DIR = Path.home() / ".chrome-flow-automation"


async def upload_via_youtube_studio(
    video_file_path: Path,
    title: str,
    description: str,
    privacy_status: str = "unlisted"  # 'private', 'unlisted', 'public'
) -> str:
    """
    Automates YouTube Studio web upload using the logged-in Google Chrome profile.
    Bypasses API quotas and doesn't require Google Cloud Console OAuth setup.
    """
    if not video_file_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_file_path}")

    print("=" * 65)
    print(" 📺 YOUTUBE STUDIO DIRECT UPLOAD AGENT")
    print("=" * 65)
    print(f"File:     {video_file_path.name} ({video_file_path.stat().st_size / (1024*1024):.2f} MB)")
    print(f"Title:    {title}")
    print(f"Privacy:  {privacy_status}")
    print("=" * 65)

    playwright = await async_playwright().start()
    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        channel="chrome",
        headless=False,
        args=[
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled"
        ]
    )

    page = context.pages[0] if context.pages else await context.new_page()
    print("[YOUTUBE-AGENT] Navigating to YouTube Upload...")
    await page.goto("https://www.youtube.com/upload", wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(5)

    # Find file input
    file_input = page.locator('input[type="file"]')
    if await file_input.count() == 0:
        # Check if "Create" button needs to be clicked
        create_btn = page.locator('#create-icon, button:has-text("Create")').first
        if await create_btn.count() > 0 and await create_btn.is_visible():
            await create_btn.click()
            await asyncio.sleep(1)
            up_option = page.locator('text="Upload videos"').first
            if await up_option.count() > 0:
                await up_option.click()
                await asyncio.sleep(2)

    file_input = page.locator('input[type="file"]').first
    print("[YOUTUBE-AGENT] Attaching video file...")
    await file_input.set_input_files(str(video_file_path.resolve()))
    await asyncio.sleep(6)

    # Wait for details dialog
    print("[YOUTUBE-AGENT] Filling video details...")
    
    # Title input
    title_box = page.locator('#title-textarea #textbox, [aria-label*="title" i][contenteditable="true"]').first
    if await title_box.count() > 0 and await title_box.is_visible():
        await title_box.click()
        await page.keyboard.press("Meta+A")
        await page.keyboard.press("Backspace")
        await title_box.fill(title[:100])
        await asyncio.sleep(1)

    # Description input
    desc_box = page.locator('#description-textarea #textbox, [aria-label*="description" i][contenteditable="true"]').first
    if await desc_box.count() > 0 and await desc_box.is_visible():
        await desc_box.click()
        await page.keyboard.press("Meta+A")
        await page.keyboard.press("Backspace")
        await desc_box.fill(description[:4900])
        await asyncio.sleep(1)

    # Audience: Set "Not made for kids"
    not_for_kids = page.locator('[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"], tp-yt-paper-radio-button[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"], [aria-label*="not made for kids" i]').first
    if await not_for_kids.count() > 0:
        print("[YOUTUBE-AGENT] Setting audience: Not made for kids...")
        await not_for_kids.scroll_into_view_if_needed()
        await not_for_kids.click(force=True)
        await asyncio.sleep(1)

    # Extract Video Link
    video_url = ""
    link_loc = page.locator('a.ytcp-video-info, a[href*="youtu.be"]').first
    if await link_loc.count() > 0:
        video_url = await link_loc.get_attribute("href")
        print(f"[YOUTUBE-AGENT] Detected Video URL: {video_url}")

    # Step through wizard: Next -> Next -> Next
    for step in range(3):
        next_btn = page.locator('#next-button, button:has-text("Next")').first
        if await next_btn.count() > 0 and await next_btn.is_visible():
            print(f"[YOUTUBE-AGENT] Advancing wizard step {step + 1}...")
            await next_btn.click()
            await asyncio.sleep(2)

    # Visibility step
    print(f"[YOUTUBE-AGENT] Setting visibility: {privacy_status}...")
    if privacy_status.lower() == "public":
        vis_radio = page.locator('[name="PUBLIC"], tp-yt-paper-radio-button[name="PUBLIC"], #public-radio-button').first
    elif privacy_status.lower() == "private":
        vis_radio = page.locator('[name="PRIVATE"], tp-yt-paper-radio-button[name="PRIVATE"], #private-radio-button').first
    else:  # unlisted
        vis_radio = page.locator('[name="UNLISTED"], tp-yt-paper-radio-button[name="UNLISTED"], #unlisted-radio-button').first

    if await vis_radio.count() > 0:
        await vis_radio.scroll_into_view_if_needed()
        await vis_radio.click(force=True)
        await asyncio.sleep(1)

    # Check for video link again if not captured earlier
    if not video_url:
        link_loc = page.locator('a[href*="youtu.be"]').first
        if await link_loc.count() > 0:
            video_url = await link_loc.get_attribute("href")

    # Click Save / Publish / Done button inside dialog
    save_btn = page.locator('ytcp-uploads-dialog #done-button, ytcp-button#done-button, #done-button').first
    if await save_btn.count() > 0:
        print("[YOUTUBE-AGENT] Clicking Save/Publish button inside dialog...")
        await save_btn.click(force=True)
        await asyncio.sleep(5)

    # Capture completion screenshot
    screenshot_path = DEBUG_DIR / f"{int(time.time())}_youtube_upload_complete.png"
    await page.screenshot(path=str(screenshot_path))
    print(f"[DEBUG] Upload completion screenshot: {screenshot_path}")

    await context.close()
    await playwright.stop()

    print("\n" + "=" * 65)
    print("🎉 YOUTUBE UPLOAD COMPLETE!")
    print(f"Watch URL: {video_url or 'Available on your YouTube Studio content page'}")
    print("=" * 65)
    return video_url or "https://studio.youtube.com"


if __name__ == "__main__":
    import json
    plan_file = config.OUTPUT_DIR / "current_scene_plan.json"
    title = "Cinematic AI: Europa Ice Cave Journey"
    desc = "Generated via Google Flow & AI Automation Pipeline."
    if plan_file.exists():
        data = json.loads(plan_file.read_text(encoding="utf-8"))
        title = data.get("title", title)
        desc = data.get("description", desc)

    video_file = config.FINAL_VIDEO_DIR / "final_combined_video.mp4"
    if not video_file.exists():
        # Fallback to any mp4 in final dir
        candidates = list(config.FINAL_VIDEO_DIR.glob("*.mp4"))
        if candidates:
            video_file = candidates[0]

    asyncio.run(
        upload_via_youtube_studio(
            video_file_path=video_file,
            title=title,
            description=desc,
            privacy_status=config.YOUTUBE_PRIVACY_STATUS or "unlisted"
        )
    )
