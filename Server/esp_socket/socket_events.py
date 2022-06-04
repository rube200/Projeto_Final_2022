from events import Events


class SocketEvents(Events):
    def __init__(self):
        events = (
            'on_esp_uuid_recv',
            'on_esp_username_recv',
            'on_bell_pressed',
            'on_motion_detected',
            'on_open_relay_requested'
        )
        super(SocketEvents, self).__init__(events)
