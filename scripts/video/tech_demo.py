"""Video 2: how CineSense's AI parts work (German voice-over over animated slides).

Uses the screenshots that user_demo.py saves to out/shots/ and takes its own of /tech and of a widened search
from the running app. Usage:
    python scripts/video/tech_demo.py [--out scripts/video/out] [--base http://localhost:3100]
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from code_snippets import Snippet, render_slides
from playwright.async_api import async_playwright
from recorder import H, Screencast, Segment, W, narrate, render, synthesize

SEGMENTS = [
    Segment(
        "t01",
        "CineSense unter der Haube. In diesem Video zeige ich, wie die KI-Teile von CineSense "
        "funktionieren: die Daten, die semantische Suche, den LangGraph-Agenten mit seinem Grounding-Check, "
        "die Personalisierung und wie ich das Ganze evaluiert habe. Am Ende zeige ich, was neu dazugekommen ist: "
        "Die Suche lockert sich selbst, wenn zu wenige Filme passen.",
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
        "eine Live-Suche für Filme, die nicht im Katalog stehen, etwa neuere Filme oder Winnetou, der keine "
        "Tag-Genome-Daten hat. Was sie findet, wird nachträglich in den Katalog übernommen.",
    ),
    Segment(
        "c05",
        "Hier die Plot-Suche im Code. Die Frage wird eingebettet, dann sucht Postgres mit dem Operator für den "
        "Kosinus-Abstand über den HNSW-Index die nächsten Handlungsabschnitte. Den Suchumfang ef_search habe "
        "ich von vierzig auf vierhundert erhöht, sonst bleiben zu wenige Filme übrig. Pro Film zählt nur der "
        "beste Abschnitt, und genau der wird später als Begründung angezeigt. Neu ist der Zweig oben: Steht der "
        "Filter auf Im Kino, rechnet Postgres die Ähnlichkeit nur für die Kinofilme aus. Unter den besten "
        "hundertfünfzig des ganzen Katalogs wären sie sonst kaum dabei.",
    ),
    Segment(
        "t06",
        "Das Herz ist ein LangGraph-Agent. Er bekommt die Nachricht zusammen mit den aktuellen Chips. "
        "Im Knoten Agent entscheidet das Sprachmodell, standardmäßig Claude Haiku 5.5 über OpenRouter, "
        "welche Tools es aufruft, in höchstens sechs Runden. Hat sich an den Kriterien etwas geändert, führt "
        "der Knoten Present die deterministische Suche aus. Neu ist der Knoten Verify: Findet die Suche weniger "
        "als drei Filme, zählt er, was eine Lockerung bringen würde, und gibt die Optionen an das Modell zurück. "
        "Dazu später mehr. Danach formuliert Explain die Antwort, diesmal "
        "ohne Tools, und der Grounding-Check prüft sie. Bei einer Rückfrage geht die Antwort direkt zurück. "
        "Der Fortschritt wird per Server-Sent Events ins Frontend gestreamt.",
    ),
    Segment(
        "c06",
        "So sieht der Graph im Code aus. Sieben Knoten: agent, tick als Rundenzähler, tools, present, verify, "
        "auto_relax und explain. Nach dem Agenten entscheidet eine Routing-Funktion: weitere Tools, die Suche, "
        "oder bei einer Rückfrage direkt das Ende. Nach verify geht es zur Erklärung, oder mit "
        "Lockerungs-Optionen zurück zum Agenten. Wählt das Modell keine, nimmt auto_relax die schonendste. "
        "Der Checkpointer speichert den Gesprächsverlauf pro Thread, deshalb "
        "versteht der Agent auch Folgefragen.",
    ),
    Segment(
        "t07",
        "Die Arbeitsteilung ist klar geregelt: Das Modell entscheidet, wonach gesucht wird. Es setzt "
        "Stimmungs-Tags mit Gewicht und Modus, Filter wie Laufzeit oder Sprache, durchsucht Handlungen, sucht "
        "Filme beim Namen, findet Personen oder ähnliche Filme, prüft Streaming und Fakten und wählt bei zu "
        "wenigen Treffern eine Lockerung. Vage "
        "Abneigungen schlägt es nur als Ausschluss vor, angewendet wird nichts heimlich. Alles, was "
        "reproduzierbar sein muss, ist "
        "deterministischer Code: das Ranking, die harten Filter und die Zählung ausgeblendeter Filme, die "
        "finale Suche, die gezählten Lockerungs-Optionen, die API-Budgets und der Grounding-Check.",
    ),
    Segment(
        "c07",
        "Ein Tool ist schlicht Python. find_title zum Beispiel lässt die echte Suche laufen. Findet der Katalog"
        " keinen guten Treffer, sucht sie live weiter. Erst danach wird der Titel als Kriterium gesetzt. Zurück"
        " ans Modell geht nur eine kurze Textzusammenfassung. Der Docstring unten ist genau die Beschreibung, "
        "nach der das Modell entscheidet, wann es dieses Tool benutzt.",
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
        "c08",
        "Und so prüft der Grounding-Check. Erlaubt sind die Titel aus den Suchergebnissen und Titel, die der "
        "Nutzer selbst genannt hat. Jeder hervorgehobene Name in der Antwort, der wie ein Filmtitel aussieht "
        "oder im Katalog steht, aber nicht erlaubt ist, landet in der Liste bad. Ist sie nicht leer, oder ist "
        "die Antwort leer oder abgeschnitten, ersetzt eine Template-Antwort aus den echten Daten den Text des "
        "Modells.",
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
        "c09",
        "Das Ranking im Code: Jedes aktive Signal wird auf null bis eins normiert und mit seinem Gewicht "
        "multipliziert, dazu kommen Bayes-Rating, Bekanntheit und Neuheit. Geteilt durch die Summe der aktiven "
        "Gewichte ergibt das den Match-Prozentwert. Darunter das Geschmacksprofil: Durchschnitt der gemochten "
        "Filme minus Katalog-Durchschnitt, abgelehnte Filme ziehen ab, und die acht stärksten Tags bleiben.",
    ),
    Segment(
        "n01",
        "Und jetzt das Neue: Die Suche lockert sich selbst. Bisher endete ein zu enger Wunsch einfach mit "
        "einer leeren Liste. Ein Beispiel: gruselig als Stimmung, kein Horror, und nur Filme, die gerade im "
        "Kino laufen. Das ergibt null Treffer, denn die aktuellen Kinofilme haben noch keine "
        "Tag-Genome-Daten. Jetzt zählt CineSense für jeden Wunsch, der sich lockern ließe, wie viele Filme "
        "dann passen würden, ohne Live-Import und ohne Streaming-Abfragen. Angeboten wird nur, was mehr "
        "findet: die Stimmung in den Handlungstexten suchen, oder nicht nur im Kino. Ausschlüsse wie kein "
        "Horror werden nie gelockert. Auf der Ergebnisseite wählt man per Klick, im Chat wählt das Modell "
        "die Option, die den Wunsch am wenigsten verändert.",
    ),
    Segment(
        "n02",
        "Wichtig war mir dabei Transparenz. Über der Liste steht, was gelockert wurde. Und jeder Film zeigt "
        "mit einem Ungleich-Zeichen, welchen Teil des Wunsches er verfehlt, hier: keine Stimmungsdaten für "
        "creepy. Andere Hinweise lauten etwa: länger als gewünscht, oder: nicht im Kino. Im Chat beginnt die "
        "Antwort mit: Nichts passte zu allen Wünschen, deshalb habe ich die Suche erweitert. Neu ist außerdem "
        "eine Regel für Wünsche wie: so wie dieser Film, aber weniger düster. Das Modell übernimmt die "
        "Stimmungen des Films ohne die eine, die stören soll.",
    ),
    Segment(
        "c10",
        "Im Code: Der Knoten verify prüft nach jeder Suche, ob mindestens drei Filme da sind. Wenn nicht, "
        "probiert probe jede mögliche Lockerung mit einer reinen Zählung. Übrig bleiben nur Optionen, die "
        "mehr Filme finden als jetzt. Höchstens zwei Runden pro Nachricht, damit der Agent nicht endlos "
        "weitersucht.",
    ),
    Segment(
        "t10",
        "Evaluiert habe ich mit 48 Szenarien gegen den echten Agenten und den echten Katalog: "
        "Stimmungen, ähnliche Filme, Laufzeit, Ausschlüsse, Personen, Handlung, widersprüchliche Wünsche, "
        "Folgefragen, zwei eingeschleuste Ausfälle und, neu, zwölf Szenarien zur Lockerung und zu Wünschen "
        "wie: so wie dieser Film, aber weniger düster. 47 bestehen. Die Constraints sind in 24 von 24 Fällen "
        "erfüllt, das passende Tool wurde in 40 von 41 Fällen gewählt. Der eine Fehler: Bei der mehrdeutigen "
        "Anfrage Solaris ruft das Modell die Titelsuche auf statt eines der erwarteten Tools. Gelockert wurde "
        "in vier von vier Fällen genau dann, wenn es nötig war. Besonders aufschlussreich ist das Grounding. "
        "Vor dem Guard nannte das Modell allein in 90 Prozent der Fälle nur echte Treffer. Nach dem Guard "
        "sind es 100 Prozent. Fünf Mal hat die Template-Antwort gegriffen.",
    ),
    Segment(
        "t11",
        "Für den Ranking-Vergleich bewertet ein LLM-Judge, Claude Sonnet 5.5, die Top-Ergebnisse von "
        "drei Verfahren in 21 Stimmungs-Szenarien. Nur nach Bewertung sortiert: 1,29 von 5. Die Kosinus-Methode "
        "aus movieFinder: 3,48. CineSense: 3,76. Die Werte schwanken von Lauf zu Lauf, die Reihenfolge blieb "
        "bisher gleich. Ein Chat-Turn kostet rund 0,14 Cent, die Median-Latenz liegt bei gut siebeneinhalb "
        "Sekunden, und die komplette Evaluation hat etwa 27 Cent gekostet.",
    ),
    Segment(
        "t11t",
        "Für die Prüfung gibt es eine eigene, schlichte Seite: slash tech. Sie zeigt einen Agent-Turn ohne "
        "Bilder und Animationen. Links stehen die gesetzten Stimmungs-Tags mit Gewicht und Modus, jeder "
        "Tool-Aufruf mit seinen Argumenten und der Rückgabe an das Modell, die tatsächlich gesendeten Prompts "
        "sowie Modell, Tokens, Kosten und Latenz. Rechts stehen die gefundenen Filme als einfache Liste: der "
        "Titel als Link zur IMDb-Seite, eine kurze Inhaltsangabe, und Score, Begründung und Daten zum "
        "Aufklappen. Die Vorschläge der Antwort sind golden markiert.",
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


CODE = {  # code slide -> its panels, read from the repository at recording time
    "c05": [Snippet("src/cinesense/providers/postgres.py", "PostgresProvider.semantic_search",
                    mark=["only_ids is not None", "ef_search", "best[film_id]"])],
    "c06": [Snippet("src/cinesense/agent/graph.py", start="g = StateGraph(AgentState)", end="return g.compile",
                    mark=["add_conditional_edges", "verify", "checkpointer"])],
    "c07": [Snippet("src/cinesense/agent/tools.py", "ToolKit.find_title", mark=["self.service.run", "model_copy"]),
            Snippet("src/cinesense/agent/tools.py", "make_tools.find_title", mark=["@tool", '"""'])],
    "c08": [Snippet("src/cinesense/agent/graph.py", start='allowed = [r["movie"]["title"]', end="grounding_fallback",
                    mark=["validate_titles", "template_answer", "grounding_fallback"]),
            Snippet("src/cinesense/agent/grounding.py", start="    bad: list[str] = []", end="return not bad, bad",
                    mark=["bad.append"])],
    "c10": [Snippet("src/cinesense/agent/graph.py", "build_graph.verify",
                    mark=["MIN_RESULTS", "relax.probe", "relax_rounds\": rounds + 1"]),
            Snippet("src/cinesense/search/relax.py", "probe", mark=["service.count", "opt.count > current"])],
    "c09": [Snippet("src/cinesense/recommend/combined.py", start="    ranked = []", end="ranked.sort(",
                    mark=["WEIGHTS[k] * v", "score = "]),
            Snippet("src/cinesense/personal/profile.py", start="like_vec = avg(liked)", end="taste = {",
                    mark=["lift = like_vec - mean", "lift -=", "TASTE_TAGS"])],
}  # fmt: skip


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


