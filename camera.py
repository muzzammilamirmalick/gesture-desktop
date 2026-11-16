"""Reads the webcam on its own thread so the app always gets the newest frame.

Without this, OpenCV can hand back frames that have been waiting in a queue,
which shows up as lag between your hand and the cursor.
"""

import threading

import time

import cv2

from fps import FpsCounter


class Camera:
    def __init__(self, index, width, height, fps=60):
        self.capture = cv2.VideoCapture(index)
        # Most webcams only do 720p at 60 fps (or even 30) in MJPG, so ask for it.
        self.capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.capture.set(cv2.CAP_PROP_FPS, fps)
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.rate = FpsCounter()
        self.fps = 0.0  # what the webcam really delivers, shown on screen
        self.frame = None
        self.frame_number = 0
        self.running = False
        self.new_frame = threading.Condition()

    def is_open(self):
        return self.capture.isOpened()

    def start(self):
        self.running = True
        threading.Thread(target=self.keep_reading, daemon=True).start()

    def keep_reading(self):
        while self.running:
            ok, frame = self.capture.read()
            with self.new_frame:
                if not ok:
                    self.running = False
                else:
                    self.frame = frame
                    self.frame_number += 1
                    self.fps = self.rate.tick(time.monotonic())
                self.new_frame.notify_all()

    def latest(self):
        """Return (frame number, newest frame) straight away, without waiting.

        The number goes up with every new frame, so the caller can tell when
        there is something new to show.
        """
        with self.new_frame:
            return self.frame_number, self.frame

    def stopped(self):
        """True once the camera has stopped sending frames."""
        return not self.running

    def release(self):
        self.running = False
        self.capture.release()
