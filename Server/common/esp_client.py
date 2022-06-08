from selectors import BaseSelector
from socket import socket
from time import monotonic
from typing import Tuple

from socket_common.socket_events import SocketEvents

from common.notification_type import NotificationType
from socket_client.client_record import ClientRecord
from socket_client.client_socket import ClientSocket


class EspClient(ClientSocket, ClientRecord):
    def __init__(self, address: Tuple[str, int], selector: BaseSelector, tcp_socket: socket, events: SocketEvents):
        ClientSocket.__init__(self, address, selector, tcp_socket)
        ClientRecord.__init__(self, lambda: self.__camera)

        self.__events = events
        self.__events.on_camera_requested += self.__on_camera_requested
        self.__events.on_open_doorbell_requested += self.__on_open_doorbell_requested
        self.__events.on_start_stream_requested += self.on_start_stream_requested
        self.__events.on_stop_stream_requested += self.on_stop_stream_requested

        self.__config_bell_duration = 0.0
        self.__config_motion_duration = 0.0
        self.__stream_requests = 0

    def __del__(self):
        ClientSocket.__del__(self)
        ClientRecord.__del__(self)
        self.__events.on_stop_stream_requested -= self.on_stop_stream_requested
        self.__events.on_start_stream_requested -= self.on_start_stream_requested
        self.__events.on_open_doorbell_requested -= self.__on_open_doorbell_requested
        self.__events.on_camera_requested -= self.__on_camera_requested
        self.__events = None
        del self.__config_bell_duration
        del self.__config_motion_duration
        del self.__stream_requests

    def __process_uuid(self, data: bytes) -> None:
        super(EspClient, self).__process_uuid(data)
        config = self.__events.on_esp_uuid_recv(self)
        if not config:
            return

        self.__wait_username = config[0]
        self.__config_bell_duration = (config[1] / 1000.0)
        self.__config_motion_duration = (config[2] / 1000.0)
        self.__send_config(config)

    def __process_username(self, data: bytes) -> None:
        username = data.decode('utf-8')
        is_valid = self.__events.on_esp_username_recv(self, username)
        self.__send_username_confirmation(is_valid)

    def __process_bell_pressed(self) -> None:
        time = monotonic()
        path = self.start_record(f'{time}.mp4', time + self.__config_bell_duration)
        self.__events.on_notification(self, NotificationType.Bell, path)

    def __process_motion_detected(self) -> None:
        time = monotonic()
        path = self.start_record(f'{time}.mp4', time + self.__config_motion_duration)
        self.__events.on_notification(self, NotificationType.Movement, path)

    def __on_camera_requested(self, uuid: int) -> bytes or None:
        if uuid is self.__uuid:
            return self.camera
        return None

    def __on_open_doorbell_requested(self, uuid: int) -> None:
        if uuid is self.__uuid:
            self.__send_open_relay()

    def on_start_stream_requested(self, uuid: int, is_maintain_stream: bool) -> None:
        if uuid is not self.__uuid:
            return

        if is_maintain_stream:
            self.__send_start_stream()
            return

        self.__stream_requests += 1
        if self.__stream_requests is 1:
            self.__send_start_stream()

    def on_stop_stream_requested(self, uuid: int) -> None:
        if uuid is not self.__uuid:
            return

        self.__stream_requests -= 1
        if self.__stream_requests is 0:
            self.__send_stop_stream()
            return
