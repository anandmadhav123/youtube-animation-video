import os
import time
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import config
from playwright.async_api import async_playwright, Page, BrowserContext

DEBUG_DIR = config.OUTPUT_DIR / "debug"
DEBUG_DIR.mkdir(parents=True, exist_ok=True)
PROFILE_DIR = Path.home() / ".chrome-flow-automation"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)


class GoogleFlowAutomator:
    """
    Automates Google Flow (flow.google.com) project using Playwright Persistent Context with Google Chrome.
    Handles scene generation, credit auto-approval, and automatic batch downloading of 8s MP4 clips.
    """

    def __init__(self, project_url: str = config.FLOW_PROJECT_URL):
        self.project_url = project_url
        self.playwright = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def connect(self):
        """
        Launches Google Chrome with a persistent profile so logins and cookies are retained permanently.
        """
        print(f"[FLOW-AGENT] Launching Chrome with automation profile ({PROFILE_DIR})...")
        self.playwright = await async_playwright().start()

        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",
            headless=False,
            accept_downloads=True,
            downloads_path=str(config.CLIPS_DIR),
            args=[
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-blink-features=AutomationControlled"
            ]
        )

        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        print(f"[FLOW-AGENT] Navigating to Google Flow: {self.project_url}")
        await self.page.goto(self.project_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)

        # Check for landing page "Create with Google Flow" button
        create_btn = self.page.locator('button:has-text("Create with Google Flow"), a:has-text("Create with Google Flow")')
        if await create_btn.count() > 0 and await create_btn.first.is_visible():
            print("[FLOW-AGENT] Detected landing page. Clicking 'Create with Google Flow' button...")
            await create_btn.first.click()
            await asyncio.sleep(3)

        # Check if user needs to log into Google Account
        current_url = self.page.url
        if "about" in current_url or "signin" in current_url or "accounts.google.com" in current_url:
            print("\n" + "=" * 65)
            print("🔑 [ACTION REQUIRED] GOOGLE LOGIN NEEDED")
            print("=" * 65)
            print("Please log into your Google Account in the opened Chrome window.")
            print("=" * 65 + "\n")
            
            while True:
                url = self.page.url
                if "accounts.google.com" not in url and "about" not in url:
                    if "project" not in url:
                        print(f"[FLOW-AGENT] Redirecting to project: {self.project_url}")
                        await self.page.goto(self.project_url, wait_until="domcontentloaded")
                        await asyncio.sleep(3)
                    print(f"[FLOW-AGENT] Successfully logged in! Active on: {self.page.url}")
                    break
                await asyncio.sleep(2)

        print(f"[FLOW-AGENT] Ready on Google Flow project page.")
        await asyncio.sleep(3)
        await self.handle_overlay_drawers()
        await self.capture_debug_screenshot("connected")

    async def handle_overlay_drawers(self):
        """Closes any open sidebar or instruction drawers and approves credits."""
        if not self.page:
            return
        
        # If 'Agent instructions' drawer is open, click 'Done'
        done_btn = self.page.locator('button:has-text("Done")')
        if await done_btn.count() > 0 and await done_btn.first.is_visible():
            await done_btn.first.click()
            await asyncio.sleep(1)

        # Check for credit approval prompts ("Always approve" or "Approve")
        always_approve = self.page.locator('button:has-text("Always approve")')
        if await always_approve.count() > 0 and await always_approve.first.is_visible():
            print("[FLOW-AGENT] Auto-approving generation credits ('Always approve')...")
            await always_approve.first.click()
            await asyncio.sleep(1)
            return

        approve_btn = self.page.locator('button:has-text("Approve")')
        if await approve_btn.count() > 0 and await approve_btn.first.is_visible():
            print("[FLOW-AGENT] Auto-approving generation credits ('Approve')...")
            await approve_btn.first.click()
            await asyncio.sleep(1)

    async def capture_debug_screenshot(self, name: str):
        """Captures a debug screenshot to verify the UI state."""
        screenshot_path = DEBUG_DIR / f"{int(time.time())}_{name}.png"
        if self.page:
            try:
                await self.page.screenshot(path=str(screenshot_path))
                print(f"[DEBUG] Screenshot saved: {screenshot_path}")
            except Exception as e:
                pass

    async def find_prompt_input(self):
        """Locates the video prompt input field on Google Flow."""
        await self.handle_overlay_drawers()
        selectors = [
            'textarea[placeholder*="What do you want to create" i]',
            '[contenteditable="true"]',
            'textarea[placeholder*="prompt" i]',
            'textarea[placeholder*="describe" i]',
            'div[role="textbox"]',
            'textarea',
            'input[type="text"][placeholder*="create" i]'
        ]
        for sel in selectors:
            loc = self.page.locator(sel)
            count = await loc.count()
            for i in range(count):
                el = loc.nth(i)
                tag = await el.evaluate("node => node.tagName.toLowerCase()")
                if tag != "button" and await el.is_visible():
                    return el
        return None

    async def generate_scene(self, scene_number: int, visual_prompt: str, duration: int = 8) -> Dict[str, Any]:
        """
        Submits a scene prompt into Google Flow, approves credits, and awaits generation.
        """
        print(f"\n=======================================================")
        print(f"[FLOW-AGENT] Processing Scene {scene_number} ({duration}s)")
        print(f"[PROMPT]: {visual_prompt}")
        print(f"=======================================================")

        await self.handle_overlay_drawers()
        input_field = await self.find_prompt_input()
        if not input_field:
            await self.capture_debug_screenshot(f"scene_{scene_number}_no_input")
            print(f"[FLOW-AGENT] Prompt box not found. Waiting 10 seconds...")
            await asyncio.sleep(10)
            return {"scene_number": scene_number, "status": "waiting"}

        # Clear and fill the prompt
        await input_field.click()
        await self.page.keyboard.press("Meta+A")
        await self.page.keyboard.press("Backspace")
        await input_field.fill(visual_prompt)
        await asyncio.sleep(1)

        # Press Enter to submit
        print(f"[FLOW-AGENT] Sending prompt...")
        await self.page.keyboard.press("Enter")
        await asyncio.sleep(3)

        # Check for credit approval prompt
        await self.handle_overlay_drawers()

        print(f"[FLOW-AGENT] Scene {scene_number} submitted. Waiting for generation to finish...")
        await self.wait_for_render_completion(scene_number)
        
        await self.capture_debug_screenshot(f"scene_{scene_number}_completed")
        return {
            "scene_number": scene_number,
            "status": "completed",
            "prompt": visual_prompt
        }

    async def wait_for_render_completion(self, scene_number: int, timeout_seconds: int = 180):
        """Polls until render completes."""
        start_time = time.time()
        await asyncio.sleep(4)

        loading_selectors = [
            '[aria-busy="true"]',
            '.loading',
            '.spinner',
            'progress',
            'div[role="progressbar"]',
            'text=Generating',
            'text=Rendering'
        ]

        while time.time() - start_time < timeout_seconds:
            await self.handle_overlay_drawers()
            is_busy = False
            for sel in loading_selectors:
                loc = self.page.locator(sel)
                if await loc.count() > 0 and await loc.first.is_visible():
                    is_busy = True
                    break

            if not is_busy and (time.time() - start_time) > 15:
                print(f"[FLOW-AGENT] Scene {scene_number} render finished ({int(time.time() - start_time)}s elapsed).")
                return True

            elapsed = int(time.time() - start_time)
            print(f"[FLOW-AGENT] Scene {scene_number} rendering in progress... ({elapsed}s)", end="\r")
            await asyncio.sleep(4)

        print(f"\n[WARN] Scene {scene_number} render wait reached {timeout_seconds}s timeout.")
        return False

    async def export_or_download_clips(self) -> List[Path]:
        """
        Navigates to Videos gallery, iterates through generated scenes, and downloads each 8s clip in 720p.
        """
        print("\n[FLOW-AGENT] Starting automated download of generated video clips...")
        downloaded_paths = []

        # Make sure we are on project page
        if "project" not in self.page.url:
            await self.page.goto(self.project_url, wait_until="domcontentloaded")
            await asyncio.sleep(4)

        # Click 'Videos' tab in left sidebar
        vid_tab = self.page.locator('text=Videos')
        if await vid_tab.count() > 0:
            print("[FLOW-AGENT] Opening Videos gallery...")
            await vid_tab.first.click()
            await asyncio.sleep(3)

        # Open the first video card to enter timeline editor
        preview = self.page.locator('div:has(> img), div:has(> canvas), .media-card, [class*="media"]').first
        if await preview.count() > 0:
            await preview.click()
            await asyncio.sleep(3)

        # Find top thumbnail items representing each scene
        top_thumbnails = self.page.locator('div[class*="thumbnail"], img[class*="thumbnail"], .preview-item, [role="tab"]')
        count = await top_thumbnails.count()
        print(f"[FLOW-AGENT] Found {count} scene thumbnails in editor gallery.")

        if count == 0:
            # Fallback: Just download currently active video
            count = 1

        for i in range(count):
            scene_idx = i + 1
            dest_file = config.CLIPS_DIR / f"scene_{scene_idx:02d}.mp4"

            if count > 1:
                try:
                    thumb = top_thumbnails.nth(i)
                    if await thumb.is_visible():
                        await thumb.scroll_into_view_if_needed()
                        await thumb.click(force=True)
                        await asyncio.sleep(2)
                except Exception as e:
                    print(f"[FLOW-AGENT] Thumbnail click note for scene {scene_idx}: {e}")

            # Find Download button
            dl_btn = self.page.locator('[aria-label*="Download media" i]').first
            if await dl_btn.count() > 0 and await dl_btn.is_visible():
                await dl_btn.click()
                await asyncio.sleep(1)

                btn720 = self.page.locator('button.mat-mdc-menu-item:has-text("720p")').first
                if await btn720.count() > 0 and await btn720.is_visible():
                    print(f"[FLOW-AGENT] Downloading Scene {scene_idx} (720p MP4)...")
                    try:
                        async with self.page.expect_download(timeout=30000) as dl_info:
                            await btn720.click()
                        download = await dl_info.value
                        await download.save_as(str(dest_file))
                        print(f"[FLOW-AGENT] Saved: {dest_file.name} ({dest_file.stat().st_size / (1024*1024):.2f} MB)")
                        downloaded_paths.append(dest_file)
                    except Exception as e:
                        print(f"[WARN] Download for scene {scene_idx} timed out or failed: {e}")
                else:
                    # Close menu if 720p option not found
                    await self.page.keyboard.press("Escape")
            await asyncio.sleep(1)

        # Also collect any existing clips
        existing = sorted(list(config.CLIPS_DIR.glob("scene_*.mp4")))
        return existing if existing else downloaded_paths

    async def close(self):
        """Cleanly releases playwright resources."""
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
        print("[FLOW-AGENT] Playwright session closed.")
