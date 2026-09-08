"""Atomic local state storage. No credentials or provider requests are persisted."""
import copy
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Protocol


def empty_state():
    return {'version': 1, 'generated': [], 'batches': {}, 'usage': {}, 'queues': {}, 'picks': {}}


class StateStore(Protocol):
    def read(self) -> dict: ...
    def write(self, state: dict) -> None: ...


class JsonStateStore:
    def __init__(self, path):
        self.path = Path(path)

    def read(self):
        if not self.path.exists():
            return empty_state()
        state = json.loads(self.path.read_text(encoding='utf-8'))
        if state.get('version') != 1:
            raise ValueError('Unsupported local state version')
        for key in empty_state():
            if key not in state:
                raise ValueError(f'Local state is missing {key}')
        return state

    def write(self, state):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(dir=self.path.parent, suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                json.dump(state, handle, ensure_ascii=False, indent=2)
                handle.write('\n')
            os.replace(temp, self.path)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)

    @contextmanager
    def locked(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock = self.path.with_suffix('.lock')
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise RuntimeError('Local state is busy. Retry after the other operation finishes.') from exc
        try:
            os.close(fd)
            yield self
        finally:
            lock.unlink(missing_ok=True)


class MemoryStateStore:
    def __init__(self):
        self.state = empty_state()

    def read(self):
        return copy.deepcopy(self.state)

    def write(self, state):
        self.state = copy.deepcopy(state)
