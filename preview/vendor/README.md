# Local preview assets

The preview deliberately makes no third-party network requests.

- `plugins.css` and `plugins.js`: TRMNL framework, retrieved from `https://trmnl.com/css/latest/plugins.min.css` and `https://trmnl.com/js/latest/plugins.js` on 2026-09-08. Framework source: https://github.com/usetrmnl/framework (MIT).
- `fonts/Inter.ttf`: TRMNL's Inter font, retrieved from `https://trmnl.com/fonts/Inter.ttf`; Inter is distributed under the SIL Open Font License: https://github.com/rsms/inter/blob/master/LICENSE.txt.
- `fonts/TRMNL12-*.ttf`, `fonts/TRMNL16-*.ttf`, `fonts/TRMNL21-*.ttf`: TRMNL's OG pixel fonts, retrieved from `https://trmnl.com/fonts/` (TRMNL12 and TRMNL21 on 2026-09-28).
- `liquid.js`: copied from `liquidjs@10.29.0/dist/liquid.browser.min.js`, MIT: https://github.com/harttle/liquidjs/blob/master/LICENSE.

The runtime font face is overridden in `studio.css` to use the local Inter file. The card renderer runs `terminalize()` from `plugins.js` after each render, so `data-clamp` and its responsive variants behave as they do on the device. The framework stylesheet retains its original font paths for unused framework styles.

These assets belong to the local preview. TRMNL supplies its own framework and fonts when the plugin is installed.
