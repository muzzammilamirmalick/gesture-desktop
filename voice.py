"""Offline voice commands with Vosk.

Everything runs on this computer. Vosk is a speech recognizer that works
without the internet, and the model is a folder on disk (see the README).

The microphone is read on its own thread, so listening never slows down the
hand tracking. Phrases that are heard go into a queue, and the main loop picks
them up whenever it likes, the same way it picks up hand detections.

Vosk is told the exact phrases we care about (a "grammar"). That makes it
much more accurate on short commands, and anything else comes back as "[unk]".
"""

import json
import queue
import threading

SAMPLE_RATE = 16000
BLOCK_SIZE = 2000  # 1/8 of a second of audio per read

OFF = "off"
LOADING = "loading"
LISTENING = "listening"
FAILED = "failed"


class PhraseRecognizer:
    """Feed it raw 16 kHz mono audio, it gives back each finished phrase."""

    def __init__(self, model_path, phrases):
        import vosk  # imported here so the app starts fast when voice is off

        vosk.SetLogLevel(-1)
        grammar = json.dumps(sorted(set(phrases)) + ["[unk]"])
        self.recognizer = vosk.KaldiRecognizer(vosk.Model(str(model_path)), SAMPLE_RATE, grammar)

    def feed(self, audio):
        """Returns the phrase once the speaker pauses, otherwise None."""
        if not self.recognizer.AcceptWaveform(bytes(audio)):
            return None
        text = json.loads(self.recognizer.Result()).get("text", "")
        return text or None


class VoiceListener:
    def __init__(self, model_path, phrases):
        self.model_path = model_path
        self.phrases = list(phrases)
        self.heard = queue.Queue()
        self.status = OFF
        self.error = ""
        self.running = False

    def start(self):
        if self.running:
            return
        self.running = True
        self.status = LOADING
        threading.Thread(target=self.listen, daemon=True).start()

    def stop(self):
        self.running = False
        self.status = OFF

    def listen(self):
        try:
            import sounddevice

            recognizer = PhraseRecognizer(self.model_path, self.phrases)
            with sounddevice.RawInputStream(
                samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE, dtype="int16", channels=1
            ) as stream:
                self.status = LISTENING
                while self.running:
                    audio, _ = stream.read(BLOCK_SIZE)
                    text = recognizer.feed(audio)
                    if text:
                        self.heard.put(text)
        except Exception as error:  # no microphone, no model, and so on
            self.error = str(error) or type(error).__name__
            self.status = FAILED
            self.running = False

    def take_heard(self):
        """Everything heard since the last call, oldest first."""
        phrases = []
        while not self.heard.empty():
            phrases.append(self.heard.get_nowait())
        return phrases
