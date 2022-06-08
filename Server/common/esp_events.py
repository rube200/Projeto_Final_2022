from events import Events


class EspEvents(Events):
    def __init__(self):
        super(EspEvents, self).__init__((
            'on_esp_uuid_recv',  # Client -> (username, bell_duration, motion_duration)
            'on_esp_username_recv',  # Client, username -> bool
            'on_notification',  # Client, NotificationType, Path -> None
            'on_camera_requested',  # uuid -> bytes or None
            'on_open_doorbell_requested',  # uuid -> None
            'on_start_stream_requested',  # uuid, is_maintain_stream -> None
            'on_stop_stream_requested'  # uuid -> None
        ))
