# Local studio — no publishing

The deck contains 54 curated exercises across nine categories, plus an optional saved queue of API-generated exercises. The API is never called by the browser or a device refresh. Accepted live cards are stored in `data/generated.json` and merged into `data/daily.json` when the feed is built, so TRMNL can show them after **Publish daily prompt**.

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

Use the category, prompt, practice-level, source, and device selectors. **Actual pixels · 100%** enables native-size inspection; scroll for large X screens. **Read full brief** opens the expanded scenario and discussion guidance. The full device card is a usable exercise: illustrated challenge, user/goal/constraint row, task and pattern row, and a separate watch-for note. Dotted dividers separate the rows, including the divider below task/patterns. Half layouts retain the essential instructions; the quadrant is explicitly a teaser with a full-screen hint.

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

No key means no request. Live mode uses `gpt-5-mini`, strict structured output, and one candidate per category. Accepted cards are appended to `data/generated.json` and the local daily feed is rebuilt. The key is never written to the feed or logs. Do not put it in settings.yml or daily.json.

Each ISO week allows two requests, with at most ten per calendar month. Requests are reserved on disk before sending; a timeout still counts because it may have been billed. Each request uses a conservative input byte ceiling below 8,000 tokens, including its schema/envelope, and a 12,000 output-token limit. No image generation, web tools, or extra model-based review runs. Limits apply to this local state file, not to unrelated usage on your API account. Retain `.runtime/state.json` to retain usage history.

Missing keys, timeouts, rate limits, invalid responses, or failed rendering leave saved cards usable. A partial batch saves only accepted candidates. A completed same-week batch is not generated again. Authentication and model access must be configured in the provider account.

A generated card is selected for its category on the first days after `generated_at`, then the curated calendar continues unchanged. Historical dates such as 2026-07-20 still select `ddd-004`. The GitHub **Generate prompt batch** workflow runs live every Monday and can also be started by hand. Live runs need the `OPENAI_API_KEY` repository secret; they commit accepted cards and trigger **Publish daily prompt**. Do not put the key in `.env` in git, `settings.yml`, or `daily.json`.

## Selection and storage

`data/prompts.json` is the reviewed offline source. Existing IDs and full-brief fields are preserved. Each prompt also has `display_title`, `display_brief`, `compact_brief`, `visual_key`, `provenance`, and optionally `render_layout: poster`.

`JsonStateStore` implements the storage interface with atomic writes and an exclusive operation lock. Runtime state contains generated cards, weekly batch IDs, request/usage counters, and per-category/order/level queues and date selections. A future remote implementation can replace storage without changing card validation or selection.

Fresh unshown generated cards are chosen first for each eligible category, then curated cards are consumed without repeating within a cycle. Smart shuffle and sequential order remain separate. Same-day selections stay fixed even if a new batch arrives. The Offline source has separate queues, so inspecting it does not consume the generated queue. Runtime state is local to this machine; it is not device history or a multi-user account service.

If a process is forcibly terminated, a `.runtime/*.lock` may remain. Only remove that exact lock after confirming no generation or preview operation is running; keep the JSON state and usage counters. Corrupt state is not overwritten automatically.

## Design source and tests

The updated designs are on [02 · Local implementation in Figma](https://www.figma.com/design/GdHCyZDIvAsd1p17ICo5ha?node-id=21-17): nine screens, including the hotel example, new categories, three mashups, and both X orientations. Headings use reusable component instances. OG pixel text is vectorized for font fidelity; Inter text is editable. The concept gallery remains a record of the earlier directions. Browser rendering remains the authority for exact text wrapping and the platform title bar.

Edit the native Framework class choices in `scripts/build_layouts.py`, selection in `src/selection.liquid`, and drawings in `assets/visuals.json`. Run `python scripts/build_layouts.py` to assemble Shared and the four views. Shared is prepended to each view, matching TRMNL's renderer. The exported markup contains no style attributes or embedded stylesheets. The former `src/card.css` is no longer used.

TRMNL X uses a logical 1040 × 780 canvas at a 1.8 scale. X typography is specified in logical pixels, not physical panel pixels. Preview images should be judged at native size and on hardware.

```powershell
python -m unittest discover -s tests -v
python scripts/validate_project.py
npm run test:layout
```

The browser gate checks every curated card at six device configurations and all three practice levels (972 combinations), required device fields, empty states, and unknown visuals. Screenshots are saved under ignored `qa/`. Windows uses installed Edge; other platforms need `npx playwright install chromium`. Set `DDD_BROWSER` to an executable path if needed; `DDD_NODE` can select Node for Python's render gate.

The September 8 brief redesign preserves native Framework fonts and illustrated category art. Inter headings and a larger summary establish hierarchy; compact TRMNL16 body text keeps supporting detail readable on OG. X uses native Inter throughout. `scripts/figma_snapshot.cjs` captures browser geometry for Figma; `scripts/figma_native_text.py` outlines the OG pixel text using optional FontTools installed under `qa/fonttools`. This avoids substituting a different font in Figma. These QA files are not included in the device export.

Local review on 2026-09-08: 29 unit tests passed; project/schema validation passed; all 324 curated prompt/device combinations passed the browser fit gate. The nine-card mock batch passed validation and browser checks; rerunning the saved batch made zero requests. Native-device legibility still needs the later on-device review, and live API generation has not been exercised.

The generation workflow runs live every Monday, persists accepted cards to `data/generated.json`, and then triggers **Publish daily prompt**. It does not push TRMNL markup. Live runs require the `OPENAI_API_KEY` repository secret.

## Export for TRMNL

Run `npm run export:trmnl` to rebuild the layouts, validate the six required files, and write `design-drill-deck-trmnl.zip` at the project root with a flat archive layout. After local approval, in TRMNL open **Plugins → Private Plugins → Import new** and select that ZIP. The export contains the current polling URL in `settings.yml`; it does not include `.runtime`, `.env`, the prompt bank, preview files, or credentials. Make layout changes in `scripts/build_layouts.py`; exporting regenerates the four view templates.

All four views include a Framework `.title_bar` sibling of `layout layout--col`, with the plugin name and (except quadrant) the date. Native fonts are bundled only for the local preview; TRMNL supplies them on the device.