# the widening example: creepy as a mood, no horror, only films in cinemas (in cinema films have no Tag Genome data)
RELAX_CRITERIA = {
    "tags": [{"idx": 266, "weight": 5, "mode": "prefer"}, {"idx": 521, "weight": 5, "mode": "not"}],
    "exclude_genres": ["Horror"],
    "availability": "cinema",
}


async def relax_shots(browser, base: str, out: Path) -> None:
    """Screenshots of a search that finds nothing (with its widening offer) and of the widened result, for n01/n02."""
    page = await browser.new_page(viewport={"width": 1600, "height": 900})
    await page.goto(f"{base}/")
    # the app fills every criterion left out here with its default
    await page.evaluate("c => sessionStorage.setItem('cinesense.search', JSON.stringify(c))", RELAX_CRITERIA)
    await page.goto(f"{base}/results")
    await page.wait_for_selector("text=Nothing matches every wish", timeout=30_000)
    await page.wait_for_timeout(800)
    (out / "shots").mkdir(parents=True, exist_ok=True)
    clip = {"x": 150, "y": 150, "width": 1300, "height": 500}
    await page.screenshot(path=str(out / "shots" / "relax-offer.jpg"), quality=92, type="jpeg", clip=clip)
    await page.locator("button:has-text('in plot descriptions')").first.click()
    await page.wait_for_selector(".result-miss", timeout=30_000)
    await page.wait_for_timeout(1500)
    clip = {**clip, "height": 580}
    await page.screenshot(path=str(out / "shots" / "relax-widened.jpg"), quality=92, type="jpeg", clip=clip)
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
        await relax_shots(browser, base, out)
        page = await browser.new_page(viewport={"width": W, "height": H})
        await page.goto(slides.as_uri())
        await page.wait_for_load_state("networkidle")
        await page.evaluate("fillCode", render_slides(CODE))
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
