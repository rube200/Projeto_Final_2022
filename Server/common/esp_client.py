from os import environ, path, makedirs
from selectors import BaseSelector
from socket import socket
from time import monotonic
from typing import Tuple

from werkzeug.utils import secure_filename

from common.esp_events import EspEvents
from common.notification_type import NotificationType
from socket_client.client_record import ClientRecord
from socket_client.client_socket import ClientSocket


class EspClient(ClientSocket, ClientRecord):
    def __init__(self, address: Tuple[str, int], selector: BaseSelector, tcp_socket: socket, events: EspEvents):
        ClientSocket.__init__(self, address, selector, tcp_socket)
        ClientRecord.__init__(self, lambda: self._camera)

        self.__events = events
        self.__events.on_open_doorbell_requested += self.__on_open_doorbell_requested
        self.__events.on_start_stream_requested += self.on_start_stream_requested
        self.__events.on_stop_stream_requested += self.on_stop_stream_requested

        self.__config_bell_duration = 0.0
        self.__config_motion_duration = 0.0
        self.__esp_files_path = environ.get('ESP_FILES_PATH') or './esp_files'
        if not path.exists(self.__esp_files_path):
            makedirs(self.__esp_files_path)
        self.__esp_to_save_paths = []
        self.__stream_requests = 0

    def __del__(self):
        ClientSocket.__del__(self)
        ClientRecord.__del__(self)
        self.__events.on_stop_stream_requested -= self.on_stop_stream_requested
        self.__events.on_start_stream_requested -= self.on_start_stream_requested
        self.__events.on_open_doorbell_requested -= self.__on_open_doorbell_requested
        self.__events = None
        del self.__config_bell_duration
        del self.__config_motion_duration
        del self.__esp_files_path
        del self.__esp_to_save_paths
        del self.__stream_requests

    def _process_uuid(self, data: bytes) -> None:
        super(EspClient, self)._process_uuid(data)
        config = self.__events.on_esp_uuid_recv(self)
        if not config:
            return

        self.__wait_username = config[0]
        self.__config_bell_duration = (config[1] / 1000.0)
        self.__config_motion_duration = (config[2] / 1000.0)
        self._send_config(config)

    def _process_username(self, data: bytes) -> None:
        username = data.decode('utf-8')
        is_valid = self.__events.on_esp_username_recv(self, username)
        self._send_username_confirmation(is_valid)

    def _process_camera(self, data: bytes) -> None:
        super(EspClient, self)._process_camera(data)
        while self.__esp_to_save_paths:
            filepath = self.__esp_to_save_paths.pop()
            with open(filepath, 'wb') as f:
                f.write(data)

    def __prepare_and_notify(self, notification_type: NotificationType, duration: float) -> None:
        time = monotonic()
        if duration > 0.0:
            filepath = path.join(self.__esp_files_path, secure_filename(f'{time}.mp4'))
            filepath = self.start_record(filepath, time + duration)
        else:
            filepath = path.join(self.__esp_files_path, secure_filename(f'{time}.jpeg'))
            self.__esp_to_save_paths.append(filepath)
        self.__events.on_notification(self, notification_type, filepath)

    def _process_bell_pressed(self) -> None:
        self.__prepare_and_notify(NotificationType.Bell, self.__config_bell_duration)

    def _process_motion_detected(self) -> None:
        self.__prepare_and_notify(NotificationType.Movement, self.__config_motion_duration)

    def __on_open_doorbell_requested(self, uuid: int) -> None:
        if uuid == self._uuid:
            self._send_open_relay()

    def on_start_stream_requested(self, uuid: int, is_maintain_stream: bool) -> None:
        if uuid != self._uuid:
            return

        if is_maintain_stream:
            self._send_start_stream()
            return

        self.__stream_requests += 1
        if self.__stream_requests == 1:
            self._send_start_stream()

    def on_stop_stream_requested(self, uuid: int) -> None:
        if uuid != self._uuid:
            return

        self.__stream_requests -= 1
        if self.__stream_requests == 0:
            self._send_stop_stream()
            return
