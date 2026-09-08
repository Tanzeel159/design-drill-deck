import copy
from datetime import date, timedelta
import json
from pathlib import Path
import tempfile
import unittest

from scripts.cards import validate_card, content_id
from scripts.generate_daily import load_prompts
from scripts.generate_prompts import generate, make_request, parse_response, reserve_request
from scripts.local_state import JsonStateStore, MemoryStateStore, empty_state
from scripts.rotation import build_local_payload, next_pick

FIXTURE = json.loads((Path(__file__).parent / 'fixtures/generation.json').read_text(encoding='utf-8'))
TODAY = date(2026, 9, 8)


def response(payload=FIXTURE):
    return {'status': 'completed', 'output': [{'content': [{'type': 'output_text', 'text': json.dumps(payload)}]}],
            'usage': {'input_tokens': 100, 'output_tokens': 300}}


def passing_gate(cards):
    return {c['id']: {'accepted': True, 'render_layout': 'visual'} for c in cards}


class CardContractTests(unittest.TestCase):
    def test_entire_offline_bank_validates(self):
        cards = load_prompts()
        self.assertEqual(len(cards), 54)
        self.assertEqual(sum(p['mode'] == 'Everyday UX' for p in cards), 6)
        self.assertEqual(sum(p['mode'] == 'Dark Patterns' for p in cards), 6)
        for card in cards:
            validate_card(card)

    def test_duplicate_and_near_duplicate(self):
        card = copy.deepcopy(FIXTURE['prompts'][0])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            validate_card(card, [card])
        card['display_brief'] += ' Now.'
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            validate_card(card, [FIXTURE['prompts'][0]])

    def test_invalid_text_visual_category_and_lengths(self):
        for key, value in [('display_title', '<script>'), ('display_title', 'x' * 43),
                           ('display_brief', 'Something interesting.'), ('compact_brief', 'x' * 101),
                           ('visual_key', 'made-up'), ('mode', 'made-up'), ('primary_user', 3),
                           ('required_patterns', ['<img src=x>'])]:
            with self.subTest(key=key, value=value):
                card = {**FIXTURE['prompts'][0], key: value}
                with self.assertRaises(ValueError):
                    validate_card(card)

    def test_request_is_bounded_and_structured(self):
        body = make_request(load_prompts())
        self.assertEqual(body['model'], 'gpt-5-mini')
        self.assertEqual(body['max_output_tokens'], 12000)
        self.assertTrue(body['text']['format']['strict'])
        self.assertLessEqual(len(json.dumps(body, ensure_ascii=False).encode()), 6976)
        self.assertFalse(body['store'])

    def test_incomplete_refused_and_malformed_responses(self):
        responses = [dict(status='incomplete'),
                     {'status': 'completed', 'output': [{'content': [{'type': 'refusal'}]}]},
                     {'status': 'completed', 'output': [{'content': [{'type': 'output_text', 'text': 'bad json'}]}]},
                     response({'prompts': []})]
        for payload in responses:
            with self.assertRaises(ValueError):
                parse_response(payload)


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStateStore()
        self.curated = load_prompts()

    def test_complete_batch_saved_once_and_rerun_is_free(self):
        calls = []
        def transport(body):
            calls.append(body)
            return response()
        first = generate(self.store, self.curated, TODAY, transport, passing_gate)
        second = generate(self.store, self.curated, TODAY, transport, passing_gate)
        self.assertEqual(len(first['accepted']), 9)
        self.assertEqual(second['status'], 'already_complete')
        self.assertEqual(len(calls), 1)
        state = self.store.read()
        self.assertEqual(state['usage']['2026-09']['requests'], 1)
        self.assertEqual(state['usage']['2026-09']['output_tokens'], 300)

    def test_timeout_and_rate_limit_consume_at_most_two_requests(self):
        for error in (TimeoutError(), OSError('HTTP 429')):
            store = MemoryStateStore()
            def fail(body):
                raise error
            report = generate(store, self.curated, TODAY, fail, passing_gate)
            self.assertEqual(report['requests'], 2)
            self.assertEqual(report['status'], 'fallback')
            self.assertEqual(store.read()['usage']['2026-09']['requests'], 2)
            self.assertFalse(store.read()['generated'])
            self.assertEqual(generate(store, self.curated, TODAY, fail, passing_gate)['requests'], 0)

    def test_monthly_limit_survives_new_batches(self):
        state = self.store.read()
        for i in range(5):
            for _ in range(2):
                self.assertTrue(reserve_request(state, f'batch-{i}', '2026-09'))
        self.assertFalse(reserve_request(state, 'new-batch', '2026-09'))
        self.assertTrue(reserve_request(state, 'oct-batch', '2026-10'))

    def test_render_gate_is_required(self):
        report = generate(self.store, self.curated, TODAY, lambda b: response(), lambda cards: {})
        self.assertEqual(report['status'], 'fallback')
        self.assertFalse(self.store.read()['generated'])

    def test_gate_failure_does_not_replace_saved_cards(self):
        state = self.store.read()
        state['generated'] = [{**FIXTURE['prompts'][0], 'id': 'saved-existing', 'provenance': {'source':'generated'}}]
        self.store.write(state)
        def broken(cards):
            raise RuntimeError('Browser unavailable')
        generate(self.store, self.curated, TODAY, lambda b: response(), broken)
        self.assertEqual([p['id'] for p in self.store.read()['generated']], ['saved-existing'])

    def test_partial_batch_keeps_valid_candidates(self):
        payload = copy.deepcopy(FIXTURE)
        payload['prompts'][0]['visual_key'] = 'bad'
        report = generate(self.store, self.curated, TODAY, lambda b: response(payload), passing_gate)
        self.assertEqual(len(report['accepted']), 8)
        self.assertEqual(len(self.store.read()['generated']), 8)

    def test_mock_does_not_spend(self):
        generate(self.store, self.curated, TODAY, lambda b: response(), passing_gate, mock=True)
        self.assertEqual(self.store.read()['usage'], {})
        self.assertTrue(all(p['provenance']['source'] == 'mock' for p in self.store.read()['generated']))


