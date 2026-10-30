"""Video 1: how a user works with CineSense (German voice-over, real screen recording).

Needs the API and the web app running (default http://localhost:3100). Usage:
    python scripts/video/user_demo.py [--base http://localhost:3100] [--out scripts/video/out]
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright
from recorder import (
    CURSOR_JS,
    H,
    Screencast,
    Segment,
    W,
    click,
    glide,
    glide_to,
    narrate,
    render,
    strip_trailers,
    synthesize,
)

QUERY = "Something like Interstellar, but shorter – and no horror please"

SEGMENTS = [
    Segment(
        "01_intro",
        "Willkommen bei CineSense. Die Idee: Du suchst keinen Film aus einer endlosen Liste aus, "
        "sondern wählst ein Gefühl. Die Startseite ist wie ein Kinosaal gestaltet, mit Leinwand, Vorhang, "
        "Nebel und Projektorlicht. Im Hintergrund wechseln sechs Stimmungswelten, zum Beispiel Spannung, "
        "Komödie oder Liebe, und Filmreihen ziehen vorbei.",
    ),
    Segment(
        "02_type",
        "Am einfachsten startest du mit dem Chat. Ich schreibe einfach in eigenen Worten, worauf "
        "ich Lust habe: etwas wie Interstellar, aber kürzer, und bitte keinen Horror.",
    ),
    Segment(
        "03_agent",
        "Jetzt arbeitet ein KI-Agent. Er übersetzt meinen Wunsch in konkrete Suchkriterien. "
        "Er wählt passende Stimmungs-Tags aus, zum Beispiel Raumfahrt und Science-Fiction, setzt eine "
        "Obergrenze für die Laufzeit und macht aus „kein Horror“ einen Ausschluss. Die eigentliche Suche "
        "danach ist deterministisch. Das Sprachmodell darf keine Filme erfinden, es erklärt nur, was die "
        "Suche im echten Katalog gefunden hat.",
    ),
    Segment(
        "04_reply",
        "Die Antwort kommt mit Vorschlägen, jeder mit einer kurzen Begründung und einem "
        "Prozentwert, wie gut er passt. Links siehst du, was der Agent eingestellt hat: Jeder Stimmungs-Tag "
        "ist eine Karte mit Gewicht und Modus, also bevorzugen, muss oder ausschließen.",
    ),
    Segment(
        "05_results",
        "Über „Search“ sehe ich alle Treffer zu genau diesen Kriterien, denn Chat und Suche "
        "teilen sich denselben Zustand. Unter „Excluded“ steht Horror, als Tag und als Genre, und CineSense "
        "sagt offen, wie viele Filme dadurch ausgeblendet werden. Es wird also nichts heimlich gefiltert. "
        "Darunter steht der Laufzeitfilter.",
    ),
    Segment(
        "06_edit",
        "Alles, was die KI gesetzt hat, kann ich selbst ändern. Ich gebe dem ersten Tag das volle "
        "Gewicht, und die Ergebnisliste wird sofort neu sortiert.",
    ),
    Segment(
        "07_stage",
        "Ein Klick holt einen Film auf die Bühne: Poster, wenn vorhanden der offizielle Trailer, "
        "Regie und Besetzung, Stimmungs-Tags, Links zu IMDb und Wikipedia, "
        "und wo man den Film in Deutschland streamen kann. "
        "Ist das nicht bekannt, steht dort ehrlich „unbekannt“, statt dass geraten wird. Darunter laufen "
        "weitere passende Filme, die man mit der Maus steuert.",
    ),
    Segment(
        "08_feedback",
        "Mit Daumen hoch oder Daumen runter bringe ich CineSense meinen Geschmack bei. Ich "
        "markiere ein paar Filme, die mir gefallen. „More action“ und „Funnier“ steuern dagegen nur die "
        "aktuelle Sitzung.",
    ),
    Segment(
        "09_profile",
        "Im Profil sehe ich, was CineSense gelernt hat: ein Geschmacksprofil aus Stimmungs-Tags, "
        "berechnet aus meinen Bewertungen. Es fließt als zusätzliches Signal in jede Rangliste ein. Es gibt "
        "kein Konto und keine persönlichen Daten, nur eine zufällige Kennung im Browser. Mit einem Klick ist "
        "alles wieder gelöscht.",
    ),
    Segment(
        "10_outro",
        "Das ist CineSense. Du sagst, wie du dich fühlst, und der Agent macht daraus eine "
        "nachvollziehbare Suche über echte Filmdaten, mit Begründung und unter deiner Kontrolle. Wie das "
        "technisch funktioniert, zeigt das zweite Video.",
    ),
]


async def shot(page, out: Path, name: str) -> None:
    """Screenshot of the cinema screen for the slides of the technical video (tech_demo.py)."""
    (out / "shots").mkdir(parents=True, exist_ok=True)
    clip = {"x": 177, "y": 178, "width": 1566, "height": 722}
    await page.screenshot(path=str(out / "shots" / f"{name}.jpg"), clip=clip, quality=92, type="jpeg")


async def main(base: str, api: str, out: Path) -> None:
    work = out / "work-user"
    await synthesize(SEGMENTS, work / "voice")
    seg = {s.key: s for s in SEGMENTS}

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": W, "height": H}, device_scale_factor=1)
        await ctx.add_init_script(CURSOR_JS)
        page = await ctx.new_page()
        await strip_trailers(page, api)
        await page.goto(base + "/")
        await page.wait_for_timeout(3500)

        rec = Screencast(page, work / "frames")
        await rec.start()

        async def intro():
            await glide(page, 1300, 700, 2500)
            await asyncio.sleep(3)
            await glide(page, 760, 620, 2000)

        await narrate(rec, seg["01_intro"], intro)

        box = page.get_by_label("Message CineSense")

        async def type_query():
            await click(page, box)
            await page.keyboard.type(QUERY, delay=55)
            await glide_to(page, page.get_by_label("Send"), 600)

        await narrate(rec, seg["02_type"], type_query, pad=0.3)

        async def send():
            await click(page, page.get_by_label("Send"), 200)
            await glide(page, 1250, 560, 1500)

        await narrate(rec, seg["03_agent"], send, pad=0.3)
        # The agent turn takes 10–45 s; whatever outlasts the narration is cut from the video.
        await rec.wait_cut(page.locator("[data-testid=chat-pick]").first.wait_for(timeout=120000))
        await page.wait_for_timeout(1500)

        async def reply():
            log = page.locator(".chat-log")
            await glide_to(page, log, 900, dx=0.8)
            for _ in range(6):
                await page.mouse.wheel(0, -120)
                await asyncio.sleep(0.35)
            await asyncio.sleep(1.5)
            for _ in range(8):
                await page.mouse.wheel(0, 120)
                await asyncio.sleep(0.3)
            await shot(page, out, "chat")
            await glide_to(page, page.locator("[aria-label='Search criteria']"), 1400, dy=0.2)
            await glide_to(page, page.locator("[role=group][aria-label^='Mode for']").first, 1000)

        await narrate(rec, seg["04_reply"], reply)

        async def results():
            await click(page, page.get_by_role("link", name="🔍 Search"), 900)
            await page.locator("[data-testid=result-card]").first.wait_for(timeout=30000)
            await glide(page, 1100, 210, 800)
            await asyncio.sleep(1.5)
            excluded = page.locator(".chips-heading", has_text="Excluded")
            if await excluded.count():
                await glide_to(page, excluded, 1200)
                await asyncio.sleep(2.5)
            hidden = page.locator(".chips-hidden")
            if await hidden.count():
                await glide_to(page, hidden, 900)
                await asyncio.sleep(3)
            await shot(page, out, "results")
            filters = page.locator(".chips-heading", has_text="Filters")
            if await filters.count():
                await glide_to(page, filters, 900, dy=2.5)

        await narrate(rec, seg["05_results"], results)

        async def edit():
            await click(page, page.locator("[aria-label^='Weight 5 of 5 for']").first, 900)
            await asyncio.sleep(2.5)
            await glide(page, 1500, 300, 1200)

        await narrate(rec, seg["06_edit"], edit)

        async def stage():
            await click(page, page.locator("[aria-label^='Open ']").first, 900)
            await page.get_by_role("button", name="👍 More like this").wait_for(timeout=30000)
            await page.wait_for_timeout(1200)
            for sel in [".stage-info h2, h1, h2", "text=/streaming|Netflix|unknown|rent/i", "text=Wikipedia"]:
                loc = page.locator(sel).first
                if await loc.count():
                    await glide_to(page, loc, 1100)
                    await asyncio.sleep(1.6)
            row = page.locator("[aria-label='Also fits your mood']")
            await glide_to(page, row, 1000, dx=0.75)
            await asyncio.sleep(1.5)
            await glide_to(page, row, 1800, dx=0.3)

        await narrate(rec, seg["07_stage"], stage)

        async def feedback():
            like = page.get_by_role("button", name="👍 More like this")
            await click(page, like, 900)
            await asyncio.sleep(1.0)
            for n in (1, 2):  # back to the result grid (stable, unlike the drifting row) and like two more
                await page.go_back()
                await page.locator("[aria-label^='Open ']").nth(n).wait_for(timeout=30000)
                await page.wait_for_timeout(600)
                await click(page, page.locator("[aria-label^='Open ']").nth(n), 900)
                await like.wait_for(timeout=30000)
                await page.wait_for_timeout(900)
                await click(page, like, 800)
                await asyncio.sleep(0.8)

        await narrate(rec, seg["08_feedback"], feedback)

        async def profile():
            await click(page, page.get_by_role("link", name="Back to home").first, 900)
            await page.wait_for_timeout(1800)
            await click(page, page.get_by_label("Profile").first, 800)
            await page.wait_for_timeout(1200)
            panel = page.get_by_label("Your profile")
            await glide_to(page, panel, 900, dy=0.25)
            await asyncio.sleep(4)
            await shot(page, out, "profile")
            await glide_to(page, panel, 900, dy=0.55)
            await asyncio.sleep(seg["09_profile"].duration - 11)
            await click(page, page.get_by_role("button", name="Reset profile"), 800)

        await narrate(rec, seg["09_profile"], profile)

        async def outro():
            await asyncio.sleep(1.5)
            close = page.get_by_label("Close profile")
            if await close.count():
                await click(page, close, 700)
            await glide(page, 760, 470, 1800)

        await narrate(rec, seg["10_outro"], outro, pad=1.5)
        await rec.stop(tail=1.0)
        await browser.close()

    render(rec, SEGMENTS, out / "cinesense-bedienung.mp4")
    print("wrote", out / "cinesense-bedienung.mp4", f"{rec.shift(rec.end):.1f}s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:3100")
    ap.add_argument("--api", default="http://localhost:8100")
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "out")
    a = ap.parse_args()
    asyncio.run(main(a.base, a.api, a.out.resolve()))
