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
        "Nebel und zwei Scheinwerfern. Im Hintergrund wechseln sechs Stimmungswelten, zum Beispiel Spannung, "
        "Komödie oder Liebe, und rechts laufen Filmreihen dieser Welten vorbei. Jede Kachel lässt sich anklicken.",
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
        "Die Antwort kommt mit den drei besten Vorschlägen, jeder mit einer kurzen Begründung. Gleichzeitig "
        "passen sich rechts die Filmreihen an: In der Mitte stehen jetzt, größer und mit goldenem Rand, die "
        "Treffer meiner Suche, also die engere Wahl. Darüber und darunter laufen weitere passende Filme aus den "
        "Genres dieser Treffer, mit denselben Kriterien. Links siehst du, was der Agent "
        "eingestellt hat: Jeder Stimmungs-Tag ist eine Karte mit Gewicht und Modus, also bevorzugen, muss "
        "oder ausschließen.",
    ),
    Segment(
        "05_best",
        "Mit „Show results“ springt CineSense direkt zum besten Treffer. Die Rangfolge berücksichtigt alle "
        "Kriterien: wie gut der Film zur Suche passt, seine Bewertung, wie bekannt er ist und, etwas schwächer, "
        "wie neu er ist. Auf der Bühne stehen Poster, wenn vorhanden der offizielle Trailer, Regie, Besetzung "
        "und eine kurze Inhaltsangabe aus Wikipedia. Darunter steht, wo man den Film in Deutschland streamen, "
        "leihen oder kaufen kann, mit direktem Link zum Anbieter. Ist das nicht bekannt, steht dort ehrlich "
        "„unbekannt“, statt dass geraten wird. Unten laufen meine übrigen Treffer durch, jeder mit Begründung. "
        "Mit der Maus am rechten oder linken Rand werden sie schneller.",
    ),
    Segment(
        "06_results",
        "Über „Search“ sehe ich alle Treffer als Übersicht, denn Chat und Suche teilen sich denselben "
        "Zustand. Unter „Excluded“ steht Horror, als Tag und als Genre, und CineSense sagt offen, wie viele "
        "Filme dadurch ausgeblendet werden. Es wird also nichts heimlich gefiltert. Darunter steht der "
        "Laufzeitfilter, und unten laufen alle Treffer durch.",
    ),
    Segment(
        "07_edit",
        "Alles, was die KI gesetzt hat, kann ich selbst ändern. Ich gebe dem ersten Tag das volle "
        "Gewicht, und die Trefferreihe wird sofort neu sortiert.",
    ),
    Segment(
        "08_feedback",
        "Mit Daumen hoch oder Daumen runter bringe ich CineSense meinen Geschmack bei. Ein Klick auf eine "
        "Karte holt den Film auf die Bühne, und ich markiere ein paar Filme, die mir gefallen. „More action“ "
        "und „Funnier“ steuern dagegen nur die aktuelle Sitzung.",
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


RESULT_CARDS = "[aria-label='Results'] .related-card"

CARD_AT_JS = """
([sel, slot]) => {
  const cards = [...document.querySelectorAll(sel)].map((c) => c.getBoundingClientRect()).filter((r) => r.width > 0);
  const row = document.querySelector("[aria-label='Results'] .related-viewport").getBoundingClientRect();
  const x = row.left + row.width * slot;
  const best = cards.filter((r) => r.left > row.left && r.right < row.right)
    .sort((a, b) => Math.abs(a.left + a.width / 2 - x) - Math.abs(b.left + b.width / 2 - x))[0];
  return best ? { x: best.left + best.width / 2, y: best.top + best.height * 0.4 } : null;
}
"""


async def click_card(page, selector: str, slot: float) -> None:
    """The result row keeps creeping, so aim at the card nearest to `slot` (share of the row's width, kept inside
    the row's slow middle) and click it with the pointer right there."""
    pos = await page.evaluate(CARD_AT_JS, [selector, slot])
    if pos is None:
        return
    await glide(page, pos["x"], pos["y"], 800)
    await page.mouse.down()
    await page.mouse.up()


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
            hits = page.locator(".tile-row-wrap--picked")
            await hits.wait_for(timeout=30000)
            await glide_to(page, hits, 1200, dx=0.6)
            await asyncio.sleep(1.5)
            await glide(page, 1500, 820, 1500)  # over the other candidates below
            await asyncio.sleep(1.0)
            await shot(page, out, "chat")
            await glide_to(page, page.locator("[aria-label='Search criteria']"), 1400, dy=0.2)
            await glide_to(page, page.locator("[role=group][aria-label^='Mode for']").first, 1000)

        await narrate(rec, seg["04_reply"], reply)

        async def best():
            await click(page, page.get_by_role("button", name="Show results →"), 1000)
            await page.get_by_role("button", name="👍 More like this").wait_for(timeout=30000)
            await page.wait_for_timeout(1500)
            await shot(page, out, "stage")
            for sel, pause in [(".stage-info h2", 2.0), (".stage-people", 1.6), (".stage-overview", 3.5),
                               (".stage-tags", 3.0), (".stage-why", 2.0)]:  # fmt: skip
                loc = page.locator(sel).first
                if await loc.count():
                    await glide_to(page, loc, 1000, dx=0.3)
                    await asyncio.sleep(pause)
            row = page.locator("[aria-label='Your other matches']")
            await glide_to(page, row, 1000, dx=0.5, dy=0.6)
            await asyncio.sleep(2.0)
            await glide_to(page, row, 1200, dx=0.96, dy=0.6)  # right edge: runs fast
            await asyncio.sleep(1.8)
            await glide_to(page, row, 1600, dx=0.04, dy=0.6)  # left edge: fast the other way
            await asyncio.sleep(1.5)

        await narrate(rec, seg["05_best"], best)

        async def results():
            await click(page, page.get_by_role("link", name="Back to home").first, 900)
            await page.wait_for_timeout(1200)
            await click(page, page.get_by_role("link", name="🔍 Search"), 900)
            await page.locator(RESULT_CARDS).first.wait_for(timeout=30000)
            await glide(page, 1100, 210, 800)
            await asyncio.sleep(1.0)
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
            await glide_to(page, page.locator("[aria-label='Results']"), 1200, dx=0.5, dy=0.6)

        await narrate(rec, seg["06_results"], results)

        async def edit():
            await click(page, page.locator("[aria-label^='Weight 5 of 5 for']").first, 900)
            await asyncio.sleep(2.5)
            await glide(page, 1500, 300, 1200)

        await narrate(rec, seg["07_edit"], edit)

        async def feedback():
            like = page.get_by_role("button", name="👍 More like this")
            for slot in (0.3, 0.5, 0.7):  # open three films from the result row and like each
                await page.locator(RESULT_CARDS).first.wait_for(timeout=30000)
                await page.wait_for_timeout(800)
                await click_card(page, RESULT_CARDS, slot)
                await like.wait_for(timeout=30000)
                await page.wait_for_timeout(900)
                await click(page, like, 800)
                await asyncio.sleep(0.8)
                if slot != 0.7:
                    await page.go_back()  # the result row restarts in place

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
