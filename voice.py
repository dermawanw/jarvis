import queue
import warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from kokoro import KPipeline

print("  [voice] loading models...")
stt = WhisperModel("small", device="cpu", compute_type="int8")
tts = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")


def listen() -> str:
    q = queue.Queue()

    def cb(indata, frames, t, status):
        q.put(indata.copy())

    with sd.InputStream(samplerate=16000, channels=1, dtype="float32", callback=cb):
        input("  [mic] recording... press Enter to stop ")
    if q.empty():
        return ""
    audio = np.concatenate(list(q.queue)).flatten()
    segments, _ = stt.transcribe(audio, language="en", vad_filter=True)
    return " ".join(s.text for s in segments).strip()


def speak(text: str):
    for _, _, audio in tts(text, voice="af_heart"):
        if audio is None:
            continue
        audio = audio.numpy() if hasattr(audio, "numpy") else audio
        sd.play(audio, 24000)
        sd.wait()