# Local studio — no publishing

The deck contains 54 curated exercises across nine categories, plus an optional saved queue of API-generated exercises. The API is never called by the browser or a device refresh.

## Start

From `design-drill-deck`:

```powershell
npm install
python -m pip install -r requirements-dev.txt
python scripts/build_layouts.py
python scripts/generate_daily.py
python scripts/serve.py --port 4173
```

Open http://127.0.0.1:4173/preview/. The server binds only to loopback and serves an allowlist of public assets. It never serves `.env`, `.runtime`, or Git files.

Use the category, prompt, practice-level, source, and device selectors. **Actual pixels · 100%** enables native-size inspection; scroll for large X screens. **Read full brief** opens the complete exercise. The compact card intentionally omits the old dense checklist.

Examples:

- `/preview/?prompt=ddd-012` — illustrated recovery challenge.
- `/preview/?prompt=ddd-043` — Everyday UX, Poster variant.
- `/preview/?prompt=ddd-049` — Dark Patterns, informed choice.
- `/preview/?prompt=ddd-012&device=x-portrait` — TRMNL X portrait.
- `/preview/?source=mock` — nine clearly labeled mock API responses; no spending.
- `/preview/?empty=1` — empty-feed handling.

The preview has local copies of the framework, font, and Liquid runtime. If the local feed service fails, it uses `data/daily.json`. With the preview already running, generation-provider outages do not affect rendering.

## Mock and live generation

```powershell
python scripts/generate_prompts.py --mock
```

The mock command exercises content validation, duplicate checks, actual browser layout checks, and persistence to `.runtime/mock-state.json`. The UI's demo source is isolated from real rotation and uses the checked fixture.

For a real test, copy `.env.example` to `.env` and set `OPENAI_API_KEY`, or set that environment variable. Then explicitly run:

```powershell
python scripts/generate_prompts.py --live
```

No key means no request. Live mode uses `gpt-5-mini`, strict structured output, and one candidate per category. The key is never written to the feed or logs. Do not put it in settings.yml or daily.json.

Each ISO week allows two requests, with at most ten per calendar month. Requests are reserved on disk before sending; a timeout still counts because it may have been billed. Each request uses a conservative input byte ceiling below 8,000 tokens, including its schema/envelope, and a 12,000 output-token limit. No image generation, web tools, or extra model-based review runs. Limits apply to this local state file, not to unrelated usage on your API account. Retain `.runtime/state.json` to retain usage history.

Missing keys, timeouts, rate limits, invalid responses, or failed rendering leave saved cards usable. A partial batch saves only accepted candidates. A completed same-week batch is not generated again. Authentication and model access must be configured in the provider account; live API behavior has not been verified without a key.

## Selection and storage

`data/prompts.json` is the reviewed offline source. Existing IDs and full-brief fields are preserved. Each prompt also has `display_title`, `display_brief`, `compact_brief`, `visual_key`, `provenance`, and optionally `render_layout: poster`.

`JsonStateStore` implements the storage interface with atomic writes and an exclusive operation lock. Runtime state contains generated cards, weekly batch IDs, request/usage counters, and per-category/order/level queues and date selections. A future remote implementation can replace storage without changing card validation or selection.

Fresh unshown generated cards are chosen first for each eligible category, then curated cards are consumed without repeating within a cycle. Smart shuffle and sequential order remain separate. Same-day selections stay fixed even if a new batch arrives. The Offline source has separate queues, so inspecting it does not consume the generated queue. Runtime state is local to this machine; it is not device history or a multi-user account service.

If a process is forcibly terminated, a `.runtime/*.lock` may remain. Only remove that exact lock after confirming no generation or preview operation is running; keep the JSON state and usage counters. Corrupt state is not overwritten automatically.

## Design source and tests

The matching editable designs are on [02 · Local implementation in Figma](https://www.figma.com/design/GdHCyZDIvAsd1p17ICo5ha?node-id=11-14), including the new categories, three mashups, and both X orientations. The kitchen wording is updated only in the concept gallery. Browser rendering remains the authority for exact text wrapping.

Edit `src/card.css`, `src/selection.liquid`, and `assets/visuals.json`, then run `python scripts/build_layouts.py`. This assembles `shared.liquid` and the four views. Shared is prepended to each view, matching TRMNL's documented renderer. There are no inline style attributes in the device layouts.

TRMNL X uses a logical 1040 × 780 canvas at a 1.8 scale. X typography is specified in logical pixels, not physical panel pixels. Preview images should be judged at native size and on hardware.

```powershell
python -m unittest discover -s tests -v
python scripts/validate_project.py
npm run test:layout
```

The browser gate checks every curated card at six device configurations, empty states, unknown visuals, and Poster fallback. Screenshots are saved under ignored `qa/`. Windows uses installed Edge; other platforms need `npx playwright install chromium`. Set `DDD_BROWSER` to an executable path if needed; `DDD_NODE` can select Node for Python's render gate.

Local review on 2026-09-08: 29 unit tests passed; project/schema validation passed; all 324 curated prompt/device combinations passed the browser fit gate. The nine-card mock batch passed validation and browser checks; rerunning the saved batch made zero requests. Native-device legibility still needs the later on-device review, and live API generation has not been exercised.

The manual-only generation workflow produces preview artifacts. It has no schedule or deployment step. Its cache is a preview convenience, not durable production accounting; production activation must replace it with durable state. No workflow has been dispatched, no commits pushed, and no live TRMNL configuration changed as part of this local build.
