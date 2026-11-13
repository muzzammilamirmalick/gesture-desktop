# Gesture Control (desktop)

Control your computer with one hand in front of your webcam. Point to move the mouse, pinch to click, and hold an open palm to open a radial menu with everything else: scroll, volume, switch app, screenshot, play or pause, close window and show desktop.

There is almost nothing to memorize. Two gestures are always on, and the menu shows the rest with icons and labels.

It also has two optional extras: a sign language mode that reads static ASL letters and builds a word, and eye tracking where blinking twice plays or pauses media.

This is the desktop half of my gesture project. It runs on Windows and Mac. Everything runs locally. Nothing is sent over the network.

## Stack

- Python
- MediaPipe HandLandmarker for the 21 hand landmarks, in LIVE_STREAM mode
- MediaPipe FaceLandmarker for blinks and gaze (optional)
- OpenCV to read the webcam and draw the window
- pyautogui to send mouse and keyboard actions
- pytest for the tests

## How to use it

1. Run it. The first time, a short intro shows the three things to know. Press any key to close it.
2. Press **space** to turn control on. The badge in the top right turns green.
3. **Point** with your index finger to move the mouse.
4. **Pinch** (thumb and index together) to click. Let go and pinch again to click again.
5. **Hold an open palm** for half a second. A ring fills around your hand, then the radial menu opens around it.
6. In the menu, **point** at an action to highlight it and **pinch** to pick it. A line from the middle of the menu to your hand shows what you are pointing at. Make a **fist**, or pinch in the middle, to close the menu without doing anything.

### What is in the menu

| Item | What it does |
| --- | --- |
| Scroll | Bring your hand to the circle, then move it up or down to scroll the window under the mouse. The further you move, the faster it scrolls. Pinch when done. |
| Volume | Bring your hand to the circle, then move it up or down. A slider shows each step. Pinch when done. |
| Switch app | Opens the app switcher (Alt+Tab on Windows, Cmd+Tab on Mac). Flick your hand left or right to move through your apps, pinch to go to the highlighted one, or make a fist to cancel. |
| Screenshot | Saves a screenshot (Win+PrintScreen saves to Pictures > Screenshots, Cmd+Shift+3 saves to the Mac desktop). The window flashes so you know it worked. |
| Play / pause | Plays or pauses music and video. |
| Close window | Closes the window or tab (Ctrl+W on Windows, Cmd+W on Mac). |
| Desktop | Hides all windows (Win+D on Windows, F11 on Mac). |

Keyboard actions go to whichever window has focus. Click the window you want first (point and pinch), then use the menu.

Change the order of the menu, or take items out, in `MENU_ITEMS` in `config.py`. The keys behind each action are in `SHORTCUTS` in `config.py`, with a `windows` section and a `mac` section. The app checks which OS it is running on at startup and uses the matching section.

On Mac, pyautogui's play/pause and volume keys do nothing, so `mac_keys.py` sends the same system events that a real keyboard's media keys send.

## The window

- **Top left:** the current mode in big letters (Paused, Pointer, Menu, Scroll, Volume, Switch app) and the hand shape under it.
- **Top right:** a solid **CONTROL ON** (green) or **CONTROL OFF** (red) badge, the video frame rate and the detection rate.
- **Bottom:** one line telling you what to do next, and the keys.
- **Feedback:** every action shows a short label, and a ripple where it happened. A click shows a green ripple at your fingertip. Screenshots flash the window.
- **Help:** press **h** for a side panel with the two gestures, every menu item and the keys.

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
- A pinch only clicks once. Your fingers have to open again before the next pinch counts, and a pinch you were already making when control turned on does not click.
- The cursor freezes the moment your fingers start closing for a pinch, so the click lands where you pointed.
- Scroll and volume wait until your hand reaches the start circle, so nothing jumps the moment you pick them.
- The app switcher holds Alt (or Cmd) down while you flick. It always lets go again: when you pinch, make a fist, take your hand away, turn control off, or quit.
- The menu and the tools close by themselves if your hand is out of view for a second and a half.
- Sign mode always turns control off, so signing letters never clicks or presses anything.
- A double blink only plays or pauses while control is on.
- pyautogui's failsafe is on. Push the real mouse into a screen corner and control switches off.

## Performance

The main loop never waits for the models.

- **Detection runs in the background.** MediaPipe runs in LIVE_STREAM mode (`tracking.py`). The loop hands over the newest frame and carries on straight away, and picks up the newest result whenever one is ready. If the model is still busy, frames are simply not sent, so nothing queues up.
- **The cursor is predicted between detections.** Each detection updates a position and a speed (`CursorPredictor` in `cursor.py`). The loop moves the cursor on every pass using where the hand should be by now, so it glides even when detection runs slower than the camera. `CURSOR_ALPHA`, `CURSOR_BETA` and `CURSOR_MAX_AHEAD` in `config.py` tune it.
- **Scrolling is smooth too.** It also runs on every pass of the loop, as many small wheel steps.
- **GPU if there is one.** With `USE_GPU = True` the app tries the GPU first and falls back to the CPU. The window shows which one is in use. The pip build of MediaPipe for Windows has no GPU support, so it uses the CPU there.
- **Small input for the model.** The camera runs at 640x480 and the models get a 320 pixel wide copy (`DETECTION_WIDTH`). The window still shows the full frame.
- **Light drawing.** The hand is shown as a dot on each fingertip and a ring where the cursor follows, not a full skeleton.
- **The camera is read on its own thread** (`camera.py`), so the loop always has the newest frame.
- **Extras stay off.** Sign mode and eye tracking are off by default. The face model only loads the first time you turn eye tracking on.

