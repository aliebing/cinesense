"""Takes the two README screenshots in docs/showcase/ against the local app, with film posters and stills blurred:
01-home (the home page after a chat answer) and 02-stage (a film's detail page, reached from the search page).

    python -m venv /tmp/pw && /tmp/pw/bin/pip install playwright
    /tmp/pw/bin/python docs/showcase/shots.py [--base http://localhost:8080]

Needs the local stack (`make up`, or the API and web app run by hand). Two chat turns with the real model (well
under a cent). Posters, stills and trailers are copyrighted, so every picture in the page is blurred before a shot;
text, chips and controls stay sharp. The review deck (docs/presentation/build_review.js) uses the same two shots.
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
BEST = "[aria-label='Best matches'] .related-card"

# Blur every image, video and embed, and every element painted with a background picture (except the curtain).
BLUR_JS = """
() => {
  if (!document.getElementById('shot-blur')) {
    const s = document.createElement('style');
    s.id = 'shot-blur';
    // the shots strip trailer ids (headless Chrome can't play them), so the 'no trailer' note would be wrong
    s.textContent = 'img, video, iframe, picture, canvas { filter: blur(16px) saturate(0.9) !important; } ' +
      '.stage-trailer__note { visibility: hidden !important; }';
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


async def main(base: str) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 1600, "height": 760}, locale="en-GB")
        page = await ctx.new_page()
        await strip_trailers(page)
        await page.goto(base + "/")
        await page.wait_for_timeout(4000)

        box = page.get_by_label("Message CineSense")
        await box.fill(QUERY)
        await page.get_by_label("Send").click()
        await page.locator("[data-testid=chat-pick]").first.wait_for(timeout=120_000)
        await page.wait_for_timeout(3000)
        await shot(page, "01-home")

        await box.fill(FOLLOW_UP)
        await page.get_by_label("Send").click()
        await page.locator("[aria-label^='Remove excluded person']").first.wait_for(timeout=120_000)
        await page.wait_for_timeout(2000)
        await page.get_by_role("button", name="Show results →").first.click()
        await page.locator(BEST).first.wait_for(timeout=30_000)
        await page.wait_for_timeout(2000)
        await page.locator(BEST).first.click()
        await page.get_by_role("button", name="👍 More like this").wait_for(timeout=30_000)
        await page.wait_for_timeout(3000)
        await shot(page, "02-stage")
        await browser.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8080")
    a = ap.parse_args()
    asyncio.run(main(a.base))
