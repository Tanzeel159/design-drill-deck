"""Assemble Shared + four self-contained TRMNL views from the local design source."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build():
    src = ROOT / 'src'
    selection = src / 'selection.liquid'
    if not selection.exists():
        old = (src / 'full.liquid').read_text(encoding='utf-8')
        selection.write_text(old.split('\n{% if p == blank %}\n<div')[0] + '\n', encoding='utf-8')
    css = (src / 'card.css').read_text(encoding='utf-8')
    visuals = json.loads((ROOT / 'assets/visuals.json').read_text(encoding='utf-8'))
    art = '{% capture card_art %}{% case p.visual_key %}'
    for key, svg in visuals.items():
        art += '{% when "' + key + '" %}' + svg
    art += '{% endcase %}{% endcapture %}\n'
    shared = '<style>\n' + css + '\n</style>\n' + selection.read_text(encoding='utf-8') + art
    shared += '''{% assign card_title = p.display_title | default: p.problem %}
{% assign card_brief = p.display_brief | default: p.problem %}
{% assign card_compact = p.compact_brief | default: card_brief %}
{% assign card_style = p.render_layout | default: 'visual' %}
{% assign stripped_art = card_art | strip %}
{% if stripped_art == blank %}{% assign card_style = 'poster' %}{% endif %}
'''
    (src / 'shared.liquid').write_text(shared, encoding='utf-8')
    for layout, suffix in [('full', 'full'), ('half_horizontal', 'hh'), ('half_vertical', 'hv'), ('quadrant', 'q')]:
        heading = 'card_compact' if suffix == 'q' else 'card_title'
        brief = '' if suffix == 'q' else '<p class="ddd-brief">{{ ' + ('card_brief' if suffix == 'full' else 'card_compact') + ' | escape }}</p>'
        category = '{{ level_profile.label | default: difficulty | capitalize | escape }}' if suffix == 'q' else '{{ p.mode | escape }} · {{ level_profile.label | default: difficulty | capitalize | escape }}'
        body = '''<!-- Shared markup supplies selection and styles, including lg: and portrait: adaptations. -->
<article class="ddd-card ddd-SUFFIX ddd-{{ card_style }}" data-card-id="{{ p.id | escape }}">
{% if p == blank %}
  <p class="ddd-kicker">Design Drill Deck</p>
  <div class="ddd-main"><div class="ddd-copy"><h1 class="ddd-title">No drill available.</h1>EMPTY_HELP</div></div>
{% else %}
  <p class="ddd-kicker">CATEGORY</p>
  <div class="ddd-main">
    <div class="ddd-copy"><h1 class="ddd-title">{{ HEADING | escape }}</h1>BRIEF</div>
    ART
  </div>
{% endif %}
  <footer class="ddd-footer"><span>Design Drill Deck</span>FOOTER</footer>
</article>
'''
        body = body.replace('SUFFIX', suffix).replace('CATEGORY', category).replace('HEADING', heading).replace('BRIEF', brief)
        body = body.replace('ART', '<div class="ddd-art">{{ card_art }}</div>' if suffix == 'full' else '')
        body = body.replace('EMPTY_HELP', '<p class="ddd-brief">Try again on the next refresh.</p>' if suffix in ('full', 'hv') else '')
        body = body.replace('FOOTER', '<span>{{ display_date | date: "%b %-d" }}</span>' if suffix != 'q' else '')
        body = '\n'.join(line.rstrip() for line in body.splitlines()) + '\n'
        (src / (layout + '.liquid')).write_text(body, encoding='utf-8')


if __name__ == '__main__':
    build()
