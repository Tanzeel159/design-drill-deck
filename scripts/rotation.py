"""Stable daily picks: unseen generated cards first, then a curated cycle."""
import hashlib
from scripts.generate_daily import build_payload, build_pools, DIFFICULTY_LEVELS


def ordered(ids, mode, key, cycle):
    if mode == 'sequential':
        return list(ids)
    return sorted(ids, key=lambda value: hashlib.sha256(f'{key}|{cycle}|{value}'.encode()).hexdigest())


def next_pick(state, curated, generated, scope, mode, level, day):
    key = f'{scope}:{mode}:{level}'
    date_key = f'{day}:{key}'
    if date_key in state['picks']:
        return state['picks'][date_key]
    queue = state['queues'].setdefault(key, {'seen_generated': [], 'remaining': [], 'cycle': 0, 'last': None})
    fresh = [p['id'] for p in generated if p['id'] not in queue['seen_generated']]
    if fresh:
        selected = ordered(fresh, mode, key, 0)[0]
        queue['seen_generated'].append(selected)
        source = 'generated'
    else:
        ids = [p['id'] for p in curated]
        queue['remaining'] = [i for i in queue['remaining'] if i in ids]
        if not queue['remaining']:
            queue['remaining'] = ordered(ids, mode, key, queue['cycle'])
            queue['cycle'] += 1
            if len(ids) > 1 and queue['remaining'][0] == queue['last']:
                queue['remaining'][0], queue['remaining'][1] = queue['remaining'][1], queue['remaining'][0]
        if not queue['remaining']:
            raise ValueError('No saved prompts in this category')
        selected = queue['remaining'].pop(0)
        source = 'curated'
    queue['last'] = selected
    all_ids = [p['id'] for p in curated + generated]
    result = {'prompt_id': selected, 'drill_number': all_ids.index(selected) + 1,
              'position': all_ids.index(selected) + 1, 'pool_size': len(all_ids),
              'cycle': queue['cycle'], 'source': source}
    state['picks'][date_key] = result
    return result


def build_local_payload(curated, store, day, source='auto'):
    state = store.read()
    generated = state['generated'] if source != 'curated' else []
    payload = build_payload(curated, day, 'local-preview')
    payload['prompts'] = curated + generated
    pools = build_pools(curated)
    gpools = build_pools(generated)
    # Source namespaces keep inspection of the offline deck from consuming API queues.
    working = dict(state)
    namespace = state.setdefault('source_states', {}).setdefault(source, {'queues': {}, 'picks': {}})
    working.update(namespace)
    for mode in ('smart_shuffle', 'sequential'):
        for scope, cards in pools.items():
            for level in DIFFICULTY_LEVELS:
                payload['daily_picks'][mode][scope][level['key']] = next_pick(
                    working, cards, gpools.get(scope, []), scope, mode, level['key'], day.isoformat())
    for item in payload['scopes']:
        item['count'] += len(gpools.get(item['key'], []))
    state['source_states'][source] = {'queues': working['queues'], 'picks': working['picks']}
    store.write(state)
    payload['local_status'] = {'source': source, 'saved_generated': len(generated), 'offline_cards': len(curated)}
    return payload
