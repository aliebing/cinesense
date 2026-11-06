"""Takes the README screenshots in docs/showcase/ against the local app, with film posters and stills blurred.

    python -m venv /tmp/pw && /tmp/pw/bin/pip install playwright
    /tmp/pw/bin/python docs/showcase/shots.py [--base http://localhost:8080] [01 02 …]

Needs the local stack (`make up`) and TECH_USER / TECH_PASSWORD from .env for the admin shot. Two chat
turns with the real model (well under a cent). Posters, stills and trailers are copyrighted, so every
picture in the page is blurred before a shot; text, chips and controls stay sharp.
The 👍 given for the profile shot is reset at the end.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

OUT = Path(__file__).resolve().parent
QUERY = "Something like Interstellar, but shorter – and no horror please"
FOLLOW_UP = "but without Matthew McConaughey"
CLIP = {"x": 0, "y": 66, "width": 1600, "height": 626}  # the cinema screen without the black bars
RESULT_CARDS = "[aria-label='Results'] .related-card"
RELAX_CRITERIA = {
    "tags": [{"idx": 266, "weight": 5, "mode": "prefer"}, {"idx": 521, "weight": 5, "mode": "not"}],
    "exclude_genres": ["Horror"],
    "availability": "cinema",
}

# Blur every image, video and embed, and every element painted with a background picture (except the curtain).
BLUR_JS = """
() => {
  if (!document.getElementById('shot-blur')) {
    const s = document.createElement('style');
    s.id = 'shot-blur';
    s.textContent = 'img, video, iframe, picture, canvas { filter: blur(16px) saturate(0.9) !important; }';
    document.head.appendChild(s);
  }
  for (const el of document.querySelectorAll('body *')) {
    const bg = getComputedStyle(el).backgroundImage;
    if (bg && bg.includes('url(') && !bg.includes('curtain')) el.style.setProperty('filter', 'blur(16px)', 'important');
  }
}
"""


async def strip_trailers(page) -> None:
    """Headless Chrome can't play YouTube embeds; drop the trailer ids from API answers (chat stream untouched)."""

    def scrub(v):
        if isinstance(v, dict):
            return {k: (None if k == "youtube_key" else scrub(x)) for k, x in v.items()}
        if isinstance(v, list):
            return [scrub(x) for x in v]
        return v

    async def handle(route):
        url = route.request.url
        if "/api/trailers/report" in url:
            return await route.fulfill(status=204)
        if "/api/chat" in url or route.request.method != "GET":
            return await route.continue_()
        resp = await route.fetch()
        if "json" not in (resp.headers.get("content-type") or ""):
            return await route.fulfill(response=resp)
        await route.fulfill(response=resp, json=scrub(await resp.json()))

    await page.route("**/api/**", handle)


async def shot(page, name: str, **kw) -> None:
    await page.mouse.move(5, 5)
    await page.evaluate(BLUR_JS)
    await page.wait_for_timeout(400)
    await page.screenshot(path=str(OUT / f"{name}.jpg"), type="jpeg", quality=85, clip=CLIP, **kw)
    print("shot", name)


async def main(base: str, only: set[str]) -> None:
    want = lambda n: not only or n in only  # noqa: E731
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 1600, "height": 760}, locale="en-GB")
        page = await ctx.new_page()
        await strip_trailers(page)
        await page.goto(base + "/")
        await page.wait_for_timeout(4000)
        if want("01"):
            await shot(page, "01-home")

        if want("02") or want("03") or want("04") or want("05"):
            box = page.get_by_label("Message CineSense")
            await box.fill(QUERY)
            await page.get_by_label("Send").click()
            await page.locator("[data-testid=chat-pick]").first.wait_for(timeout=120_000)
            await page.locator(".tile-row-wrap--picked").wait_for(timeout=30_000)
            await page.wait_for_timeout(2500)
            if want("02"):
                await shot(page, "02-chat")
            await box.fill(FOLLOW_UP)
            await page.get_by_label("Send").click()
            await page.locator("[aria-label^='Remove excluded person']").first.wait_for(timeout=120_000)
            await page.wait_for_timeout(2500)
            await page.get_by_role("button", name="Show results →").click()
            await page.locator(RESULT_CARDS).first.wait_for(timeout=30_000)
            await page.wait_for_timeout(2500)
            if want("03"):
                await shot(page, "03-results")
            await page.locator(RESULT_CARDS).first.click()
            like = page.get_by_role("button", name="👍 More like this")
            await like.wait_for(timeout=30_000)
            await page.wait_for_timeout(2500)
            if want("04"):
                await shot(page, "04-stage")
            if want("05"):
                await like.click()
                await page.wait_for_timeout(1500)
                await page.get_by_role("link", name="CineSense").first.click()
                await page.wait_for_timeout(2500)
                await page.get_by_label("Profile").first.click()
                await page.get_by_label("Your profile").wait_for(timeout=15_000)
                await page.wait_for_timeout(1500)
                await shot(page, "05-profile")
                await page.get_by_role("button", name="Reset profile").click()
                await page.wait_for_timeout(800)

        if want("06"):
            p2 = await ctx.new_page()
            await strip_trailers(p2)
            await p2.goto(base + "/")
            await p2.evaluate("c => sessionStorage.setItem('cinesense.search', JSON.stringify(c))", RELAX_CRITERIA)
            await p2.goto(base + "/results")
            await p2.wait_for_selector("text=Nothing matches every wish", timeout=30_000)
            await p2.locator("button:has-text('in plot descriptions')").first.click()
            await p2.wait_for_selector(".result-miss", timeout=30_000)
            await p2.wait_for_timeout(2000)
            await shot(p2, "06-widened")
            await p2.close()

        if want("07"):
            env = dict(
                line.split("=", 1)
                for line in (OUT.parents[1] / ".env").read_text().splitlines()
                if "=" in line and not line.startswith("#")
            )
            creds = {
                "username": env["TECH_USER"].strip().strip('"'),
                "password": env["TECH_PASSWORD"].strip().strip('"'),
            }
            admin = await browser.new_context(viewport={"width": 1600, "height": 900}, http_credentials=creds)
            p3 = await admin.new_page()
            await p3.goto(base + "/admin/visitors")
            await p3.wait_for_timeout(5000)
            await p3.screenshot(path=str(OUT / "07-admin-visitors.jpg"), type="jpeg", quality=85)
            print("shot 07-admin-visitors")
            await p3.close()

        await browser.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8080")
    ap.add_argument("only", nargs="*")
    a = ap.parse_args()
    asyncio.run(main(a.base, set(a.only)))
