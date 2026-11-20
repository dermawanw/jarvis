import queue
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from kokoro import KPipeline

stt = WhisperModel("small", device="cpu", compute_type="int8")
tts = KPipeline(lang_code="a")   # 'a' = American English

def listen() -> str:
    q = queue.Queue()
    def cb(indata, frames, t, status):
        q.put(indata.copy())
    with sd.InputStream(samplerate=16000, channels=1, dtype="float32", callback=cb):
        input("  [mic] merekam... tekan Enter untuk berhenti ")
    if q.empty():
        return ""
    audio = np.concatenate(list(q.queue)).flatten()
    segments, _ = stt.transcribe(audio, language="id", vad_filter=True)
    return " ".join(s.text for s in segments).strip()

def speak(text: str):
    for _, _, audio in tts(text, voice="af_heart"):
        audio = audio.numpy() if hasattr(audio, "numpy") else audio
        sd.play(audio, 24000)
        sd.wait()
