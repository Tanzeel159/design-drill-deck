"""Manual, capped generation. No network call without --live and a local API key."""
import argparse
from datetime import date
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.cards import CATEGORIES, TEXT_FIELDS, LIST_FIELDS, content_id, response_schema, validate_card
from scripts.generate_daily import load_prompts, resolve_date
from scripts.local_state import JsonStateStore

MODEL = 'gpt-5-mini'
MAX_REQUESTS_MONTH = 10
MAX_REQUESTS_BATCH = 2
MAX_INPUT_TOKENS = 8000
MAX_OUTPUT_TOKENS = 12000


def make_request(existing):
    recent = [p['display_title'] for p in existing[-12:]]
    guidance = (
        'Write nine distinct product-design practice exercises, exactly one per category. '
        'Categories: ' + '; '.join(CATEGORIES) + '. '
        'Use clear, concrete English. These are daily e-ink cards for UX designers. '
        'display_title: at most 42 characters; display_brief: at most 150 characters, '
        'a complete actionable task; compact_brief: at most 100 characters, preserving the task. '
        'primary_user: at most 56 characters. All other strings: at most 700 characters. '
        'required_patterns and deliverables: 1 to 6 short items each. '
        'Do not include line breaks, HTML, URLs, durations, or invented research findings. '
        'Everyday UX: ask the reader to notice a real usability problem, explain its impact, and redesign it. '
        'Dark Patterns: ask the reader to examine pressured choices and propose honest alternatives. '
        'Never assert a named company uses a dark pattern. Do not give the exercise solution. '
        'Choose a relevant visual_key from the schema. ai_capability may be empty. '
        'Keep category-specific substance in the full problem, constraint, and interview_focus. '
        'Avoid these recent headlines: ' + '; '.join(recent)
    )
    body = {'model': MODEL, 'store': False, 'input': guidance,
            'reasoning': {'effort': 'low'}, 'max_output_tokens': MAX_OUTPUT_TOKENS,
            'text': {'format': {'type': 'json_schema', 'name': 'design_drills', 'strict': True,
                                'schema': response_schema()}}}
    # Conservative byte ceiling counts the whole schema/envelope as well as input.
    # UTF-8 bytes upper-bound text BPE token count; leave room for API framing.
    if len(json.dumps(body, ensure_ascii=False).encode('utf-8')) > MAX_INPUT_TOKENS - 1024:
        raise ValueError('Request exceeds the conservative input-token budget')
    return body


def parse_response(response):
    if response.get('status') != 'completed':
        raise ValueError('API response was incomplete')
    chunks = []
    for item in response.get('output', []):
        for part in item.get('content', []):
            if part.get('type') == 'refusal':
                raise ValueError('API declined the generation request')
            if part.get('type') == 'output_text':
                chunks.append(part.get('text', ''))
    payload = json.loads(''.join(chunks))
    if not isinstance(payload, dict) or not isinstance(payload.get('prompts'), list) or len(payload['prompts']) != 9:
        raise ValueError('Expected exactly nine candidate prompts')
    return payload['prompts']


def request_openai(body, api_key):
    request = Request('https://api.openai.com/v1/responses', data=json.dumps(body).encode(),
                      headers={'Authorization': 'Bearer ' + api_key, 'Content-Type': 'application/json'})
    with urlopen(request, timeout=90) as response:
        return json.load(response)


def render_candidates(cards):
    """Use the actual browser renderer; no acceptance on an unavailable renderer."""
    if not cards:
        return {}
    node = os.environ.get('DDD_NODE') or shutil.which('node')
    if not node:
        raise RuntimeError('Node.js is required for the rendered-fit gate. Run npm install first.')
    runtime = ROOT / '.runtime'
    runtime.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=runtime) as directory:
        target = Path(directory) / 'candidates.json'
        target.write_text(json.dumps({'prompts': cards}), encoding='utf-8')
        result = subprocess.run([node, str(ROOT / 'scripts/browser_check.cjs'), '--input', str(target)],
                                cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=180)
        if result.returncode not in (0, 1):
            raise RuntimeError('Rendered-fit check could not run; no candidates accepted')
        report = json.loads(result.stdout)
        if report['errors']:
            raise RuntimeError('Renderer reported errors; no candidates accepted')
        return {p['id']: p for p in report['results']}


