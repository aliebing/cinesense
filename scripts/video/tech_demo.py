"""Video 2: how CineSense's AI parts work (German voice-over over animated slides).

Uses the screenshots that user_demo.py saves to out/shots/ and takes one of /tech from the running app. Usage:
    python scripts/video/tech_demo.py [--out scripts/video/out] [--base http://localhost:3100]
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright
from recorder import H, Screencast, Segment, W, narrate, render, synthesize

SEGMENTS = [
    Segment(
        "t01",
        "CineSense unter der Haube. In diesem Video zeige ich, wie die KI-Teile von CineSense "
        "funktionieren: die Daten, die semantische Suche, den LangGraph-Agenten mit seinem Grounding-Check, "
        "die Personalisierung, und wie ich das Ganze evaluiert habe.",
    ),
    Segment(
        "t02",
        "Zuerst das Warum, im Schema Situation, Complication, Resolution. Die Situation: Kino- und "
        "Streamingseiten zeigen lange Titellisten und Genre-Raster. Die Komplikation: Wer mehrere Wünsche "
        "kombinieren will, also eine Stimmung, eine Sprache, kein Horror, nicht zu lang, im Kino oder im Abo, "
        "muss das selbst zusammensuchen. Und ein reiner Chatbot würde Filme oder Streaming-Angebote einfach "
        "erfinden. Die Lösung: Ein Sprachmodell versteht den Wunsch, aber eine deterministische Suche über "
        "echte Daten liefert die Filme.",
    ),
    Segment(
        "t03",
        "Die Architektur hat drei Schichten. Ein Next.js-Frontend in TypeScript spricht mit einem "
        "FastAPI-Backend in Python, dort laufen der Agent, die Suche und das Ranking. Die Daten liegen in "
        "Supabase Postgres mit pgvector, in einem eigenen Schema. Externe Dienste wie OpenRouter für Sprachmodelle "
        "und Embeddings, die Streaming-API und YouTube stecken hinter Adaptern. Dadurch laufen alle Tests "
        "offline auf Fixtures. Jeder Agent-Lauf wird in LangSmith getraced.",
    ),
    Segment(
        "t04",
        "Die Daten: rund zwanzigtausendsechshundert Filme. Etwa neunzehntausendachthundert kommen aus "
        "MovieLens, mit Bewertungen und dem Tag Genome. Das sind für jeden Film elfhundertachtundzwanzig "
        "Relevanzwerte, zum Beispiel wie düster ein Film ist, wie stark sein Twist oder wie viel Raumfahrt "
        "er enthält. Dazu kommen rund achthundert deutsche Kinostarts seit 2021. Wikidata liefert IDs, "
        "Personen, Laufzeit, Sprache und Trailer, Wikipedia die Handlungstexte. TMDB nutze ich bewusst "
        "nicht, denn seine Nutzungsbedingungen verbieten den Einsatz in KI-Anwendungen.",
    ),
    Segment(
        "t05",
        "Gesucht wird auf vier Wegen. Erstens semantisch, als Retrieval Augmented Generation: Die "
        "Wikipedia-Handlungen sind in Abschnitte zerlegt, über OpenRouter eingebettet und als Vektoren mit "
        "fünfzehnhundertsechsunddreißig Dimensionen und HNSW-Index in pgvector gespeichert. So findet eine "
        "beschriebene Handlung passende Filme, auch ohne Titel. Zweitens über gewichtete Stimmungs-Tags aus "
        "dem Tag Genome. Drittens tippfehler- und klangtolerant nach Titeln und Personen. Und viertens über "
        "eine erweiterte Live-Suche für neuere Filme.",
    ),
    Segment(
        "t06",
        "Das Herz ist ein LangGraph-Agent. Er bekommt die Nachricht zusammen mit den aktuellen Chips. "
        "Im Knoten Agent entscheidet das Sprachmodell, standardmäßig Claude Haiku 5.5 über OpenRouter, "
        "welche Tools es aufruft, in höchstens sechs Runden. Hat sich an den Kriterien etwas geändert, führt "
        "der Knoten Present die deterministische Suche aus. Danach formuliert Explain die Antwort, diesmal "
        "ohne Tools, und der Grounding-Check prüft sie. Bei einer Rückfrage geht die Antwort direkt zurück. "
        "Der Fortschritt wird per Server-Sent Events ins Frontend gestreamt.",
    ),
    Segment(
        "t07",
        "Die Arbeitsteilung ist klar geregelt: Das Modell entscheidet, wonach gesucht wird. Es setzt "
        "Stimmungs-Tags mit Gewicht und Modus, Filter wie Laufzeit oder Sprache, durchsucht Handlungen, findet "
        "Personen oder ähnliche Filme und prüft Streaming und Fakten. Vage Abneigungen schlägt es nur als "
        "Ausschluss vor, angewendet wird nichts heimlich. Alles, was reproduzierbar sein muss, ist "
        "deterministischer Code: das Ranking, die harten Filter und die Zählung ausgeblendeter Filme, die "
        "finale Suche, die API-Budgets und der Grounding-Check.",
    ),
    Segment(
        "t08",
        "Der Grounding-Check ist die wichtigste Schutzschicht gegen Halluzinationen. Das Modell schreibt "
        "die Empfehlungsliste nie selbst. Seine Erklärung darf nur Filme nennen, die die Suche zurückgegeben "
        "hat oder die der Nutzer selbst genannt hat. Und sie darf nur dann sagen, dass ein Film streambar ist, "
        "wenn die Daten das bestätigen. Nennt sie zum Beispiel einen unbekannten Titel oder bricht mitten im "
        "Satz ab, wird sie durch eine Template-Antwort aus den echten Daten ersetzt.",
    ),
    Segment(
        "t09",
        "Das Ranking kombiniert gewichtete Tag-Relevanz, die Ähnlichkeit der Handlung, Personen und "
        "eine Bayes'sche Bewertung, die wenig bewertete Filme dämpft. Schwach gewichtet zählen außerdem die "
        "Bekanntheit, gemessen an der Zahl der Bewertungen, und ein kleiner Bonus für neuere Filme. "
        "Als weiteres Signal kommt der Geschmack "
        "dazu. Aus den Filmen mit Daumen hoch bildet CineSense den mittleren Tag-Genome-Vektor, minus den "
        "Katalog-Durchschnitt. Abgelehnte Filme zählen dagegen. Übrig bleiben die acht stärksten Tags. Das "
        "Signal hat nur das Gewicht 0,15, damit Stimmung, Handlung und Personen führend bleiben.",
    ),
    Segment(
        "t10",
        "Evaluiert habe ich mit 36 Szenarien gegen den echten Agenten und den echten Katalog: "
        "Stimmungen, ähnliche Filme, Laufzeit, Ausschlüsse, Personen, Handlung, widersprüchliche Wünsche, "
        "Folgefragen und zwei eingeschleuste Ausfälle. Alle 36 bestehen. Die Constraints sind in 19 von 19 "
        "Fällen erfüllt, das passende Tool wurde in 35 von 35 Fällen gewählt. Besonders aufschlussreich ist "
        "das Grounding. Vor dem Guard nannte das Modell allein in 86 Prozent der Fälle nur echte Treffer. "
        "Nach dem Guard sind es 100 Prozent. Fünf Mal hat die Template-Antwort gegriffen.",
    ),
    Segment(
        "t11",
        "Für den Ranking-Vergleich bewertet ein LLM-Judge, Claude Sonnet 5.5, die Top-Ergebnisse von "
        "drei Verfahren. Nur nach Bewertung sortiert: 1,52 von 5. Die Kosinus-Methode aus movieFinder: 3,67. "
        "CineSense: 4,05. Ein Chat-Turn kostet rund ein Zehntel Cent, die Median-Latenz liegt bei siebeneinhalb "
        "Sekunden, und die komplette Evaluation hat etwa 22 Cent gekostet.",
    ),
    Segment(
        "t11t",
        "Für die Prüfung gibt es eine eigene, schlichte Seite: slash tech. Sie zeigt einen Agent-Turn ohne "
        "Bilder und Animationen. Links stehen die gesetzten Stimmungs-Tags mit Gewicht und Modus, jeder "
        "Tool-Aufruf mit seinen Argumenten und der Rückgabe an das Modell, die tatsächlich gesendeten Prompts "
        "sowie Modell, Tokens, Kosten und Latenz. Rechts steht die Rangliste als Text, mit Score, Begründung "
        "und Daten jedes Films. Die Vorschläge der Antwort sind markiert.",
    ),
    Segment(
        "t12",
        "Zur Ethik: Es gibt kein Konto und keine persönlichen Daten, nur eine zufällige ID im Browser, "
        "und das Profil ist mit einem Klick gelöscht. Jede Entscheidung der KI ist als Chip sichtbar und "
        "änderbar, und ausgeblendete Filme werden gezählt. CineSense nutzt nur lizenzierte offene Daten und "
        "offizielle APIs und nennt alle Quellen. Und die Grenzen sind benannt: Das Tag Genome deckt vor allem "
        "ältere, englischsprachige Filme ab, und die Bayes'sche Bewertung bevorzugt bekannte Titel.",
    ),
    Segment(
        "t13",
        "Die größten Herausforderungen waren Halluzinationen, gelöst durch die Trennung von Suche und "
        "Erklärung plus Grounding-Check. Dann knappe API-Budgets, gelöst mit Cache und Budget-Wächter. Und "
        "Fehler in den eigenen Prüfungen, die erst die ersten Evaluationsläufe aufgedeckt haben. Mit mehr Zeit "
        "kämen Stimmungs-Tags auch für neue Filme, Seiten für Schauspieler und Regie, ein Modus, um gemeinsam "
        "einen Film zu finden, und lokale Kino-Spielzeiten. Danke fürs Zuschauen.",
    ),
]


async def tech_shot(browser, base: str, out: Path) -> None:
    """Screenshot of the technical view after one real agent turn (about $0.001), for slide t11t."""
    page = await browser.new_page(viewport={"width": 1600, "height": 900})
    await page.goto(f"{base}/tech")
    await page.get_by_label("Message").fill("something funny or action, Marvel welcome, no horror")
    await page.get_by_role("button", name="send").click()
    await page.wait_for_selector(".is-pick", timeout=60_000)
    (out / "shots").mkdir(parents=True, exist_ok=True)
    await page.screenshot(path=str(out / "shots" / "tech.jpg"), quality=92, type="jpeg")
    await page.close()


async def main(out: Path, base: str) -> None:
    work = out / "work-tech"
    await synthesize(SEGMENTS, work / "voice")
    slides = (Path(__file__).parent / "slides.html").resolve()
    for s in SEGMENTS:
        print(f"{s.key}: {s.duration:5.1f}s")

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        await tech_shot(browser, base, out)
        page = await browser.new_page(viewport={"width": W, "height": H})
        await page.goto(slides.as_uri())
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1500)
        rec = Screencast(page, work / "frames")
        await page.evaluate("go('none')")
        await rec.start()
        for s in SEGMENTS:
            await page.evaluate(f"go('{s.key}')")
            await narrate(rec, s, pad=1.2)
        await rec.stop(tail=1.5)
        await browser.close()

    render(rec, SEGMENTS, out / "cinesense-technik.mp4")
    print("wrote", out / "cinesense-technik.mp4", f"{rec.shift(rec.end):.1f}s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "out")
    ap.add_argument("--base", default="http://localhost:3100", help="running web app, for the /tech screenshot")
    args = ap.parse_args()
    asyncio.run(main(args.out.resolve(), args.base))
