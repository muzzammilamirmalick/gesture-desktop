# Gesture Control (desktop)

Control your computer with your hands in front of your webcam. Point to move the mouse, pinch to click, and hold an open palm to open a radial menu with everything else: scroll, volume, switch app, screenshot, play or pause, close window and show desktop.

There is almost nothing to memorize. Two gestures are always on, and the menu shows the rest with icons and labels.

You can also use offline voice commands like "scroll down" or "next window", and there is an optional sign language mode that reads static ASL letters and builds a word.

This is the desktop half of my gesture project. It runs on Windows and Mac. Everything runs locally. Nothing is sent over the network.

## Stack

- Python
- MediaPipe HandLandmarker for the 21 hand landmarks, in LIVE_STREAM mode
- OpenCV to read the webcam and draw the window
- Vosk for offline speech recognition, and sounddevice to read the microphone
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

## Both hands

The app tracks up to two hands at once. Each one is labelled **Left** or **Right** (from MediaPipe's handedness) and drawn in its own color: blue for right, amber for left. Each hand has its own smoothing, so they never pull on each other.

One hand moves the mouse. When both are in view it is the one set in `CONTROL_HAND` in `config.py` (right by default). With only one hand in view, that hand is in control, whichever side it is. The control hand has the green ring on it.

Now and then MediaPipe calls both hands the same side. When that happens the app goes by position instead: in the mirrored view, your left hand is the one on the left.

## Finger counting

Each hand shows a tag under the wrist with its side and how many fingers it is holding up, from 0 to 5. A new number shows once it has held for a few detections, so it does not flicker while you move.

The rules are in `fingers.py`. They only use angles and distance ratios, so the count stays the same when your hand is tilted, upside down, near the camera or far away:

- **Index to pinky:** a finger is up when it is straight (it bends less than 50 degrees at its middle joint) and its tip is farther from the wrist than its middle joint.
- **Thumb:** up when it is straight, it points away from the pinky side of the hand, and its tip is at least half a hand size away from the index knuckle. A thumb tucked across the palm or pressed against the side of the hand does not count.

The app gives these rules MediaPipe's 3D world points (in meters, centred on the hand). In 3D a finger pointing towards the camera still looks straight, which a flat 2D picture cannot tell you.

## Voice commands

Press **v** to turn voice on. It is off by default, so it never takes anything away from hand tracking unless you want it. Speech recognition runs on this computer with [Vosk](https://alphacephei.com/vosk/). Nothing is recorded and nothing goes over the internet.

| Say | What it does |
| --- | --- |
| "click" | Click where the mouse is |
| "scroll up" / "scroll down" | Scroll the window under the mouse |
| "next window" | Alt+Tab (Cmd+Tab on Mac) |
| "volume up" / "volume down" | Two volume steps |
| "play" / "pause" | The play/pause media key. There is only one key for both, so both toggle |
| "screenshot" | Save a screenshot |
| "control on" / "control off" | Same as the space key |

Everything except "control on" is ignored while control is off, so talking near your computer never does anything by surprise.

A box under the badge shows whether voice is listening, the last thing it heard, and which action that fired (or why it did not).

The phrases and their actions are in `VOICE_COMMANDS` in `config.py`. Add or change a line there and the app picks it up on the next start. Vosk is given the exact list of phrases, which makes it much more accurate on short commands than general dictation. Anything else comes back as unknown and is ignored.

The microphone is read on its own thread (`voice.py`), and the main loop picks up phrases the same way it picks up hand detections, so it never waits. `voice_commands.py` matches what was heard to a command.

I checked the recognizer with every phrase spoken by Windows text to speech: all 11 were heard correctly, and a phrase that is not a command ("what time is it") was ignored. Each took under 70 ms to process after the speaker stopped.

## Your own gestures

Press **t** for training mode. A bar across the top shows the four steps and which one you are on.

1. **Pose.** Make the pose you want to teach and press **r**. You get a two second countdown to get your hand back in place.
2. **Record.** Hold still for two seconds while it records. A red bar fills up. It keeps about 30 samples of your pose.
3. **Name.** Type a name and press Enter.
4. **Action.** Press a number from 1 to 9 to pick what it does (the list is `TRAINING_ACTIONS` in `config.py`).

It is saved straight away to `my_gestures.json` and loaded every time the app starts. Press **r** to record another or **Esc** to leave. On the first step, backspace deletes the last gesture you saved. The help screen (h) lists your gestures.

With control on, hold one of your gestures still for about half a second and its action runs once. A ring fills around your hand while you hold it, and the header shows the gesture's name. To run it again, drop the pose and make it again. Your gestures never get in the way of pointing, pinching or the open palm menu.

### How it recognizes them

The classifier is in `custom_gestures.py`. It is a k-nearest-neighbour classifier, and the comments at the top of the file walk through it:

1. **Features.** The 21 hand points are moved so the wrist is at zero and divided by the hand size, so it does not matter where your hand is or how far from the camera. Left hands are flipped, so a gesture trained with one hand works with the other.
2. **Distance.** Two hands are compared by the biggest gap between any pair of matching points. The average would hide a pose that differs in only one finger.
3. **Vote.** The live hand is compared to every saved sample. The 5 closest vote, and the most common name wins.
4. **Too far is nothing.** If even the closest sample is more than `CUSTOM_MATCH_DISTANCE` away (0.35 hand sizes), it is not any of your gestures.

If a gesture fires when it should not, lower `CUSTOM_MATCH_DISTANCE`. If it is hard to trigger, raise it a little or record it again while moving your hand around a bit, so it has more variety to match against.

## App profiles

The app checks which program is in front twice a second and switches to a profile for it. The header shows the active profile next to the hand shape.

| Profile | Apps | Hold a hand shape | Extra voice commands |
| --- | --- | --- | --- |
| Browser | Chrome, Edge, Firefox, Safari, Brave, Opera, Vivaldi, Arc | Two fingers: next tab. Thumbs up: forward. Thumbs down: back | "next tab", "previous tab", "go back", "go forward" |
| Media | Spotify, VLC, Music, iTunes, Windows Media Player, mpv | Two fingers: play or pause. Thumbs up/down: volume | "next", "next song", "previous", "previous song" |
| Default | everything else | Thumbs up/down: volume | none |

Scrolling works everywhere with the menu or by voice, so the browser profile does not need its own. The main voice commands work in every profile, and a profile only adds to them. Hold a hand shape still for about half a second to run it, the same as your own gestures. The help screen (h) shows the hand shapes for the profile you are in. A phrase from another profile shows "not for this app" so you know it was heard.

Profiles live in `PROFILES` in `config.py`. To add one, copy a block, put part of the program's name in `apps` (the .exe name on Windows, like `msedge`, or the app name on a Mac, like `Safari`), and fill in `gestures` and `voice`. Only the program name is matched, not the window title, so a document called "knowledge base" never counts as Edge.

When you press a key in the gesture window, it is the window in front for a moment. The app spots its own window and keeps the profile you were in.

`active_window.py` reads the app in front (with Win32 calls on Windows and NSWorkspace on Mac, nothing extra to install) and `profiles.py` picks the profile and merges its mappings.

## The window

- **Top left:** the current mode in big letters (Paused, Pointer, Menu, Scroll, Volume, Switch app), and under it the hand shape and the app profile.
- **Top right:** a solid **CONTROL ON** (green) or **CONTROL OFF** (red) badge, the display frame rate, the webcam rate and the detection rate.
- **Bottom:** one line telling you what to do next, and the keys.
- **Feedback:** every action shows a short label, and a ripple where it happened. A click shows a green ripple at your fingertip. Screenshots flash the window.
- **Help:** press **h** for a help screen over the video with the gestures, every menu item, the voice commands and the keys.

## Keys

| Key | What it does |
| --- | --- |
| space | Control on or off (in sign mode, adds a space to the word) |
| h | Show or hide the help panel |
| s | Sign language mode on or off |
| v | Voice commands on or off |
| t | Training mode, to teach it your own gesture |
| Esc | Leave training mode |
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
- pyautogui's failsafe is on. Push the real mouse into a screen corner and control switches off.

## Performance

The window redraws at **60 fps**. The webcam and the hand model each run at their own speed, and the main loop never waits for either of them.

- **60 fps display.** The window redraws every 1/60 of a second (`DISPLAY_FPS`), even if the webcam only sends 30 frames a second. The video itself can only update as often as the webcam sends a frame, but the hand overlay, the menu and the cursor move every redraw.
- **Detection runs in the background.** HandLandmarker runs in LIVE_STREAM mode (`tracking.py`). The loop hands over the newest frame and carries on straight away, and picks up the newest result whenever one is ready. If the model is still busy, frames are simply not sent, so nothing queues up. Detection runs as fast as your hardware allows.
- **Prediction fills the gaps.** Each detection updates a position and a speed for the cursor (`cursor.py`) and for every hand point (`motion.py`). Between detections they keep moving to where the hand should be by now, so motion looks fluid even when detection is slower than 60. `CURSOR_ALPHA`, `CURSOR_BETA`, `HAND_ALPHA` and the others in `config.py` tune it.
- **GPU if there is one.** With `USE_GPU = True` the app tries the GPU first and falls back to the CPU. The window shows which one is in use. The pip build of MediaPipe for Windows has no GPU support, so it uses the CPU there.
- **High resolution camera, small copy for the model.** The app asks the webcam for 1280x720 at 60 fps (in MJPG, which most webcams need for that). The window shows it at 960 wide (`WINDOW_WIDTH`) and the model gets a 480 wide copy (`DETECTION_WIDTH`).
- **Light drawing.** The hand is a thin skeleton drawn in one call plus a dot on each fingertip. The help panel is drawn once and reused.
- **The camera is read on its own thread** (`camera.py`), so the loop always has the newest frame.
- **Voice stays off until you want it.** The Vosk model only loads the first time you press v, and the microphone is read on its own thread.
- **1 ms timer on Windows.** Windows normally sleeps in 15 ms steps, which made each pass of the loop take 15 ms and the window miss frames. The app asks for 1 ms steps while it runs.

The top right of the window shows the real numbers: the display rate, what the webcam really sends, and how fast detection is running (and on CPU or GPU).

Measured on my Windows laptop with a fake 720p camera feeding the real hand model (CPU):

| Webcam | Display | Detection | 99% of frames within | Loop passes per second |
| --- | --- | --- | --- | --- |
| 30 fps | 60.0 fps | 30 fps | 20.7 ms | about 630 |
| 60 fps | 60.0 fps | 59 fps | 20.7 ms | about 440 |
| 30 fps, before the 1 ms timer fix | 58.8 fps | 30 fps | 33.9 ms | about 65 |

With prediction, the drawn hand moves on every frame. Without it, it sat still on half the frames and then jumped (detection at 25 fps, drawn at 60).

## Sign language mode (optional)

Press **s** to switch to sign mode. The window shows the letter it sees in big type, and a bar fills while you hold the letter still. After about a second the letter is added to the word at the bottom of the window.

It knows the ASL letters that can be read from a still hand shape: **A B C D E F I L O U V W Y**. Letters like J and Z need movement, and others such as M, N, S and T look too much alike from a webcam to tell apart reliably.

- To type the same letter twice, drop the shape (or move your hand away) and sign it again.
- Take your hand out of view for about a second and a half to add a space.
- Backspace deletes a letter and **c** clears the word.

The letter rules are in `asl_letters.py`. Each finger is sorted into straight, bent or curled by how far its tip reaches from the wrist compared to its knuckle. Then the letter comes from which fingers are straight, where the thumb is, and which fingertips are touching. The thresholds are in `config.py` under `ASL_`.

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
gesture_control.spec  the PyInstaller build
controller.py    pointer, menu and tools
menu.py          radial menu and the open palm hold
gestures.py      hand shape rules and flick detection
fingers.py       counts the fingers held up on each hand
debounce.py      ignores flicker between poses
tracking.py      runs the hand model in the background
camera.py        reads the webcam on its own thread
cursor.py        hand to screen mapping and cursor prediction
motion.py        smooth, predicted hand points for drawing
actions.py       mouse, keyboard, scrolling and held keys
shortcuts.py     detects the OS and picks its shortcuts
mac_keys.py      media keys on Mac
permissions.py   startup permission checks
overlay.py       drawing the window
icons.py         the menu icons
instructions.py  plain words for the help panel and intro
custom_gestures.py  your gestures: features, the classifier, saving
training.py      the steps of training mode
pose_trigger.py  runs a pose's action once it is held
paths.py         where the app keeps its files
active_window.py which app is in front
profiles.py      picks the app profile and merges its mappings
asl_letters.py   sign language letter rules
voice.py         listens to the microphone with Vosk, offline
voice_commands.py  matches what was heard to a command
speller.py       builds a word from signed letters
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

Download the MediaPipe hand model and the small Vosk English model (about 40 MB) once into `models/`. Both stay out of git.

```
mkdir models
curl -L -o models/hand_landmarker.task https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
curl -L -o models/vosk.zip https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
tar -xf models/vosk.zip -C models
del models\vosk.zip
```

The Vosk model is only needed for voice commands. Without it everything else works, and pressing v says the model is missing.

Then run:

```
python main.py
```

Check that both models load, without needing a camera:

```
python main.py --check
```

It prints OK and exits with code 0 when everything is in place.

Run the tests:

```
python -m pytest
```

The tests use sample landmark data and stub out pyautogui, so they never move your mouse and they pass the same way on Windows and Mac.

If something is too touchy or not touchy enough, these are the values in `config.py` to try first: `PINCH_RATIO`, `STABLE_FRAMES`, `MENU_HOLD_SECONDS`, `SCROLL_SPEED`, `VOLUME_STEP` and `FLICK_DISTANCE`.

## Building a double-click app

PyInstaller packs Python, the libraries and both models into one app, so it runs on a computer without Python. Download the models first (see Running it), then:

```
pip install -r requirements-build.txt
pyinstaller gesture_control.spec
```

- **Windows:** `dist\GestureControl.exe`, a single file. Double-click it.
- **Mac:** `dist/Gesture Control.app`. Drag it into Applications.

Build on the system you want the app for. PyInstaller cannot build a Mac app on Windows or the other way round. The output in `build/` and `dist/` stays out of git.

To check a build without a camera, run `GestureControl.exe --check` (or `"dist/Gesture Control.app/Contents/MacOS/GestureControl" --check` on a Mac). On my Windows laptop the exe is about 180 MB, takes about a minute and a half to build, and the check passes with both models loading from inside the exe.

Things to know about the packaged app:

- `config.py` is built into the app. Change settings before you build, or run it with Python to tweak them.
- Your saved gestures and the intro flag go into your user account instead of the project folder: `%APPDATA%\Gesture Control` on Windows and `~/Library/Application Support/Gesture Control` on a Mac.
- The Windows exe unpacks itself to a temp folder each time it starts, so it takes a few seconds to open.
- There is no terminal, so if the webcam or the hand model is missing, the app says so in a small window.

### Permissions for the packaged app

**Windows**

- The app is not signed, so the first time Windows SmartScreen says "Windows protected your PC". Click **More info**, then **Run anyway**. Some antivirus programs are wary of PyInstaller exes too.
- Settings > Privacy & security > **Camera**: turn on "Let desktop apps access your camera".
- Settings > Privacy & security > **Microphone**: turn on "Let desktop apps access your microphone", only needed for voice.
- Nothing extra is needed to move the mouse or press keys. Windows does not let an app control windows that run as administrator, unless the app also runs as administrator.

**Mac**

The permissions now belong to **Gesture Control** itself, not to Terminal.

- The app is not signed, so the first time right-click it, choose **Open**, then **Open** again. After that it opens normally.
- **Camera** and **Microphone**: macOS asks the first time. The app explains why in the prompt.
- **Accessibility** (to move the mouse, click and press keys) and **Input Monitoring**: open System Settings > Privacy & Security, click +, and add Gesture Control from Applications. Then quit the app and open it again.
- If you build a new version, macOS may treat it as a new app. Remove the old entry in Accessibility and add it again.

## Permissions

The app needs access to your camera and permission to control the mouse and keyboard.

- **Windows:** turn on Settings > Privacy & security > Camera > "Let desktop apps access your camera". For voice, do the same under Microphone. Nothing else is needed.
- **Mac:** see below.

## Running on Mac

MediaPipe 1.2.3 only ships for Apple Silicon (M1 or newer), so an Intel Mac would need an older MediaPipe.

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdir models
curl -L -o models/hand_landmarker.task https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
curl -L -o models/vosk.zip https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip models/vosk.zip -d models && rm models/vosk.zip
python main.py
```

pip also installs pyobjc, which pyautogui uses on Mac.

### Mac permissions

macOS gives these permissions to the app you run Python from (Terminal, iTerm or VS Code), not to the script. Open **System Settings > Privacy & Security** and turn that app on under:

1. **Camera**, so it can see your hand. macOS usually asks the first time you run it.
2. **Microphone**, only for voice commands. macOS asks the first time you press v.
3. **Accessibility**, so it can move the mouse, click and press keys. Without this, pyautogui does nothing and does not show an error.
4. **Input Monitoring**, which some macOS versions also want for sending keys.

After changing any of these, quit the terminal completely (Cmd+Q) and open it again.

When the app starts, it checks for Accessibility permission. If it is missing, it prints these steps in the terminal, and the window keeps working as a camera view, but CONTROL ON stays disabled until you fix it.

The Show Desktop key on a Mac is F11 by default. If you changed it, update `show_desktop` in the `mac` section of `SHORTCUTS`.

### Testing live on a Mac

The Mac has a built in camera, so it is the easiest place to test live. The rules were tuned with sample landmark data, so expect to adjust the values listed above on the first real run.

## What I learned

