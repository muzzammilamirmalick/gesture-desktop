"""Reads the webcam on its own thread so the app always gets the newest frame.

Without this, OpenCV can hand back frames that have been waiting in a queue,
which shows up as lag between your hand and the cursor.
"""

import threading

import cv2


class Camera:
    def __init__(self, index, width, height):
        self.capture = cv2.VideoCapture(index)
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
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
                self.new_frame.notify_all()

    def read(self, last_number, timeout=1.0):
        """Wait for a frame newer than last_number. Returns (number, frame)."""
        with self.new_frame:
            self.new_frame.wait_for(
                lambda: self.frame_number > last_number or not self.running, timeout
            )
            if self.frame_number <= last_number:
                return last_number, None
            return self.frame_number, self.frame

    def release(self):
        self.running = False
        self.capture.release()
