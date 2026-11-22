import re
import winsound
import numpy as np
import sounddevice as sd
from openwakeword.model import Model
from brain import chat_turn
from memory import index_vault
import voice

SAMPLE_RATE = 16000
CHUNK = 1280  # 80 ms per frame (standar openWakeWord)
WAKE_THRESHOLD = 0.35

# shortcut: ambang hening statis; naikkan ke 0.025-0.035 jika kipas laptop berisik
SILENCE_THRESHOLD = 0.015
END_SILENCE_CHUNKS = 15    # ~1.2 detik hening setelah bicara -> berhenti rekam
START_TIMEOUT_CHUNKS = 50  # ~4.0 detik tanpa suara -> batal
MAX_RECORD_CHUNKS = 125    # batas keras ~10 detik


def is_affirmative(text: str) -> bool:
    words = set(re.findall(r"[a-z]+", (text or "").lower()))
    if not words:
        return False
    deny = {"no", "nope", "cancel", "stop", "dont", "don", "never", "abort"}
    if words & deny:
        return False
    allow = {"yes", "yeah", "yep", "confirm", "confirmed", "sure", "ok", "okay", "proceed"}
    return bool(words & allow)


def collect_speech(
    read_chunk,
    threshold: float = SILENCE_THRESHOLD,
    end_silence_chunks: int = END_SILENCE_CHUNKS,
    start_timeout_chunks: int = START_TIMEOUT_CHUNKS,
    max_chunks: int = MAX_RECORD_CHUNKS,
) -> np.ndarray:
    chunks = []
    heard_speech = False
    silent = 0
    for _ in range(max_chunks):
        chunk = read_chunk()
        if chunk is None:
            break
        f32 = chunk.astype(np.float32) / 32768.0
        rms = float(np.sqrt(np.mean(f32 * f32)))
        chunks.append(f32)
        if rms >= threshold:
            heard_speech = True
            silent = 0
        else:
            silent += 1
            if heard_speech and silent >= end_silence_chunks:
                break
            if not heard_speech and silent >= start_timeout_chunks:
                return np.array([], dtype=np.float32)
    if not heard_speech or not chunks:
        return np.array([], dtype=np.float32)
    return np.concatenate(chunks)


def record_command(max_chunks: int = MAX_RECORD_CHUNKS) -> np.ndarray:
    with sd.InputStream(
        samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=CHUNK
    ) as stream:
        return collect_speech(
            lambda: stream.read(CHUNK)[0][:, 0],
            max_chunks=max_chunks,
        )


def transcribe_array(audio: np.ndarray) -> str:
    segments, _ = voice.stt.transcribe(audio, language="en", vad_filter=True)
    return " ".join(s.text for s in segments).strip()


def wait_for_wake_word(oww: Model):
    print("Listening for 'Hey Jarvis'... (Ctrl+C to stop)")
    with sd.InputStream(
        samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=CHUNK
    ) as stream:
        while True:
            data, _ = stream.read(CHUNK)
            scores = oww.predict(data[:, 0])
            if max(scores.values(), default=0.0) >= WAKE_THRESHOLD:
                oww.reset()
                return


def voice_confirm(name: str, args: dict) -> bool:
    label = name.replace("_", " ")
    print(f"  [confirm] {name}({args})")
    voice.speak(f"Confirm {label}? Say yes to proceed, or no to cancel.")
    winsound.Beep(660, 120)
    audio = record_command(max_chunks=50)
    if audio.size == 0:
        return False
    answer = transcribe_array(audio)
    print(f"  [confirm heard] {answer}")
    return is_affirmative(answer)


def main():
    print(f"Indexed: {index_vault()} chunks.")
    print("  [wake] loading hey_jarvis model...")
    oww = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
    history: list[dict] = []

    try:
        while True:
            wait_for_wake_word(oww)
            winsound.Beep(880, 120)
            print("  [mic] listening...")
            audio = record_command()
            if audio.size == 0:
                print("  [mic] no speech detected.\n")
                continue

            user = transcribe_array(audio)
            print(f"You > {user}")
            if not user:
                continue

            reply, _ = chat_turn(user, history, confirm_fn=voice_confirm)
            print(f"JARVIS > {reply}\n")
            voice.speak(reply)
    except KeyboardInterrupt:
        print("\nJARVIS wake listener stopped.")


if __name__ == "__main__":
    main()