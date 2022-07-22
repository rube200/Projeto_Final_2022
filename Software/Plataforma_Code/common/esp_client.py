from os import path, environ
from socket import socket
from time import monotonic, time
from typing import Tuple

from werkzeug.utils import secure_filename

from common.alert_type import AlertType
from common.esp_events import EspEvents
from socket_client.client_record import ClientRecord
from socket_client.client_socket import ClientSocket


class EspClient(ClientSocket, ClientRecord):
    def __init__(self, address: Tuple[str, int], tcp_socket: socket, events: EspEvents):
        ClientSocket.__init__(self, address, tcp_socket)
        ClientRecord.__init__(self, lambda: self._not_rotate_frame)
        self.__events = events
        self.__config_bell_duration = 0.0
        self.__config_motion_duration = 0.0
        self.__esp_files_path = environ.get('ESP_FILES_DIR')
        self.__esp_to_save_paths = {}
        self.__stream_requests = 0

    def close(self):
        if not self.__events:
            return

        self.__events = None
        ClientSocket.close(self)
        ClientRecord.close(self)

        del self.__config_bell_duration
        del self.__config_motion_duration
        del self.__esp_files_path
        del self.__esp_to_save_paths
        del self.__stream_requests

    def request_close(self):
        if self.__events.on_esp_disconnect(self):
            return
        self.close()

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
        username = data[:-1].decode('utf-8')
        relay = data[-1]
        is_valid = self.__events.on_esp_username_recv(self, username, relay)
        self._send_username_confirmation(is_valid)

    def _process_camera(self, data: bytes) -> None:
        super(EspClient, self)._process_camera(data)

        while self.__esp_to_save_paths:
            filename, (alert_type, alert_time) = self.__esp_to_save_paths.popitem()
            if alert_type is AlertType.Bell:
                save_img = self.__config_bell_duration <= 0.0
            else:
                save_img = self.__config_motion_duration <= 0.0
            if save_img:
                self.save_picture(filename, self.camera)

            self.__events.on_alert(self.uuid, alert_type,
                                   {'filename': filename, 'image': self.camera, 'time': alert_time})

    def __prepare_and_notify(self, alert_type: AlertType, duration: float) -> None:
        alert_time = time()
        if duration > 0.0:
            filepath = path.join(self.__esp_files_path, secure_filename(f'{alert_time}.webm'))
            filepath = self.start_record(filepath, monotonic() + duration)
            if not filepath:
                return

            filename = path.basename(filepath)
        else:
            filename = secure_filename(f'{alert_time}.jpeg')

        self.__esp_to_save_paths[filename] = (alert_type, alert_time)

    def _process_bell_pressed(self) -> None:
        self.__prepare_and_notify(AlertType.Bell, self.__config_bell_duration)

    def _process_motion_detected(self) -> None:
        self.__prepare_and_notify(AlertType.Movement, self.__config_motion_duration)

    def start_stream(self, is_maintain_stream: bool):
        if is_maintain_stream:
            self._send_start_stream()
            return

        self.__stream_requests += 1
        if self.__stream_requests == 1:
            self._send_start_stream()

    def stop_stream(self):
        self.__stream_requests -= 1
        if self.__stream_requests == 0:
            self._send_stop_stream()

    def open_doorbell(self) -> Tuple[bytes or None, str]:
        self._send_open_relay()
        return self.save_picture()

    def save_picture(self, filename: str = None, image: bytes = None) -> Tuple[bytes or None, str]:
        filename = filename or secure_filename(f'{time()}.jpeg')
        image = image or self._camera
        if not image:
            return None, filename

        filepath = path.join(self.__esp_files_path, filename)
        with open(filepath, 'wb') as f:
            f.write(image)

        return image, filename
