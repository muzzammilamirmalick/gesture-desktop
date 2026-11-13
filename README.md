# Gesture Control (desktop)

Control your computer with hand gestures from your webcam. A small always-on-top window shows your camera with the detected hand skeleton, the current gesture and whether control is on. When control is switched on, gestures send real mouse and keyboard actions to the operating system.

It also has a sign language mode that reads static ASL letters and builds a word, and an optional eye tracking mode where blinking twice plays or pauses media.

This is the desktop half of my gesture project. It runs on Windows and Mac. Everything runs locally. Nothing is sent over the network.

## Stack

- Python
- MediaPipe HandLandmarker for the 21 hand landmarks
- MediaPipe FaceLandmarker for blinks and gaze (optional)
- OpenCV to read the webcam and draw the window
- pyautogui to send mouse and keyboard actions
- pytest for the tests

## Gestures

| Gesture | Action |
| --- | --- |
| Fist | Rest. This is the neutral pose that gets everything ready to fire |
| Point with your index finger | Move the mouse |
| Pinch (thumb and index together), then let go | Click |
| Pinch and hold for 1 second | Close the window (Ctrl+W on Windows, Cmd+W on Mac) |
| Peace sign, swipe right | Next window (Alt+Tab on Windows, Cmd+Tab on Mac) |
| Peace sign, swipe left | Previous window (Shift+Alt+Tab on Windows, Shift+Cmd+Tab on Mac) |
| Open palm | Play or pause media |
| Thumbs up | Volume up |
| Thumbs down | Volume down |
| Blink twice (eye tracking on) | Play or pause media |

Any other hand shape shows **Unknown** in amber, so you can always see what the camera thinks it sees.

To click something: point to move the mouse onto it, then pinch and let go. The cursor freezes as soon as your fingers start closing, so it does not slide off the target. It follows your index knuckle rather than the fingertip for the same reason (set `CURSOR_FOLLOWS_TIP = True` in `config.py` to change that).

All of the mappings are in `GESTURE_ACTIONS` in `config.py`. Change the action name to remap a gesture, or set it to `None` to turn it off. The on-screen help panel is built from the same mappings, so it always matches.

The keys behind each action are in `SHORTCUTS` in `config.py`, with a `windows` section and a `mac` section. The app checks which OS it is running on at startup and uses the matching section. There is also a `minimize` action (Win+Down on Windows, Cmd+M on Mac) that is not mapped to a gesture.

On Mac, pyautogui's play/pause and volume keys do nothing, so `mac_keys.py` sends the same system events that a real keyboard's media keys send.

## The window

- The current gesture is shown big at the top left. Unknown poses show **UNKNOWN** in amber, and no hand shows **NO HAND** in grey.
- **CONTROL ON** (green) or **CONTROL OFF** (red) at the top right, with frames per second under it. The FPS number turns amber below 24 and red below 15.
- When an action fires, it shows as `Action: click` (or whatever fired) for a second and a half.
- The help panel on the right lists every gesture and key in plain words. Press **h** to show or hide it. It opens by itself the first time you run the app, and stays hidden after you close it once.

## Keys

| Key | What it does |
| --- | --- |
| space | Control on or off (in sign mode, adds a space to the word) |
| h | Show or hide the help panel |
| s | Sign language mode on or off |
| e | Eye tracking on or off |
| backspace | Delete a letter (sign mode) |
| c | Clear the word (sign mode) |
| q | Quit |

Keys only work while the gesture window has focus.

## Safety

- Control starts **OFF**. Press **space** to turn it on.
- After turning control on, nothing fires until you make a fist.
- A gesture has to be held for a few frames before it counts, so quick flickers between poses are ignored.
- Each gesture fires once, then you go back to a fist before anything fires again. Two exceptions: moving the mouse follows your hand the whole time you point, and going back to pointing after a click lets you click again without a fist.
- A quick pinch clicks when you let go, not when you start. That way holding a pinch to close a window never clicks first.
- Sign mode always turns control off, so signing letters never clicks or presses anything.
- A double blink only plays or pauses while control is on. With control off, the window shows that it saw the blink and does nothing.
- pyautogui's failsafe is on. Push the real mouse into a screen corner and control switches off.

## Sign language mode

Press **s** to switch to sign mode. The window shows the letter it sees in big type, and a bar fills while you hold the letter still. After about a second the letter is added to the word at the bottom of the window.

It knows the ASL letters that can be read from a still hand shape: **A B C D E F I L O U V W Y**. Letters like J and Z need movement, and others such as M, N, S and T look too much alike from a webcam to tell apart reliably.

- To type the same letter twice, drop the shape (or move your hand away) and sign it again.
- Take your hand out of view for about a second and a half to add a space.
- Backspace deletes a letter and **c** clears the word.

The letter rules are in `asl_letters.py`. Each finger is sorted into straight, bent or curled by how far its tip reaches from the wrist compared to its knuckle. Then the letter comes from which fingers are straight, where the thumb is, and which fingertips are touching. For example, V and U both have two straight fingers, but V has them spread apart. The thresholds are in `config.py` under `ASL_`.

## Eye tracking (optional)

Press **e** to turn it on. It is off by default because it runs a second model, the MediaPipe face model, on every frame. Turn it off again when you only want hand control.

- **Blink twice** quickly to play or pause media. Both eyes have to close, so a wink does not count. A long eye close does not count either. Blinks come from the face model's own blink scores, which are reliable. The timing is in `config.py` under `BLINK_` and `DOUBLE_BLINK_SECONDS`.
- **Gaze (experimental):** a rough readout of where you are looking: left, right, up or center. It is only shown on screen and never used to click or move anything, because a webcam cannot tell exactly where on the screen you are looking. `GAZE_THRESHOLD` sets how far you have to look before it changes from center.

