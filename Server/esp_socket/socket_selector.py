from collections import namedtuple
from collections.abc import Mapping
from math import ceil
from sys import platform
from typing import Any, Tuple

import select
from _socket import SocketType

EVENT_READ = (1 << 0)
EVENT_WRITE = (1 << 1)
EVENT_EXCEPTIONAL = (1 << 2)

SelectorKey = namedtuple('SelectorKey', ['fo', 'fd', 'events', 'data'])


def _fd_from_fo(fo: SocketType) -> int:
    fd = int(fo.fileno())
    if fd < 0:
        raise ValueError(f'Invalid file descriptor: {fd!r}')
    return fd


class BaseSelector(Mapping):
    def __init__(self):
        self._fd_key = {}

    def __len__(self):
        return len(self._fd_key)

    def __getitem__(self, fo: SocketType):
        fd = _fd_from_fo(fo)
        if fd in self._fd_key:
            return self._fd_key.get(fd)
        raise KeyError(f'{fo!r} is not registered') from None

    def __iter__(self):
        return iter(self._fd_key)

    def register(self, fo: SocketType, events: int, data: Any = None) -> SelectorKey:
        if not events or events & ~(EVENT_READ | EVENT_WRITE | EVENT_EXCEPTIONAL):
            raise ValueError(f'Invalid events: {events!r}')

        fd = _fd_from_fo(fo)
        key = SelectorKey(fo, fd, events, data)
        if key.fd in self._fd_key:
            raise KeyError(f'{fo!r} (FD {key.fd!r}) is already registered')

        self._fd_key[key.fd] = key
        return key

    def unregister(self, fo: SocketType) -> SelectorKey:
        fd = _fd_from_fo(fo)
        if fd in self._fd_key:
            return self._fd_key.pop(fd)
        raise KeyError(f'{fo!r} is not registered') from None

    def modify(self, fo: SocketType, events: int, data: Any = None) -> SelectorKey:
        key = self[fo]  # __getitem__
        if events != key.events:
            self.unregister(fo)
            return self.register(fo, events, data)

        if data != key.data:
            # noinspection PyProtectedMember
            key = key._replace(data=data)
            self._fd_key[key.fd] = key
        return key

    def close(self) -> None:
        self._fd_key.clear()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def _select(r, w, x, timeout=None) -> Tuple[list, list, list]:
    r, w, x = select.select(r, w, x, timeout)
    return r, w, x


class NormalSelector(BaseSelector):
    def __init__(self):
        super(NormalSelector, self).__init__()
        self._readers = set()
        self._writers = set()
        self._exceptional = set()

    def register(self, fo: SocketType, events: int, data: Any = None) -> SelectorKey:
        key = super(NormalSelector, self).register(fo, events, data)
        if events & EVENT_READ:
            self._readers.add(key.fd)
        if events & EVENT_WRITE:
            self._writers.add(key.fd)
        if events & EVENT_EXCEPTIONAL:
            self._exceptional.add(key.fd)
        return key

    def unregister(self, fo: SocketType) -> SelectorKey:
        key = super(NormalSelector, self).unregister(fo)
        self._readers.discard(key.fd)
        self._writers.discard(key.fd)
        self._exceptional.discard(key.fd)
        return key

    if platform != 'win32':
        _select = select.select

    def select(self, timeout: float = None) -> list:
        timeout = None if timeout is None else max(timeout, 0)
        ready = []
        try:
            r, w, x = _select(self._readers, self._writers, self._exceptional, timeout)
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
                events |= EVENT_EXCEPTIONAL
            key = self._fd_key.get(fd)
            if key:
                ready.append((key, events & key.events))
        return ready


ServerSelector = NormalSelector

if hasattr(select, 'poll'):
    class PollSelector(BaseSelector):
        _EVENT_READ = select.POLLIN
        _EVENT_WRITE = select.POLLOUT
        _EVENT_EXCEPTIONAL = select.EPOLLRDHUP

        def __init__(self):
            super(PollSelector, self).__init__()
            self._poll = select.poll()

        def register(self, fo: SocketType, events: int, data: Any = None) -> SelectorKey:
            key = super(PollSelector, self).register(fo, events, data)
            poll_events = 0
            if events & EVENT_READ:
                poll_events |= self._EVENT_READ
            if events & EVENT_WRITE:
                poll_events |= self._EVENT_WRITE
            if events & EVENT_EXCEPTIONAL:
                poll_events |= self._EVENT_EXCEPTIONAL
            try:
                self._poll.register(key.fd, poll_events)
            except Exception:
                super(PollSelector, self).unregister(fo)
                raise
            return key

        def unregister(self, fo: SocketType) -> SelectorKey:
            key = super(PollSelector, self).unregister(fo)
            try:
                self._poll.unregister(key.fd)
            except OSError:  # FD closed after register
                pass
            return key

        def modify(self, fo: SocketType, events: int, data: Any = None) -> SelectorKey:
            key = self[fo]  # __getitem__
            if events == key.events and data == key.data:
                return key

            if events != key.events:
                poll_events = 0
                if events & EVENT_READ:
                    poll_events |= self._EVENT_READ
                if events & EVENT_WRITE:
                    poll_events |= self._EVENT_WRITE
                if events & EVENT_EXCEPTIONAL:
                    poll_events |= self._EVENT_EXCEPTIONAL
                try:
                    self._poll.modify(key.fd, poll_events)
                except Exception:
                    super(PollSelector, self).unregister(fo)
                    raise

            # noinspection PyProtectedMember
            key = key._replace(events=events, data=data)
            self._fd_key[key.fd] = key
            return key

        def select(self, timeout: float = None) -> list:
            timeout = None if timeout is None else max(ceil(timeout * 1e3), 0)
            ready = []
            try:
                fd_list = self._poll.poll(timeout)
            except InterruptedError:
                return ready
            for fd, event in fd_list:
                events = 0
                if event & self._EVENT_READ:
                    events |= EVENT_READ
                if event & self._EVENT_WRITE:
                    events |= EVENT_WRITE
                if event & self._EVENT_EXCEPTIONAL:
                    events |= EVENT_EXCEPTIONAL
                key = self._fd_key.get(fd)
                if key:
                    ready.append((key, events & key.events))
            return ready


    ServerSelector = PollSelector