class PersistentRotationTests(unittest.TestCase):
    def setUp(self):
        self.curated = load_prompts()

    def test_generated_first_then_curated_without_repeats(self):
        cards = self.curated[:6]
        generated = [{**FIXTURE['prompts'][0], 'id': 'generated-one'}]
        for mode in ('smart_shuffle', 'sequential'):
            state = empty_state()
            picks = [next_pick(state, cards, generated, 'all', mode, 'intermediate', str(TODAY + timedelta(days=i)))['prompt_id'] for i in range(8)]
            self.assertEqual(picks[0], 'generated-one')
            self.assertEqual(set(picks[1:7]), {c['id'] for c in cards})
            self.assertNotEqual(picks[6], picks[7])

    def test_saved_same_day_pick_does_not_change_with_new_batch(self):
        state = empty_state()
        first = next_pick(state, self.curated, [], 'all', 'smart_shuffle', 'intermediate', str(TODAY))
        generated = [{**FIXTURE['prompts'][0], 'id': 'fresh'}]
        again = next_pick(state, self.curated, generated, 'all', 'smart_shuffle', 'intermediate', str(TODAY))
        self.assertEqual(first, again)
        tomorrow = next_pick(state, self.curated, generated, 'all', 'smart_shuffle', 'intermediate', str(TODAY + timedelta(days=1)))
        self.assertEqual(tomorrow['prompt_id'], 'fresh')

    def test_focus_and_offline_source_are_independent(self):
        store = MemoryStateStore()
        state = store.read()
        state['generated'] = [{**FIXTURE['prompts'][0], 'id':'fresh', 'provenance':{'source':'generated'}}]
        store.write(state)
        auto = build_local_payload(self.curated, store, TODAY)
        offline = build_local_payload(self.curated, store, TODAY, 'curated')
        self.assertEqual(auto['daily_picks']['smart_shuffle']['core_ux_flow']['intermediate']['prompt_id'], 'fresh')
        self.assertTrue(offline['daily_picks']['smart_shuffle']['core_ux_flow']['intermediate']['prompt_id'].startswith('ddd-'))
        self.assertTrue(auto['daily_picks']['smart_shuffle']['dark_patterns']['intermediate']['prompt_id'].startswith('ddd-'))
        self.assertEqual(auto, build_local_payload(self.curated, store, TODAY))

    def test_disk_state_and_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            store = JsonStateStore(Path(folder) / 'state.json')
            with store.locked():
                first = build_local_payload(self.curated, store, date(2026,12,31))
                with self.assertRaises(RuntimeError):
                    with store.locked():
                        pass
            reopened = JsonStateStore(store.path)
            again = build_local_payload(self.curated, reopened, date(2026,12,31))
            self.assertEqual(first, again)
            nxt = build_local_payload(self.curated, reopened, date(2027,1,1))
            self.assertNotEqual(first['daily_picks']['smart_shuffle']['all'], nxt['daily_picks']['smart_shuffle']['all'])
            self.assertFalse(store.path.with_suffix('.lock').exists())

    def test_corrupt_state_is_not_silently_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'state.json'
            path.write_text('{broken', encoding='utf-8')
            with self.assertRaises(ValueError):
                JsonStateStore(path).read()
            self.assertEqual(path.read_text(), '{broken')


if __name__ == '__main__':
    unittest.main()
