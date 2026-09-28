"""Outline the OG pixel font for Figma, which does not host TRMNL16.

Run after figma_snapshot.cjs. FontTools is only needed for this design handoff;
install it in qa/fonttools, which is excluded from the plugin export.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'qa/fonttools'))
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

fonts = {}
for weight in ('Regular', 'Bold'):
    f = TTFont(ROOT / f'preview/vendor/fonts/TRMNL16-{weight}.ttf')
    fonts[weight] = (f, f.getGlyphSet(), f.getBestCmap())


def convert(node):
    for text in node.get('texts', []):
        lines = []
        widths = []
        starts = []
        previous_y = None
        for char in text['chars']:
            if previous_y is None or abs(char['y'] - previous_y) > 2:
                lines.append('')
                widths.append(0)
                starts.append(char['x'])
            lines[-1] += char['c']
            if not char['c'].isspace():
                widths[-1] = max(widths[-1], char['x'] + char.get('w', 0) - starts[-1])
            previous_y = char['y']
        text['renderText'] = '\n'.join(line.strip() for line in lines)
        text['lineWidths'] = widths
        if 'TRMNL16' in text['font']:
            paths = []
            for c in text['chars']:
                f, glyphs, cmap = fonts['Bold' if c['weight'] >= 600 else 'Regular']
                if c['c'].isspace():
                    continue
                glyph = glyphs[cmap.get(ord(c['c'][0]), '.notdef')]
                pen = SVGPathPen(glyphs)
                scale = c['size'] / f['head'].unitsPerEm
                transform = (scale, 0, 0, -scale, c['x']-text['x'], c['y']-text['y'])
                glyph.draw(TransformPen(pen, transform))
                paths.append(pen.getCommands())
            text['svg'] = f'<svg xmlns="http://www.w3.org/2000/svg" width="{text["w"]}" height="{text["h"]}" viewBox="0 0 {text["w"]} {text["h"]}"><path fill="#000000" d="{" ".join(paths)}"/></svg>'
        del text['chars']
    for col in node.get('columns', []):
        convert(col)


screens = json.loads((ROOT / 'qa/figma-snapshots.json').read_text(encoding='utf-8'))
for screen in screens:
    for section in screen['sections'] + [screen['footer']]:
        convert(section)
(ROOT / 'qa/figma-ready.json').write_text(json.dumps(screens), encoding='utf-8')
print(f'Prepared {len(screens)} screens with native text outlines')