Measured on my Windows laptop with a fake 30 fps camera:

| | Video shown | Cursor updates | Longest pause |
| --- | --- | --- | --- |
| Background detection, real hand model | 30 fps | about 640 a second | 3 ms (after startup) |
| Background detection, slow machine (60 ms per detection) | 30 fps | about 640 a second | 4 ms |
| Old blocking loop, slow machine (60 ms per detection) | 17 fps | 17 a second | 61 ms |

## Sign language mode (optional)

Press **s** to switch to sign mode. The window shows the letter it sees in big type, and a bar fills while you hold the letter still. After about a second the letter is added to the word at the bottom of the window.

It knows the ASL letters that can be read from a still hand shape: **A B C D E F I L O U V W Y**. Letters like J and Z need movement, and others such as M, N, S and T look too much alike from a webcam to tell apart reliably.

- To type the same letter twice, drop the shape (or move your hand away) and sign it again.
- Take your hand out of view for about a second and a half to add a space.
- Backspace deletes a letter and **c** clears the word.

The letter rules are in `asl_letters.py`. Each finger is sorted into straight, bent or curled by how far its tip reaches from the wrist compared to its knuckle. Then the letter comes from which fingers are straight, where the thumb is, and which fingertips are touching. The thresholds are in `config.py` under `ASL_`.

## Eye tracking (optional)

Press **e** to turn it on. It is off by default because it runs a second model. Turn it off again when you only want hand control.

- **Blink twice** quickly to play or pause media. Both eyes have to close, so a wink does not count. A long eye close does not count either. The timing is in `config.py` under `BLINK_` and `DOUBLE_BLINK_SECONDS`.
- **Gaze (experimental):** a rough readout of where you are looking: left, right, up or center. It is only shown on screen and never used to click or move anything, because a webcam cannot tell exactly where on the screen you are looking.

The face model needs its own model file (see Running it).

## How it works

1. A background thread grabs frames from the webcam. The main loop takes the newest one, mirrors it so the window behaves like a mirror, and hands it to the hand model in the background.
2. MediaPipe returns 21 landmarks (wrist, knuckles, joints and fingertips). The gesture logic runs once per new detection. The cursor and scrolling move on every pass of the loop.
3. `gestures.py` turns the landmarks into a hand shape with simple rules:
   - A finger is **up** when its tip is farther from the wrist than its middle joint. Using distances instead of y values means it still works with a tilted hand.
   - A **pinch** is when the thumb tip and index tip are close together.
   - All distances are compared to the hand's size (wrist to middle knuckle), so the rules work whether your hand is close to the camera or far away.
4. `debounce.py` waits for the same shape over a few detections, so flicker between poses is ignored.
5. `controller.py` decides what the hand is doing: moving the pointer, using the menu, or running a tool. `menu.py` works out which wedge you point at from the angle between the menu's middle and your hand.
6. `actions.py` sends the mouse and keyboard events with pyautogui, using the shortcut for the current OS from `shortcuts.py`.
7. `overlay.py` and `icons.py` draw the window.

### Files

```
main.py          main loop, keys, and what the window shows
controller.py    pointer, menu and tools
menu.py          radial menu and the open palm hold
gestures.py      hand shape rules and flick detection
debounce.py      ignores flicker between poses
tracking.py      runs the hand and face models in the background
camera.py        reads the webcam on its own thread
cursor.py        hand to screen mapping and cursor prediction
actions.py       mouse, keyboard, scrolling and held keys
shortcuts.py     detects the OS and picks its shortcuts
mac_keys.py      media keys on Mac
permissions.py   startup permission checks
overlay.py       drawing the window
icons.py         the menu icons
instructions.py  plain words for the help panel and intro
asl_letters.py   sign language letter rules
speller.py       builds a word from signed letters
eyes.py          blink detection and gaze
fps.py           frames per second counter
config.py        menu, shortcuts and tuning values
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

If something is too touchy or not touchy enough, these are the values in `config.py` to try first: `PINCH_RATIO`, `STABLE_FRAMES`, `MENU_HOLD_SECONDS`, `SCROLL_SPEED`, `VOLUME_STEP` and `FLICK_DISTANCE`.

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

The Show Desktop key on a Mac is F11 by default. If you changed it, update `show_desktop` in the `mac` section of `SHORTCUTS`.

### Testing live on a Mac

The Mac has a built in camera, so it is the easiest place to test live. The rules were tuned with sample landmark data, so expect to adjust the values listed above on the first real run.

## What I learned

