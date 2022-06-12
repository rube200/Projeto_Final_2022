from threading import Thread, Event
from time import monotonic, sleep
from typing import Callable

import numpy
from cv2 import imdecode, IMREAD_COLOR, VideoWriter, VideoWriter_fourcc

FOURCC = VideoWriter_fourcc(*'MP4V')


class ClientRecord(Thread):
    def __init__(self, get_camera: Callable[[], bytes]):
        super(ClientRecord, self).__init__()
        self.__get_camera = get_camera
        self.__interval = 0.05
        self.__record_until = 0.0
        self.__reset = Event()
        self.__running = False
        self.__video_writer = None
        self.__video_name = None
        self.__waiter = Event()
        self.__working = False

    def __del__(self):
        self.stop()
        sleep(0.01)
        del self.__get_camera
        del self.__interval
        del self.__record_until
        del self.__reset
        del self.__video_name
        del self.__video_writer
        del self.__waiter

    def start_record(self, name: str, record_until: float) -> str or None:
        if self.__working:
            self.__record_until = max(self.__record_until, record_until)
            return self.__video_name

        if not name:
            return self.__video_name

        self.__record_until = record_until
        self.__video_name = name
        self.__video_writer = VideoWriter(name, FOURCC, 20, (320, 240))

        if self.__running:
            self.__waiter.clear()
            self.__reset.set()
            self.__reset.clear()
            return self.__video_name

        self.__running = True
        self.start()
        return self.__video_name

    def __take_frame(self):
        frame = self.__get_camera()
        if frame and self.__video_writer:
            np_img = numpy.frombuffer(frame, dtype=numpy.uint8)
            img = imdecode(np_img, IMREAD_COLOR)
            self.__video_writer.write(img)
            return

        self.__working = False

    def __process_record(self):
        try:
            self.__working = True
            while self.__working:
                if self.__waiter.wait(self.__interval) or self.__record_until < monotonic():
                    break

                self.__take_frame()

            if self.__video_writer:
                self.__video_name = None
                self.__video_writer.release()
                self.__video_writer = None
        finally:
            self.__working = False

    def run(self):
        while self.__running:
            self.__process_record()
            self.__reset.wait()

    def stop(self):
        self.__running = False
        self.__working = False
        self.__waiter.set()
