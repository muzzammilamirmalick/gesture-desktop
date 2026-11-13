# Gesture Control (desktop)

Control your computer with hand gestures from your webcam. A small always-on-top window shows your camera with the detected hand skeleton and the current gesture. When control is switched on, gestures send real mouse and keyboard actions to the operating system.

This is the desktop half of my gesture project. Everything runs locally. Nothing is sent over the network.

## Stack

- Python
- MediaPipe Hands (HandLandmarker) for the 21 hand landmarks
- OpenCV to read the webcam and draw the overlay
- pyautogui to send mouse and keyboard actions
- pytest for the tests

## Gestures

| Gesture | Action |
| --- | --- |
| Pinch (thumb and index together) | Click |
| Point with index finger | Move the cursor |
| Two fingers, swipe right | Next window (Alt+Tab) |
| Two fingers, swipe left | Previous window (Alt+Shift+Tab) |
| Open palm | Play or pause media |
| Thumbs up | Volume up |
| Thumbs down | Volume down |
| Fist | Nothing. This is the neutral pose that re-arms gestures |

All of the mappings are in `GESTURE_ACTIONS` in `config.py`. Change the action name to remap a gesture, or set it to `None` to turn it off.

## Safety

- Control starts **OFF**. Press **space** to toggle it. The window shows CONTROL ON or CONTROL OFF.
- After turning control on, nothing fires until you make a fist.
- A gesture has to be held for a few frames before it counts, so quick flickers between poses are ignored.
- Each gesture fires once, then you have to go back to a fist before anything fires again. Moving the cursor is the exception. It follows your finger the whole time you point.
- pyautogui's failsafe is on. Push the real mouse into a screen corner and control switches off.
- Press **q** (or close the window) to quit.

## How it works

1. OpenCV grabs a frame from the webcam and mirrors it so it behaves like a mirror.
2. MediaPipe finds the hand and returns 21 landmarks (wrist, knuckles, joints and fingertips).
3. `gestures.py` turns those landmarks into a gesture name with simple rules:
   - A finger is **up** when its tip is farther from the wrist than its middle joint. Using distances instead of y values means it still works with a tilted hand.
   - The thumb is **out** when its tip is far from the index knuckle. Whether it points **up** or **down** depends on the thumb tip's position relative to its base.
   - A **pinch** is when the thumb tip and index tip are close together.
   - All distances are compared to the hand's size (wrist to middle knuckle), so the rules work whether your hand is close to the camera or far away.
   - A **swipe** is the two finger pose moving more than a quarter of the frame width in under half a second.
4. `debounce.py` smooths the result. `GestureStabilizer` waits for the same gesture over several frames, and `TriggerGate` lets a gesture fire once until you reset with a fist.
5. `actions.py` sends the action with pyautogui. `cursor.py` maps your fingertip to screen pixels and smooths the movement.

### Files

```
main.py          webcam loop, window and keys
gestures.py      gesture rules and swipe detection
debounce.py      stabilizer and fire-once gate
cursor.py        fingertip to screen mapping and smoothing
actions.py       mouse and keyboard actions
overlay.py       drawing the skeleton and status
config.py        gesture mappings and tuning values
tests/           unit tests with sample landmark data
```

## Running it

Needs Python 3.10 or newer and a webcam.

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Download the MediaPipe hand model once into `models/`:

```
mkdir models
curl -L -o models/hand_landmarker.task https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
```

Then run:

```
python main.py
```

Run the tests:

```
python -m pytest
```

If a gesture is too touchy or not touchy enough, tune `PINCH_RATIO`, `THUMB_EXTENDED_RATIO`, `SWIPE_DISTANCE` and `STABLE_FRAMES` in `config.py`.

## Permissions

The app needs access to your camera and permission to control the mouse and keyboard.

- **Windows:** Settings > Privacy & security > Camera, and turn on "Let desktop apps access your camera".
- **macOS:** allow your terminal under System Settings > Privacy & Security > Camera, and also under Accessibility so it can control the mouse and keyboard.

Keyboard shortcuts (space and q) only work while the gesture window has focus.

## What I learned