def reserve_request(state, batch_key, month):
    batch = state['batches'].setdefault(batch_key, {'attempts': 0, 'accepted_ids': [], 'categories': []})
    usage = state['usage'].setdefault(month, {'requests': 0, 'input_tokens': 0, 'output_tokens': 0})
    if batch['attempts'] >= MAX_REQUESTS_BATCH or usage['requests'] >= MAX_REQUESTS_MONTH:
        return False
    # Reserve before sending. Timeouts may still be billed, so never refund a request.
    batch['attempts'] += 1
    usage['requests'] += 1
    return True


def generate(store, curated, day, transport, gate=render_candidates, mock=False):
    state = store.read()
    iso = day.isocalendar()
    batch_key = f'{"mock" if mock else "live"}-{iso.year}-W{iso.week:02}'
    month = day.strftime('%Y-%m')
    batch = state['batches'].setdefault(batch_key, {'attempts': 0, 'accepted_ids': [], 'categories': []})
    report = {'batch': batch_key, 'accepted': [], 'rejected': [], 'errors': [], 'requests': 0}
    if len(batch['categories']) == 9:
        report['status'] = 'already_complete'
        return report
    for _ in range(MAX_REQUESTS_BATCH):
        if mock:
            if batch['attempts'] >= 1:
                break
            batch['attempts'] += 1
        elif not reserve_request(state, batch_key, month):
            break
        store.write(state)
        try:
            body = make_request(curated + state['generated'])
            report['requests'] += 0 if mock else 1
            response = transport(body)
            if not mock:
                usage = response.get('usage', {})
                state['usage'][month]['input_tokens'] += usage.get('input_tokens', 0)
                state['usage'][month]['output_tokens'] += usage.get('output_tokens', 0)
                store.write(state)
            candidates = parse_response(response)
            valid = []
            categories = set(batch['categories'])
            for card in candidates:
                try:
                    validate_card(card, curated + state['generated'] + valid)
                    if card['mode'] in categories:
                        raise ValueError('Category already present in this batch')
                    clean = {k: card[k] for k in (*TEXT_FIELDS, *LIST_FIELDS)}
                    clean.update(id=content_id(clean), provenance={'source': 'mock' if mock else 'generated',
                                 'model': 'fixture' if mock else MODEL, 'generated_at': day.isoformat(), 'batch': batch_key})
                    valid.append(clean)
                    categories.add(clean['mode'])
                except (ValueError, KeyError, TypeError) as error:
                    report['rejected'].append(str(error))
            fit = gate(valid)
            for card in valid:
                result = fit.get(card['id'], {})
                if not result.get('accepted'):
                    report['rejected'].append(f'{card["id"]}: does not fit supported layouts')
                    continue
                card['render_layout'] = result['render_layout']
                state['generated'].append(card)
                batch['categories'].append(card['mode'])
                batch['accepted_ids'].append(card['id'])
                report['accepted'].append(card['id'])
            store.write(state)
            if len(batch['categories']) == 9:
                break
        except (ValueError, TypeError, KeyError, OSError, RuntimeError, subprocess.SubprocessError) as error:
            # No raw request/response or credentials in console output.
            report['errors'].append(type(error).__name__ + ': generation unavailable; saved deck remains active')
            store.write(state)
    report['status'] = 'saved' if report['accepted'] else 'fallback'
    return report


def load_local_key():
    if os.environ.get('OPENAI_API_KEY'):
        return os.environ['OPENAI_API_KEY']
    env = ROOT / '.env'
    if env.exists():
        for line in env.read_text(encoding='utf-8').splitlines():
            if line.strip().startswith('OPENAI_API_KEY='):
                return line.split('=', 1)[1].strip().strip('"\'')
    return ''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--mock', action='store_true')
    mode.add_argument('--live', action='store_true')
    args = parser.parse_args()
    key = load_local_key() if args.live else ''
    if args.live and not key:
        print('No OPENAI_API_KEY configured. No request made; the offline deck remains available.')
        return 0
    store = JsonStateStore(ROOT / '.runtime' / ('mock-state.json' if args.mock else 'state.json'))
    if args.mock:
        fixture = json.loads((ROOT / 'tests/fixtures/generation.json').read_text(encoding='utf-8'))
        transport = lambda body: {'status': 'completed', 'output': [{'content': [{'type': 'output_text', 'text': json.dumps(fixture)}]}]}
    else:
        transport = lambda body: request_openai(body, key)
    with store.locked():
        report = generate(store, load_prompts(), resolve_date(None), transport, mock=args.mock)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
