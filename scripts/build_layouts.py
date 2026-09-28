"""Assemble views with native TRMNL Framework classes and no embedded CSS."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def native_view(suffix):
    full = suffix == 'full'
    # .label is nowrap inline-flex; wrapping copy must use description/title.
    kicker_class = 'description lg:description--large text--bold m--0 w--full'
    field_label = 'title title--small lg:title--base text--bold m--0'
    body = 'description description--large lg:description--xlarge m--0 w--full'
    icons = {
        'user': '<circle cx="12" cy="7" r="4"/><path d="M4 22v-3a8 8 0 0 1 16 0v3"/>',
        'goal': '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
        'constraint': '<rect x="5" y="10" width="14" height="12" rx="2"/><path d="M8 10V6a4 4 0 0 1 8 0v4"/>'
    }

    def field(name, value, key, clamp=None):
        icon = ''
        if key in icons:
            icon = (
                f'<svg class="flex-none" xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
                f'viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" '
                f'stroke-linecap="round" stroke-linejoin="round">{icons[key]}</svg>'
            )
        heading = f'<div class="flex flex--row flex--left flex--center-y gap--small w--full">{icon}<h2 class="{field_label}">{name}</h2></div>'
        clamp_attr = f' data-clamp="{clamp}"' if clamp else ''
        return (
            f'<div class="flex flex--col flex--stretch-x gap--xsmall w--full w--min-0">{heading}'
            f'<p class="{body}"{clamp_attr}>{{{{ {value} | escape }}}}</p></div>'
        )

    def inline(name, value, clamp=None, clamp_lg_portrait=None):
        # A <strong> inside .description loses its weight and confuses data-clamp,
        # so the label and value are separate flex items.
        clamp_attr = f' data-clamp="{clamp}"' if clamp else ''
        if clamp_lg_portrait:
            clamp_attr += f' data-clamp-lg-portrait="{clamp_lg_portrait}"'
        return (
            f'<div class="flex flex--row flex--left flex--top m--0 w--full">'
            f'<span class="text text--base lg:text--large text--bold flex-none">{name}</span>'
            f'<span class="description description--large lg:description--xlarge flex-auto w--min-0"{clamp_attr}>'
            f'{{{{ {value} | escape }}}}</span></div>'
        )

    title = 'title title--xlarge lg:title--xxlarge portrait:title--xlarge' if full else 'title title--large lg:title--xlarge portrait:title--large'
    kicker_text = '{{ card_mode | escape }} · {{ level_profile.label | default: difficulty | capitalize | escape }}' if suffix in ('full', 'hv') else '{{ level_profile.label | default: difficulty | capitalize | escape }} practice'
    hh_clamp = ' data-clamp="2"' if suffix == 'hh' else ''
    heading = f'<h1 class="{title} text--bold m--0 w--full"{hh_clamp}>{{{{ card_title | escape }}}}</h1>'
    brief_class = 'description description--xlarge lg:description--xxlarge m--0 w--full' if full else body
    brief_key = 'card_brief' if full else 'card_compact'
    brief = f'<p class="{brief_class}"{hh_clamp}>{{{{ {brief_key} | escape }}}}</p>'
    art = '{% if stripped_art != blank %}<div class="w--20 lg:w--48 portrait:w--32 flex-none">{{ card_art }}</div>{% endif %}'
    lg_only = 'hidden lg:visible'
    lg_group = 'hidden lg:flex flex--col flex--stretch-x gap--medium w--full'
    scope = field('Your task', 'card_scope_short', 'scope', 2)
    if full:
        context_items = [
            ('Who it is for', 'p.primary_user', 'user'),
            ('Goal', 'p.business_goal', 'goal'),
            ('Constraint', 'p.constraint', 'constraint'),
        ]
        context_parts = []
        for index, item in enumerate(context_items):
            if index:
                context_parts.append('<div class="divider divider--v portrait:hidden"></div>')
            context_parts.append(
                f'<div class="flex flex--col flex--stretch-x w--1/3 portrait:w--full w--min-0">{field(*item, clamp=2)}</div>'
            )
        context = ''.join(context_parts)
        content = f'''<div class="flex flex--row flex--left flex--center-y gap--large lg:gap--xlarge w--full portrait:flex--col">{art}<div class="flex flex--col flex--stretch-x gap--small lg:gap--medium flex-auto w--min-0">{heading}{brief}</div></div>
  <div class="divider w--full"></div>
  <div class="flex flex--row flex--left flex--top gap--medium lg:gap--large w--full portrait:flex--col">{context}</div>
  <div class="divider w--full"></div>
  <div class="flex flex--row flex--left flex--top gap--large w--full portrait:flex--col">
    <div class="w--1/2 portrait:w--full w--min-0">{scope}</div><div class="w--1/2 portrait:w--full w--min-0">{field('Work through', 'card_patterns', 'patterns', 2)}</div>
  </div>
  <div class="divider w--full"></div>
  {inline('Watch for:', 'p.watch_for', 2)}
  <div class="{lg_only} lg:portrait:hidden w--full">{inline('Discuss:', 'p.interview_focus', 2)}</div>'''
    elif suffix == 'hh':
        # Fixed grid tracks give data-clamp a stable width; flex columns resize with their text.
        content = (
            heading + brief + inline('Constraint:', 'p.constraint', 1)
            + f'<div class="{lg_group}">'
            + '<div class="grid grid--cols-2 lg:portrait:grid--cols-1 gap--large lg:portrait:gap--medium w--full">'
            + '<div class="flex flex--col flex--stretch-x gap--medium w--min-0">'
            + inline('Who:', 'p.primary_user', 1)
            + inline('Goal:', 'p.business_goal', 1)
            + '</div><div class="flex flex--col flex--stretch-x gap--medium w--min-0">'
            + inline('Produce:', 'card_scope_short', 1)
            + inline('Watch for:', 'p.watch_for', 1)
            + '</div></div></div>'
        )
    elif suffix == 'hv':
        content = (
            heading + brief + '<div class="border--h w--full"></div>'
            + ''.join(
                inline(*item)
                for item in [
                    ('Who:', 'p.primary_user'),
                    ('Goal:', 'p.business_goal'),
                    ('Constraint:', 'p.constraint'),
                    ('Produce:', 'card_scope_short'),
                ]
            )
            + f'<div class="{lg_group}">'
            + inline('Work through:', 'card_patterns', 2)
            + inline('Watch for:', 'p.watch_for', 1)
            + inline('Discuss:', 'p.interview_focus', 2)
            + '</div>'
        )
    else:
        content = (
            heading + brief
            + f'<div class="{lg_group}">'
            + inline('Constraint:', 'p.constraint', 1, 2)
            + inline('Who:', 'p.primary_user', 1, 2)
            + inline('Produce:', 'card_scope_short', 1, 2)
            + '</div>'
        )
    pad = 'p--4'
    gap = 'gap--small lg:gap--large' if full else 'gap--small lg:gap--medium'
    if suffix == 'q':
        title_bar = '<div class="title_bar"><span class="title">Design Drill Deck</span></div>'
    else:
        title_bar = (
            "{% assign title_instance = display_date | date: '%b %-d' %}"
            '<div class="title_bar"><span class="title">Design Drill Deck</span>'
            '{% if title_instance != blank %}<span class="instance">{{ title_instance }}</span>{% endif %}'
            '</div>'
        )
    return f'''<!-- Native Framework brief: essential instructions are rendered on the device. -->
<div class="layout layout--col flex--stretch-x flex--top {gap} {pad} text--black text--left">
{{% if feed_empty or p == blank %}}
  <p class="{kicker_class}">Design Drill Deck</p>
  <h1 class="{title} text--bold m--0 w--full">No prompts loaded.</h1>
  <p class="{body}">The daily deck is empty or did not arrive. It will retry on the next refresh.</p>
{{% else %}}
  <p class="{kicker_class}">{kicker_text}</p>
  {content}
{{% endif %}}
</div>
{title_bar}
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
        svg = re.sub(r'\s(width|height)="\d+"', '', svg, count=2)
        svg = svg.replace('<svg ', '<svg class="w--full h--auto" ', 1)
        art += '{% when "' + key + '" %}' + svg
    art += '{% endcase %}{% endcapture %}\n'
    shared = selection.read_text(encoding='utf-8') + art
    shared += '''{% assign card_title = p.display_title | default: p.problem %}
{% assign card_brief = p.display_brief | default: p.problem %}
{% assign card_compact = p.compact_brief | default: card_brief %}
{% assign card_patterns = p.required_patterns | slice: 0, pattern_limit | join: ' · ' %}
{% assign card_scope = level_profile.scope_note %}
{% case difficulty %}
{% when 'beginner' %}{% assign card_scope_short = 'Main path, key screen, one recovery state.' %}
{% when 'advanced' %}{% assign card_scope_short = 'System states, risks, accessibility + measurement.' %}
{% else %}{% assign card_scope_short = 'Main flow, two edge cases + one success metric.' %}
{% endcase %}
{% if p.mode == 'Everyday UX' or p.mode == 'Dark Patterns' %}
  {% case difficulty %}
  {% when 'beginner' %}{% assign card_scope = 'Describe one observation and sketch an alternative.' %}
  {% when 'advanced' %}{% assign card_scope = 'Compare alternatives, examine tradeoffs, and explain how to measure the improvement.' %}
  {% else %}{% assign card_scope = 'Explain the user impact, sketch an alternative, and propose a way to test it.' %}
  {% endcase %}
  {% assign card_scope_short = card_scope %}
{% endif %}
{% comment %}
card_style maps p.render_layout from the daily feed onto CSS hooks:
  visual — illustrated brief; the SVG sits beside the copy on full.
  poster — type-only; used when the prompt sets render_layout: poster
           or when visual_key has no matching SVG (blank card_art).
{% endcomment %}
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
