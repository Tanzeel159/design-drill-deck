# Design Drill Deck

**Local redesign preview (September 2026):** 54 curated exercises, eight reusable illustrations, grouped context and practice instructions on the device, and optional capped API generation. Start with [LOCAL_PREVIEW.md](LOCAL_PREVIEW.md). This redesign has not been pushed or installed on the live device. The original implementation notes below describe the earlier release.

A TRMNL plugin that shows one realistic product-design interview drill per day. The 42-prompt bank spans Core UX, AI-Integrated Interfaces, Dashboard/Data UX, Accessibility, Enterprise UX, UX Engineering, and Information Architecture.

For design decisions, review history, and current recipe status, see [`PROJECT.md`](PROJECT.md). Questions about plugin setup and custom fields: [TRMNL custom plugin form builder](https://help.trmnl.com/en/articles/10513740-custom-plugin-form-builder#h_02dd8f84a9).

## Prompt source

Prompts are fetched from a version-controlled file, [`data/prompts.json`](data/prompts.json). There is no third-party prompt API and no generative model in the delivery path. Optional `gpt-5-mini` batches are compiled into [`data/generated.json`](data/generated.json) and merged when the daily feed is built, so a drill can still be reviewed, versioned, and shown if OpenAI is down.

To evolve the bank:

1. Add prompts with a new, permanent `ddd-NNN` ID and the existing content fields. Keep `primary_user` at 56 characters or fewer so the glanceable metadata row stays on one line.
2. Add at least three prompts for every new category so category-only rotation remains useful.
3. Add the category label/value to the `focus_area` options in `src/settings.yml`.
4. Run the tests and preview all layouts. CI rejects duplicate IDs, missing fields, undersized categories, stale generated data, or setup controls that drift from the bank.

Information Architecture includes six drills covering learning libraries, patient portals, enterprise knowledge, civic services, streaming navigation, and developer documentation.

## Daily rotation

`data/prompts.json` is the editable source of truth. `scripts/generate_daily.py` turns it into a date-stamped feed with two selection modes:

- **Smart shuffle (default):** creates a deterministic random order for each pool. Every eligible prompt appears once before the pool reshuffles, and adjacent cycles cannot repeat the same prompt.
- **Sequential:** follows the prompt bank order and wraps at the end.

The rotation is anchored so July 20, 2026 still selects `ddd-004`. Rotation uses `America/Chicago` calendar dates and continues across New Year and leap days.

The generated feed includes a pick for every category and practice level. Users with the same category, level, and order settings see the same prompt on a given day; random selection does not change on every screen render.

Difficulty is applied as a scope profile to every base prompt, so category-and-level combinations retain a useful prompt pool:

- **Beginner:** three expected patterns, one happy path, and one recovery state.
- **Intermediate (default):** four expected patterns, meaningful edge cases, and a success metric.
- **Advanced:** up to six patterns, system states, risk, accessibility, tradeoffs, and measurement.

Exercise timing is intentionally not displayed. Practice level communicates scope without implying that every prompt should take the same amount of time.

## User controls in TRMNL

`src/settings.yml` adds three plugin-specific controls to the TRMNL setup form:

- **Focus area:** all categories or one of the seven disciplines, including Information Architecture.
- **Practice level:** beginner, intermediate, or advanced.
- **Prompt order:** smart shuffle or sequential bank order.

TRMNL's normal playlist, mashup, display schedule, and device refresh controls remain available outside this plugin form.

## CI/CD

Three GitHub Actions workflows are included:

- `.github/workflows/ci.yml` runs on pushes and pull requests. It validates the prompt schema, generated feed, TRMNL settings, layouts, and shuffle behavior.
- `.github/workflows/trmnl.yml` pushes rebuilt markup to the live private plugin on every `main` commit that touches `src/` (requires `TRMNL_API_KEY`).
- `.github/workflows/generate-prompts.yml` runs weekly (Monday) and can be started by hand. Live runs need the `OPENAI_API_KEY` repository secret; they append accepted cards to `data/generated.json` and trigger a Pages publish. Manual runs default to `--mock` unless you check **live**.
- `.github/workflows/publish-daily.yml` generates the current feed and deploys it to GitHub Pages. It is still runnable by hand, and live generation triggers it after a successful batch.

Production data flow:

```text
prompts.json → scheduled generator → GitHub Pages daily.json → TRMNL background poll → Liquid layouts
```

The JSON response changes once per calendar day, allowing TRMNL to detect new content and generate the next screen. An hourly plugin poll limits normal rollover delay to about one polling interval, plus any GitHub Actions scheduling delay.

## Repository structure

- `data/prompts.json` — editable prompt bank.
- `data/generated.json` — accepted `gpt-5-mini` cards merged into the daily feed; the device never calls OpenAI.
- `data/daily.json` — generated local-preview fixture; do not edit by hand.
- `scripts/generate_daily.py` — deterministic daily-feed generator.
- `scripts/validate_project.py` — project and configuration checks.
- `tests/test_daily.py` — shuffle, boundary, and payload tests.
- `src/*.liquid` — the four TRMNL layouts.
- `src/settings.yml` — polling configuration and user controls.
- `preview/index.html` — local preview using the generated feed.

## Local development

Generate today's fixture and run the tests:

```bash
python scripts/generate_daily.py
python -m unittest discover -s tests -v
python scripts/validate_project.py
```

`validate_project.py` performs a full YAML parse when the development dependency is installed:

```bash
python -m pip install -r requirements-dev.txt
```

Start the preview:

```bash
python -m http.server 4173
```

Then open <http://localhost:4173/design-drill-deck/preview/>. The toolbar can preview every prompt, focus area, practice level, and rotation mode.

The preview also supports deep links for automated checks: `?device=x-portrait&drill=4&level=advanced` preselects the toolbar, and `?empty=1` simulates an empty feed to exercise the layouts' fallback state. Icon stroke weights and layout fitting are verified against the OG 1-bit and TRMNL X 4-bit fixtures in this preview; re-check on physical hardware after any icon change.

## Deploying the feed

1. Create a GitHub repository named `design-drill-deck` and push this project.
2. Replace `YOUR_GITHUB_USERNAME` in `src/settings.yml`.
3. In the repository, open **Settings → Pages → Build and deployment** and choose **GitHub Actions**.
4. Run **Publish daily prompt** once from the Actions tab.
5. Confirm `https://<your-username>.github.io/design-drill-deck/daily.json` returns JSON.

GitHub may disable scheduled workflows in public repositories after extended inactivity. A manual run republishes the current feed immediately.

## Installing in TRMNL

The daily JSON feed is published from GitHub Pages. Markup (the four views + Shared) is pushed to private plugin `472554` by GitHub Actions — no ZIP import on each change.

1. Confirm `https://Tanzeel159.github.io/design-drill-deck/daily.json` returns JSON.
2. In the GitHub repo, open **Settings → Secrets and variables → Actions** and add `TRMNL_API_KEY` (from [your TRMNL API key](https://trmnl.com/account)).
3. Push to `main` (or run **Push plugin to TRMNL** from the Actions tab). The workflow rebuilds layouts and runs `trmnlp push --force`.
4. In TRMNL, force a plugin refresh, then check OG and TRMNL X portrait.

ZIP import remains a fallback: `npm run export:trmnl` writes `design-drill-deck-trmnl.zip`, then **Plugins → Private Plugins → Import new**. Prefer GitHub push so you do not create a second plugin.

Custom-field help: [plugin form builder](https://help.trmnl.com/en/articles/10513740-custom-plugin-form-builder#h_02dd8f84a9). ZIP format: [importing and exporting private plugins](https://help.trmnl.com/en/articles/10542599-importing-and-exporting-private-plugins). `trmnlp` docs: [usetrmnl/trmnlp](https://github.com/usetrmnl/trmnlp).
