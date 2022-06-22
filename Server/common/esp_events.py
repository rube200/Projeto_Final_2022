from typing import Callable, Any


# Based on events.py
class EventSlot:
    def __init__(self, name):
        self.__name__ = name
        self.funcs = []

    def __repr__(self):
        return f'Event: {self.__name__}'

    def __call__(self, *args, **kwargs):
        for f in list(self.funcs):
            result = f(*args, **kwargs)
            if result:
                return result
        return None

    def __iadd__(self, func: Callable[[Any], Any]):
        self.funcs.append(func)
        return self

    def __isub__(self, func: Callable[[Any], Any]):
        while func in self.funcs:
            self.funcs.remove(func)
        return self

    def __len__(self):
        return len(self.funcs)

    def __iter__(self):
        def gen():
            for func in self.funcs:
                yield func

        return gen()

    def __getitem__(self, key):
        return self.funcs[key]


class EspEvents:
    def __init__(self):
        self.__events__ = (
            'on_esp_uuid_recv',  # Client -> (username, bell_duration, motion_duration)
            'on_esp_username_recv',  # Client, username -> bool
            'on_esp_disconnect',  # Client -> bool
            'on_alert',  # int, AlertType, dict-> None
            'on_open_doorbell_requested',  # uuid -> None
            'on_start_stream_requested',  # uuid, is_maintain_stream -> None
            'on_stop_stream_requested'  # uuid -> None
        )

    def __getattr__(self, name: str):
        if name not in self.__events__:
            raise AttributeError(f'\'{name}\' is not a declared event')

        self.__dict__[name] = ev = EventSlot(name)
        return ev

    def __repr__(self):
        return f'<{self.__class__.__module__}.{self.__class__.__name__} object at {hex(id(self))}>'

    __str__ = __repr__

    def __len__(self):
        return len(list(self.__iter__()))

    def __iter__(self):
        def gen(dic=self.__dict__.items()):
            for attr, val in dic:
                if isinstance(val, EventSlot):
                    yield val

        return gen()