The face model needs its own model file (see Running it).

## Performance

- The camera is asked for 640x480, which is plenty for hand tracking. Some cameras, like the Mac's, would otherwise send full HD frames.
- The camera is read on its own thread (`camera.py`), and the app always takes the newest frame. Without this, OpenCV can hand back frames that have been queuing up, which feels like lag between your hand and the cursor.
- The same frame is never processed twice, and the help panel is drawn once and reused.
- Measured on my Windows laptop without a camera attached, one frame (detection plus drawing) takes about 14 ms with eye tracking off. With eye tracking on and no face in view, it is about 16 ms. A real face adds a few ms more. All of these stay under the 33 ms a 30 fps webcam allows, so the camera sets the frame rate.
- The cursor smoothing calms small shakes but eases off on big moves (`CURSOR_SMOOTHING` and `CURSOR_FAST_PIXELS`), so it does not lag behind fast movements.

## How it works

1. A background thread grabs frames from the webcam. The main loop takes the newest one and mirrors it so the window behaves like a mirror.
2. MediaPipe finds the hand and returns 21 landmarks (wrist, knuckles, joints and fingertips).
3. `gestures.py` turns those landmarks into a gesture name with simple rules:
   - A finger is **up** when its tip is farther from the wrist than its middle joint. Using distances instead of y values means it still works with a tilted hand.
   - The thumb is **out** when its tip is far from the index knuckle. Whether it points **up** or **down** depends on the thumb tip's position relative to its base.
   - A **pinch** is when the thumb tip and index tip are close together. `PinchTracker` decides between a quick pinch (click on release) and a held pinch.
   - All distances are compared to the hand's size (wrist to middle knuckle), so the rules work whether your hand is close to the camera or far away.
   - A **swipe** is the peace sign moving more than a quarter of the frame width in under half a second.
4. `debounce.py` smooths the result. `GestureStabilizer` waits for the same gesture over several frames, and `TriggerGate` lets one action fire until you reset with a fist.
5. `actions.py` sends the action with pyautogui, using the shortcut for the current OS from `shortcuts.py`. `cursor.py` maps your hand to screen pixels and smooths the movement.
6. In sign mode, `asl_letters.py` reads the letter and `speller.py` builds the word.
7. With eye tracking on, `eyes.py` runs the face model on the unmirrored frame (so "left" means your left), counts blinks and estimates the gaze.

The label at the top shows what the camera sees on each frame. Actions use the stabilized gesture, so the label never freezes while you move between poses.

### Files

```
main.py          main loop, window, keys and app state
camera.py        reads the webcam on its own thread
gestures.py      gesture rules, swipe and pinch tracking
debounce.py      stabilizer and fire-once gate
cursor.py        hand to screen mapping and smoothing
actions.py       mouse and keyboard actions
shortcuts.py     detects the OS and picks its shortcuts
mac_keys.py      media keys on Mac
permissions.py   startup permission checks
asl_letters.py   sign language letter rules
speller.py       builds a word from signed letters
eyes.py          face model, blink detection and gaze
instructions.py  plain-word names for the help panel
overlay.py       drawing the window
fps.py           frames per second counter
config.py        gesture mappings, shortcuts and tuning values
tests/           unit tests with sample landmark data
```

## Running it

Needs Python 3.10 or newer and a webcam. The steps below are for Windows. For a Mac, see [Running on Mac](#running-on-mac).

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Download the MediaPipe models once into `models/`. The face model is only needed for eye tracking.

```
mkdir models
curl -L -o models/hand_landmarker.task https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
curl -L -o models/face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task
```

Then run:

```
python main.py
```

Run the tests:

```
python -m pytest
```

The tests use sample landmark data and stub out pyautogui, so they never move your mouse and they pass the same way on Windows and Mac.

If a gesture is too touchy or not touchy enough, tune `PINCH_RATIO`, `THUMB_EXTENDED_RATIO`, `SWIPE_DISTANCE`, `STABLE_FRAMES` and `PINCH_HOLD_SECONDS` in `config.py`.

## Permissions

The app needs access to your camera and permission to control the mouse and keyboard.

- **Windows:** turn on Settings > Privacy & security > Camera > "Let desktop apps access your camera". Nothing else is needed.
- **Mac:** see below.

## Running on Mac

MediaPipe 1.2.3 only ships for Apple Silicon (M1 or newer), so an Intel Mac would need an older MediaPipe.

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdir models
curl -L -o models/hand_landmarker.task https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
curl -L -o models/face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task
python main.py
```

pip also installs pyobjc, which pyautogui uses on Mac.

### Mac permissions

macOS gives these permissions to the app you run Python from (Terminal, iTerm or VS Code), not to the script. Open **System Settings > Privacy & Security** and turn that app on under:

1. **Camera**, so it can see your hand. macOS usually asks the first time you run it.
2. **Accessibility**, so it can move the mouse, click and press keys. Without this, pyautogui does nothing and does not show an error.
3. **Input Monitoring**, which some macOS versions also want for sending keys.

After changing any of these, quit the terminal completely (Cmd+Q) and open it again.

When the app starts, it checks for Accessibility permission. If it is missing, it prints these steps in the terminal, and the window keeps working as a camera view, but CONTROL ON stays disabled until you fix it.

### Testing live on a Mac

The Mac has a built in camera, so it is the easiest place to test the gestures live. The rules were tuned with sample landmark data, so expect to adjust `PINCH_RATIO`, `THUMB_EXTENDED_RATIO`, `SWIPE_DISTANCE`, `STABLE_FRAMES`, the `ASL_` values and the `BLINK_` values in `config.py` on the first real run.

## What I learned

