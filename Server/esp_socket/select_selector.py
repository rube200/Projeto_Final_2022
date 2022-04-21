import sys
from selectors import SelectSelector, EVENT_READ, EVENT_WRITE

import select

EVENT_EXCEPTION = (1 << 2)


def _select(r, w, x, timeout=None):
    r, w, x = select.select(r, w, x, timeout)
    return r, w, x


class SelectSelectorMod(SelectSelector):
    def __init__(self):
        super().__init__()
        self._exceptions = set()

    def register(self, fn, events, data=None):
        key = super().register(fn, events, data)
        if events & EVENT_EXCEPTION:
            self._exceptions.add(key.fd)
        return key

    def unregister(self, fn):
        key = super().unregister(fn)
        self._exceptions.discard(key.fd)
        return key

    if sys.platform != 'win32':
        _select = select.select

    def select(self, timeout=None):
        timeout = None if timeout is None else max(timeout, 0)
        ready = []

        try:
            # noinspection PyUnresolvedReferences
            r, w, x = self._select(self._readers, self._writers, self._exceptions, timeout)
        except InterruptedError:
            return ready

        r = set(r)
        w = set(w)
        x = set(x)
        for fd in r | w | x:
            events = 0
            if fd in r:
                events |= EVENT_READ
            if fd in w:
                events |= EVENT_WRITE
            if fd in x:
                events |= EVENT_EXCEPTION
            # noinspection PyUnresolvedReferences
            key = self._key_from_fd(fd)
            if key:
                ready.append((key, events & key.events))
        return ready
