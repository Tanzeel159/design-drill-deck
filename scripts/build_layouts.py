"""Assemble views with native TRMNL Framework classes and no embedded CSS."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def native_view(suffix):
    compact = suffix != 'full'
    pad = 'p--4' if suffix in ('hh', 'q') else 'p--6'
    gap = 'gap' if suffix in ('hh', 'q') else 'gap--large'
    title_size = {'full': 'font--xxxlarge', 'hh': 'title title--large',
                  'hv': 'font--xxlarge', 'q': 'font--xlarge'}[suffix]
    body_size = 'description description--xlarge' if suffix == 'hh' else 'font--xlarge'
    root_classes = f'layout flex flex--col flex--stretch-x {gap} {pad} text--black text--left'
    main_classes = 'flex flex--row flex--left flex--center-y gap--large flex-auto h--min-0 w--full'
    copy_classes = f'flex flex--col flex--stretch-x flex--center-y {gap} flex-auto w--min-0'
    if not compact:
        main_classes += ' portrait:flex--col portrait:flex--center'
        copy_classes += ' portrait:flex-none portrait:w--full'
    title_classes = f'ddd-title {title_size} text--bold m--0 w--full'
    brief_classes = f'ddd-brief {body_size} m--0 w--full'
    header_classes = 'ddd-kicker label label--large text--bold m--0 flex-none w--full'
    category = '{{ level_profile.label | default: difficulty | capitalize | escape }}'
    if suffix not in ('q', 'hh'):
        category = '{{ p.mode | escape }} · ' + category
    heading = 'card_compact' if suffix == 'q' else 'card_title'
    brief_key = 'card_compact' if compact else 'card_brief'
    brief = '' if suffix == 'q' else f'<p class="{brief_classes}">{{{{ {brief_key} | escape }}}}</p>'
    art = '' if compact else '''{% if card_style != 'poster' %}<div class="ddd-art flex flex--center flex-none w--48 lg:w--64 portrait:w--64">{{ card_art }}</div>{% endif %}'''
    date = '' if suffix == 'q' else '<span class="instance">{{ display_date | date: "%b %-d" }}</span>'
    help_text = '' if suffix in ('q', 'hh') else f'<p class="{brief_classes}">Try again on the next refresh.</p>'
    return f'''<!-- Native Framework sizing and lg: / portrait: composition; ddd-* hooks are for inspection only. -->
<article class="ddd-card ddd-{suffix} ddd-{{{{ card_style }}}} {root_classes}" data-card-id="{{{{ p.id | escape }}}}">
{{% if p == blank %}}
  <p class="{header_classes}">Design Drill Deck</p>
  <div class="ddd-main {main_classes}"><div class="ddd-copy {copy_classes}"><h1 class="{title_classes}">No drill available.</h1>{help_text}</div></div>
{{% else %}}
  <p class="{header_classes}">{category}</p>
  <div class="ddd-main {main_classes}">
    <div class="ddd-copy {copy_classes}"><h1 class="{title_classes}">{{{{ {heading} | escape }}}}</h1>{brief}</div>
    {art}
  </div>
{{% endif %}}
</article>
<div class="title_bar ddd-footer">
  <span class="title">Design Drill Deck</span>{date}
</div>
'''


def build():
    src = ROOT / 'src'
    selection = src / 'selection.liquid'
    if not selection.exists():
        old = (src / 'full.liquid').read_text(encoding='utf-8')
        selection.write_text(old.split('\n{% if p == blank %}\n<div')[0] + '\n', encoding='utf-8')
    visuals = json.loads((ROOT / 'assets/visuals.json').read_text(encoding='utf-8'))
    art = '{% capture card_art %}{% case p.visual_key %}'
    for key, svg in visuals.items():
        svg = svg.replace('<svg ', '<svg class="w--full h--auto" ', 1)
        art += '{% when "' + key + '" %}' + svg
    art += '{% endcase %}{% endcapture %}\n'
    shared = selection.read_text(encoding='utf-8') + art
    shared += '''{% assign card_title = p.display_title | default: p.problem %}
{% assign card_brief = p.display_brief | default: p.problem %}
{% assign card_compact = p.compact_brief | default: card_brief %}
{% assign card_style = p.render_layout | default: 'visual' %}
{% assign stripped_art = card_art | strip %}
{% if stripped_art == blank %}{% assign card_style = 'poster' %}{% endif %}
'''
    (src / 'shared.liquid').write_text(shared, encoding='utf-8')
    for layout, suffix in [('full', 'full'), ('half_horizontal', 'hh'), ('half_vertical', 'hv'), ('quadrant', 'q')]:
        body = native_view(suffix)
        body = '\n'.join(line.rstrip() for line in body.splitlines()) + '\n'
        (src / (layout + '.liquid')).write_text(body, encoding='utf-8')


if __name__ == '__main__':
    build()
