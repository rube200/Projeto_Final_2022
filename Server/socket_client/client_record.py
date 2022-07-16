import logging as log
from threading import Thread, Event
from time import monotonic, sleep
from traceback import format_exc
from typing import Callable

import numpy
# noinspection PyProtectedMember, PyUnresolvedReferences
from cv2 import imdecode, IMREAD_COLOR, rotate, ROTATE_90_CLOCKWISE, VideoWriter, VideoWriter_fourcc

FOURCC = VideoWriter_fourcc(*'AV10')


class ClientRecord(Thread):
    def __init__(self, get_frame_no_rotate: Callable[[], bytes]):
        super(ClientRecord, self).__init__()
        self.__get_frame_no_rotate = get_frame_no_rotate
        self.__interval = 0.05
        self.__record_until = 0.0
        self.__reset = Event()
        self.__running = False
        self.__video_writer = None
        self.__video_name = None
        self.__waiter = Event()
        self.__working = False

    def close(self):
        self.stop()
        sleep(0.01)
        del self.__get_frame_no_rotate
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
        self.__video_writer = VideoWriter(name, FOURCC, 20, (240, 320))

        if self.__running:
            self.__waiter.clear()
            self.__reset.set()
            self.__reset.clear()
            return self.__video_name

        self.__running = True
        self.start()
        return self.__video_name

    def __take_frame(self):
        if not self.__video_writer:
            self.__working = False
            return

        frame = self.__get_frame_no_rotate()
        if frame:
            np_img = numpy.frombuffer(frame, dtype=numpy.uint8)
            # noinspection PyUnresolvedReferences
            img = imdecode(np_img, IMREAD_COLOR)
            # noinspection PyUnresolvedReferences
            img = rotate(img, ROTATE_90_CLOCKWISE)

            self.__video_writer.write(img)

    def __process_record(self):
        try:
            self.__working = True
            while self.__working:
                start = monotonic()
                self.__take_frame()
                end = monotonic()

                interval = max(0.0, self.__interval + start - end)
                if self.__waiter.wait(interval) or self.__record_until < monotonic():
                    break

            if self.__video_writer:
                self.__video_writer.release()

        except Exception as ex:
            log.error(f'Exception while recording {self.__video_name}: {ex!r}')
            log.error(format_exc())
            if self.__video_writer:
                self.__video_writer.release()

        finally:
            self.__video_writer = None
            self.__video_name = None
            self.__working = False

    def run(self):
        while self.__running:
            self.__process_record()
            self.__reset.wait()

    def stop(self):
        self.__running = False
        self.__working = False
        self.__reset.set()
        self.__waiter.set()
