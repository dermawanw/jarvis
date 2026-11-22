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


def transcribe_file(audio_path: str) -> str:
    if not audio_path:
        return ""
    segments, _ = stt.transcribe(audio_path, language="en", vad_filter=True)
    return " ".join(s.text for s in segments).strip()


def synthesize(text: str) -> tuple[int, np.ndarray] | None:
    if not text.strip():
        return None
    chunks = []
    for _, _, audio in tts(text, voice="af_heart"):
        if audio is None:
            continue
        arr = audio.numpy() if hasattr(audio, "numpy") else np.asarray(audio)
        chunks.append(arr)
    if not chunks:
        return None
    full = np.concatenate(chunks)
    pcm16 = (np.clip(full, -1.0, 1.0) * 32767).astype(np.int16)
    return (24000, pcm16)


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
    res = synthesize(text)
    if res is None:
        return
    sr, pcm16 = res
    sd.play(pcm16, sr)
    sd.wait()