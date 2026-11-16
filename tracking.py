"""Runs MediaPipe detection in the background (LIVE_STREAM mode).

The main loop hands over a frame and carries on straight away. MediaPipe calls
back on its own thread when the result is ready, and the main loop picks up
the newest result whenever it wants it. So the video and the cursor never wait
for the model.
"""

import threading
import time

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode

from fps import FpsCounter

# If a result never comes back (MediaPipe can drop frames), stop waiting after this.
BUSY_TIMEOUT_SECONDS = 0.25


def shrink(frame, width):
    """Scale a frame down for the model. The model only needs a small image."""
    height, current_width = frame.shape[:2]
    if current_width <= width:
        return frame
    return cv2.resize(frame, (width, int(height * width / current_width)), interpolation=cv2.INTER_AREA)


class BackgroundDetector:
    """Shared plumbing: submit frames, keep only the newest result."""

    def __init__(self, model_path, detection_width, use_gpu):
        self.detection_width = detection_width
        self.lock = threading.Lock()
        self.result = None
        self.result_number = 0
        self.busy_since = None
        self.last_timestamp = 0
        self.pending_image = None
        self.rate = FpsCounter()
        self.detect_fps = 0.0
        self.delegate_name, self.model = self.create(model_path, use_gpu)

    def create(self, model_path, use_gpu):
        """Try the GPU first if asked, and fall back to the CPU."""
        if use_gpu:
            try:
                return "GPU", self.build(model_path, BaseOptions.Delegate.GPU)
            except Exception:
                pass  # many builds have no GPU support, the CPU is fine
        return "CPU", self.build(model_path, BaseOptions.Delegate.CPU)

    def build(self, model_path, delegate):
        raise NotImplementedError

    def read(self, result):
        raise NotImplementedError

    def send(self, image, timestamp_ms):
        raise NotImplementedError

    def on_result(self, result, image, timestamp_ms):
        value = self.read(result)
        with self.lock:
            self.result = value
            self.result_number += 1
            self.busy_since = None
            self.detect_fps = self.rate.tick(time.monotonic())

    def is_busy(self, now):
        return self.busy_since is not None and now - self.busy_since < BUSY_TIMEOUT_SECONDS

    def submit(self, frame, now):
        """Send a frame unless the last one is still being worked on. Returns True if sent."""
        with self.lock:
            if self.is_busy(now):
                return False
            self.busy_since = now
        rgb = cv2.cvtColor(shrink(frame, self.detection_width), cv2.COLOR_BGR2RGB)
        # Keep a reference so the image stays alive until MediaPipe is done with it.
        self.pending_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        self.send(self.pending_image, self.next_timestamp(now))
        return True

    def next_timestamp(self, now):
        # MediaPipe needs timestamps that always go up.
        self.last_timestamp = max(self.last_timestamp + 1, int(now * 1000))
        return self.last_timestamp

    def latest(self):
        """Return (result number, newest result). The number goes up with each new result."""
        with self.lock:
            return self.result_number, self.result

    def close(self):
        self.model.close()


class HandTracker(BackgroundDetector):
    def build(self, model_path, delegate):
        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path, delegate=delegate),
            running_mode=RunningMode.LIVE_STREAM,
            num_hands=1,
            result_callback=self.on_result,
        )
        return HandLandmarker.create_from_options(options)

    def read(self, result):
        """The first hand's landmarks as (x, y) pairs, or None."""
        if not result.hand_landmarks:
            return None
        return [(point.x, point.y) for point in result.hand_landmarks[0]]

    def send(self, image, timestamp_ms):
        self.model.detect_async(image, timestamp_ms)

