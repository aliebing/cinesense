# Demo videos

Two narrated videos for the capstone review, both with a German synthetic voice (edge-tts, `de-DE-FlorianMultilingualNeural`):

- `user_demo.py` records **how a user works with CineSense**. It is a real screen recording of the running app: chat → criteria chips → search → stage → 👍/👎 → taste profile. It writes `out/cinesense-bedienung.mp4`.
- `tech_demo.py` explains **the AI parts** on animated slides (`slides.html`): data, RAG, the LangGraph agent, grounding, personalisation, evaluation, the technical view `/tech`, ethics. After the slides on retrieval, the agent, its tools, grounding and ranking come **code slides**: real excerpts that `code_snippets.py` reads from the repository at recording time (by function name or first/last line, highlighted with Pygments, key lines marked), so the video always shows the current code. It writes `out/cinesense-technik.mp4`. It uses screenshots that `user_demo.py` saves to `out/shots/`, so run that first, and it screenshots `/tech` after one real agent turn of its own.

`out/` is git-ignored.

## Run

```bash
python -m venv /tmp/vtools && /tmp/vtools/bin/pip install edge-tts playwright mutagen imageio-ffmpeg pygments
/tmp/vtools/bin/playwright install chromium

# app on 3100/8100 (see CLAUDE.md); a production build avoids the Next.js dev badge.
# The Docker stack works too: --base http://localhost:8080 (and --api http://localhost:8080 for user_demo.py)
uv run uvicorn cinesense.api.app:create_app --factory --port 8100
cd web && NEXT_PUBLIC_API_URL=http://localhost:8100 npx next build && npx next start --port 3100

/tmp/vtools/bin/python scripts/video/user_demo.py   # ~4 min, one real agent turn
/tmp/vtools/bin/python scripts/video/tech_demo.py   # ~9 min
```

Narration is cached per segment in `out/work-*/voice/`, so only changed text is synthesised again. Every user-demo run makes one real chat turn (about $0.001), and the 👍 it gives are deleted again with "Reset profile".

## Notes

- **Trailers:** headless Chrome can't play YouTube embeds. The recorder therefore removes trailer ids from API answers, swallows `/api/trailers/report` and hides the "blocked" note. Without the swallowed reports, a test run would mark working trailers as broken in the shared cache.
- **Agent wait:** any part of the agent turn that outlasts the narration is cut from the video (`Screencast.wait_cut`).
- **Frames:** recorded with the Chrome DevTools screencast (sharp JPEGs with timestamps) and encoded to 30 fps H.264 with ffmpeg. A drawn dot stands in for the mouse pointer, because screencasts don't show the real one.
