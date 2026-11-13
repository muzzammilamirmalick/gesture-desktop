"""Webcam window that shows the detected hand and gesture."""

import time

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode

import config
import gestures
import overlay


def create_landmarker():
    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=config.MODEL_PATH),
        running_mode=RunningMode.VIDEO,
        num_hands=1,
    )
    return HandLandmarker.create_from_options(options)


def find_hand(landmarker, frame, timestamp_ms):
    """Return the first hand's landmarks as (x, y) pairs, or None."""
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = landmarker.detect_for_video(image, timestamp_ms)
    if not result.hand_landmarks:
        return None
    return [(point.x, point.y) for point in result.hand_landmarks[0]]


def resize_for_window(frame):
    height, width = frame.shape[:2]
    new_height = int(height * config.WINDOW_WIDTH / width)
    return cv2.resize(frame, (config.WINDOW_WIDTH, new_height))


def window_closed():
    return cv2.getWindowProperty(config.WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1


def main():
    camera = cv2.VideoCapture(config.CAMERA_INDEX)
    if not camera.isOpened():
        print("Could not open the webcam. Check CAMERA_INDEX in config.py.")
        return

    landmarker = create_landmarker()
    cv2.namedWindow(config.WINDOW_NAME)
    cv2.setWindowProperty(config.WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)
    start = time.monotonic()

    while True:
        ok, frame = camera.read()
        if not ok:
            break
        frame = cv2.flip(frame, 1)  # mirror view so moving right looks like right

        timestamp_ms = int((time.monotonic() - start) * 1000)
        landmarks = find_hand(landmarker, frame, timestamp_ms)
        gesture = gestures.classify(landmarks)

        frame = resize_for_window(frame)
        if landmarks:
            overlay.draw_hand(frame, landmarks)
        overlay.draw_status(frame, gesture)
        overlay.draw_help(frame, "q: quit")
        cv2.imshow(config.WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or window_closed():
            break

    camera.release()
    landmarker.close()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
