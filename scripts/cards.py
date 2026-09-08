"""Provider-independent content contract for offline and generated cards."""
import hashlib
import re
from difflib import SequenceMatcher

VISUALS = ('recovery', 'comparison', 'trust', 'access', 'progress', 'overload', 'friction', 'choice')
CATEGORIES = ('Core UX Flow', 'AI-Integrated Interface', 'Dashboard & Data UX',
              'Accessibility Challenge', 'Enterprise UX', 'UX Engineering',
              'Information Architecture', 'Everyday UX', 'Dark Patterns')
TEXT_FIELDS = ('mode', 'industry', 'primary_user', 'business_goal', 'constraint',
               'problem', 'ai_capability', 'watch_for', 'interview_focus',
               'display_title', 'display_brief', 'compact_brief', 'visual_key')
LIST_FIELDS = ('required_patterns', 'deliverables')


def normalized(value):
    return ' '.join(re.findall(r'\w+', value.casefold()))


def content_id(card):
    return 'gen-' + hashlib.sha256(normalized(card['problem']).encode()).hexdigest()[:16]


def validate_card(card, existing=()):
    if not isinstance(card, dict):
        raise ValueError('Candidate must be an object')
    for key in TEXT_FIELDS:
        value = card.get(key)
        if not isinstance(value, str) or (key != 'ai_capability' and not value.strip()):
            raise ValueError(f'{key} must be text')
        if '<' in value or '>' in value or any(ord(ch) < 32 for ch in value):
            raise ValueError(f'{key} must be plain, single-line text')
        if len(value) > 700:
            raise ValueError(f'{key} is too long')
    for key in LIST_FIELDS:
        values = card.get(key)
        if not isinstance(values, list) or not 1 <= len(values) <= 6:
            raise ValueError(f'{key} must contain one to six items')
        if any(not isinstance(v, str) or not v.strip() or len(v) > 150 or '<' in v or '>' in v for v in values):
            raise ValueError(f'{key} has invalid items')
    for key, limit in [('primary_user', 56), ('display_title', 42), ('display_brief', 150), ('compact_brief', 100)]:
        if len(card[key]) > limit:
            raise ValueError(f'{key} exceeds {limit} characters')
    if card['mode'] not in CATEGORIES:
        raise ValueError('Unknown category')
    if card['visual_key'] not in VISUALS:
        raise ValueError('Unknown visual key')
    if not re.search(r'\b(design|redesign|help|find|make|turn|organize|build|notice|recall|think|show|connect|combine|identify|bring|replace|rewrite|separate)\b', card['display_brief'], re.I):
        raise ValueError('Display brief needs a concrete action')
    for other in existing:
        for key in ('problem', 'display_brief', 'compact_brief'):
            a, b = normalized(card[key]), normalized(other[key])
            if a == b or SequenceMatcher(None, a, b).ratio() >= .88:
                raise ValueError(f'Near-duplicate of {other.get("id", "another candidate")}')
    return card


def response_schema():
    props = {key: {'type': 'string'} for key in TEXT_FIELDS}
    props['mode']['enum'] = list(CATEGORIES)
    props['visual_key']['enum'] = list(VISUALS)
    props.update({key: {'type': 'array', 'items': {'type': 'string'}} for key in LIST_FIELDS})
    return {'type': 'object', 'additionalProperties': False,
            'properties': {'prompts': {'type': 'array', 'minItems': 9, 'maxItems': 9,
                            'items': {'type': 'object', 'additionalProperties': False,
                                      'properties': props, 'required': list(props)}}},
            'required': ['prompts']}
