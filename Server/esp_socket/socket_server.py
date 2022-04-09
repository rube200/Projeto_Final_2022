import logging as log
from selectors import DefaultSelector, EVENT_READ
from socketserver import ThreadingTCPServer

from flup.server.threadpool import ThreadPool

from socket_client import Address, PacketType, SocketClient, wrap_try_except


class SocketServer(ThreadingTCPServer):
    def __init__(self, host_address: Address, debug: bool = False):
        super().__init__(host_address, )
        self._host_address = host_address
        self._selector = DefaultSelector()
        self._threadPool = ThreadPool
        log.basicConfig(filename='socket.log', level=log.DEBUG if debug else log.WARNING)

    def __enter__(self):
        self.setup_server()

    def setup_server(self):
        self.bind(self._host_address)
        self.listen()
        self.setblocking(False)

        self._selector.register(self, EVENT_READ)
        log.info('Socket ready! Waiting connections...')

    def process_server(self, infinite_loop: bool = True):
        if not infinite_loop:
            self._process_server()
            return

        while True:
            self._process_server()

    def _process_server(self):
        events = self._selector.select()
        for key, mask in events:
            if not key.data:
                wrap_try_except(self._accept_client, 'Exception while accepting new client')
                return

            data: SocketClient = key.data
            wrap_try_except(lambda: data.process_events(mask), f'Exception while processing event for {data.address}',
                            lambda: data.close)

    def _accept_client(self):
        connection, address = self.accept()
        log.info(f'Accepted a connection from {address}')

        connection.setblocking(False)
        message = SocketClient(self._selector, connection, address, self._process_packet)
        self._selector.register(connection, EVENT_READ, data=message)

    def _process_packet(self, packet_type: PacketType, data: bytes):
        if packet_type is PacketType.RAW:
            print('Raw')
        elif packet_type is PacketType.STATE:
            print('State')
        elif packet_type is PacketType.IMAGE:
            print('Image')
            with open('test.jpeg', 'wb') as f:
                f.write(data)
        else:
            print('None')
