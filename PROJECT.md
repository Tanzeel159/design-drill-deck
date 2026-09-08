# Design Drill Deck — project recap

A TRMNL recipe plugin that puts one realistic product-design interview drill on an e-ink display each day. Designers pick a focus area and practice level, then work the prompt as a studio brief.

**Live feed:** https://Tanzeel159.github.io/design-drill-deck/daily.json  
**Source:** https://github.com/Tanzeel159/design-drill-deck  
**Recipe ticket:** `#118084990` — RECIPE: Design Drill Deck

## Questions and issues

For plugin setup, custom fields, and form-builder questions, start here:

- [TRMNL custom plugin form builder](https://help.trmnl.com/en/articles/10513740-custom-plugin-form-builder#h_02dd8f84a9)

Other contacts:

- TRMNL recipe review and plugin support: [support@trmnl.com](mailto:support@trmnl.com)
- Plugin author: [tanzeel.ahmed1306@gmail.com](mailto:tanzeel.ahmed1306@gmail.com)
- GitHub issues: https://github.com/Tanzeel159/design-drill-deck/issues

---

## What this project is

Design Drill Deck is a **polling plugin**, not a Node app. A version-controlled prompt bank (`data/prompts.json`) is compiled into a date-stamped JSON feed. TRMNL polls that feed once an hour. Liquid layouts in `src/` render four mashup sizes: full, half horizontal, half vertical, and quadrant.

The bank currently has **42 prompts** across seven categories:

- Core UX Flow
- AI-Integrated Interface
- Dashboard & Data UX
- Accessibility Challenge
- Enterprise UX
- UX Engineering
- Information Architecture

Difficulty is a **scope profile**, not a different prompt. Beginner, intermediate, and advanced change how many patterns to design and how deep the solution should go. Exercise timing is intentionally not shown on the device.

Users configure three plugin fields:

| Control | Default | Purpose |
| --- | --- | --- |
| Focus area | All categories | Practice every discipline or one |
| Practice level | Intermediate | Change expected solution depth |
| Prompt order | Smart shuffle | Avoid repeats until the pool is exhausted |

Smart shuffle is deterministic: the same settings produce the same drill on a given `America/Chicago` calendar day.

Production path:

```text
prompts.json → GitHub Actions generator → GitHub Pages daily.json → TRMNL hourly poll → Liquid layouts
```

Local preview is a static harness at `preview/index.html`. It is not an npm app. From the `TRMNL` folder:

```bash
python -m http.server 4173
```

Open http://localhost:4173/design-drill-deck/preview/

---

## Design decisions

The visual language is a **type-led, high-contrast monochrome brief** for 1-bit e-ink:

- Hierarchy comes from type size, weight, dividers, and spacing — not color.
- Line icons mark category and metadata; they stay compact enough for OG.
- Four layouts share one information model: drill number, problem, scope, user/goal, “Design these,” interview focus.
- Smaller mashups drop fields instead of shrinking everything equally. Half horizontal joins patterns with middots. Quadrant keeps only the problem.
- Prompt content is static JSON. No generative model sits in the delivery path, so a drill can be reviewed, versioned, and still appear if an external API is down.
- Rotation is anchored so 2026-07-20 still selects `ddd-004`, which made local and recipe-review screenshots comparable.
- Framework classes only. Layouts do not use inline `style=` attributes, which TRMNL recipe validation rejects.

Responsive strategy:

- `lg:` classes scale type and spacing for TRMNL X (large / 4-bit).
- `portrait:` classes reflow the two-column full layout into one column on X portrait.
- `hidden` / `lg:block` pairs unclamp long copy on X so landscape and portrait can use extra pixels.

---

## How we refined it

### Local preview and deploy

The plugin is Python + Liquid + GitHub Pages. Early confusion around `npm run dev` was a wrong stack: there is no `package.json`. The preview server must be started from `TRMNL` (parent of `design-drill-deck`); `/preview/` 404s from that folder, while `/design-drill-deck/preview/` works.

The repo was initialized, pushed to GitHub, and GitHub Pages was enabled with the Publish daily prompt workflow. CI originally failed because `setup-python` pip cache expected `requirements.txt`; the cache path now points at `requirements-dev.txt`.

### Alignment

TRMNL’s `flex--row` defaults to `justify-content: center`. Checklist rows (“Design these”) were centering independently, so checkboxes formed a ragged column. Adding `flex--left` to those rows in `full.liquid` and `half_vertical.liquid` left-aligns them across OG, X landscape, and X portrait.

### AI Chef recipe review (`#118084990`, “needs work, 1 critical”)

The first automated review found one critical issue and several suggestions. Disposition:

| # | Severity | Reviewer note | What we did |
| --- | --- | --- | --- |
| 1 | **Critical** | If `prompts`, `difficulty_levels`, or `daily_picks` are empty, templates render a blank screen. Add a Liquid fallback. | There is no `shared.liquid`. Each of the four layouts now checks `{% if p == blank %}` after all lookup paths and shows “Unable to load today’s drill” plus a retry note. Preview flag `?empty=1` exercises that state. |
| 2 | Suggestion | Hero `data-clamp` might overflow on OG 800×480. | Rendered the longest bank problem (167 characters, drill 5) on OG full. It fits the three-line clamp; longer future prompts truncate with an ellipsis. Left as-is. |
| 3 | Suggestion | Half-horizontal middot pattern list may overflow. Add `data-clamp="1"`. | Already present on that description span. No change. |
| 4 | Suggestion | SVG `stroke-width` may scale unpredictably on 1-bit vs 4-bit. | Verified in the OG and X preview fixtures. Documented in the README that icons should be re-checked on hardware after icon changes. |
| 5 | Nitpick | Portrait grid gap could be tighter (`portrait:gap--medium`). | Left as-is; reviewer called the current fallback acceptable, and portrait spacing was comfortable in screenshots. |

### Local layout QA

Preview deep links (`?device=`, `?drill=`, `?level=`, `?empty=1`) were added so device modes can be screenshot without clicking the toolbar. Alignment and empty-feed states were checked with headless Chrome against OG full, X landscape, X portrait, half vertical, half horizontal, and quadrant.

---

## Current status (8 Sep 2026)

**Shipped and working**

- Daily feed live on GitHub Pages
- CI and Publish daily prompt workflows green on `main`
- Local preview at http://localhost:4173/design-drill-deck/preview/
- Empty-feed fallback on all four layouts (uncommitted vs `origin/main`)
- Checklist left-alignment fix (uncommitted vs `origin/main`)

**Local vs GitHub:** alignment, fallback, preview deep links, and README notes exist in the working tree and have **not** been pushed since commit `124fe56`. The live Pages feed is still the earlier published build.

**Open recipe feedback from Mario (29 Jul 2026)** — not implemented yet:

> OG looks good, and TRMNL X has good reflow for portrait, but there is SOME scaling, but for the bullet points in the middle, there is no X scaling and this is true across all views. Additionally, on portrait, you can add details that are visible only on X to make better use of the available space using a hidden div for instance: `<div class="hidden lg:visible">`.
>
> Basically, if you have an element that doesn't have a `lg:` scaling, you should add it to eat up that whitespace.
>
> Let me know when you are ready for another review!

That maps to concrete layout gaps:

- Middle metadata and “Design these” rows use `description` without `lg:description--large` (or similar) on full, half vertical, and related views.
- Portrait X still has unused vertical space. Extra fields (constraint, more patterns, longer interview focus) can be shown with `hidden lg:block` / `hidden lg:visible` so OG stays dense and X uses the extra canvas.
- Any remaining element without an `lg:` size, gap, or type variant should get one before the next recipe review.

**Recipe process notes**

- Ticket `#118084990` starts as Submitted. TRMNL Recipe Reviews do not email until status leaves Submitted.
- Ticket links from the dashboard go to the TRMNL dashboard, not a standalone messenger thread. Status changes and reviewer replies (AI Chef, then Mario) arrive by email once the ticket is in review.

---

## How to run it locally

From `d:\Tanzeel\Projects\TRMNL`:

```bash
python -m http.server 4173
```

Preview: http://localhost:4173/design-drill-deck/preview/

Regenerate the feed and run checks from `design-drill-deck`:

```bash
python scripts/generate_daily.py
python -m unittest discover -s tests -v
python scripts/validate_project.py
```

Optional YAML validation:

```bash
python -m pip install -r requirements-dev.txt
```
