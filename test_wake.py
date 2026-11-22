import numpy as np
import wake


def _chunk(amp: int) -> np.ndarray:
    return np.full(wake.CHUNK, amp, dtype=np.int16)


def test_is_affirmative():
    assert wake.is_affirmative("Yes")
    assert wake.is_affirmative("Yes, please confirm.")
    assert not wake.is_affirmative("")
    assert not wake.is_affirmative("No")
    assert not wake.is_affirmative("Yes, wait no cancel")
    assert not wake.is_affirmative("don't do it")
    assert not wake.is_affirmative("maybe later")


def test_collect_speech_boundaries():
    # 1. Hening terus -> batal setelah start_timeout_chunks
    silent_feed = iter([_chunk(10)] * 20)
    out = wake.collect_speech(
        lambda: next(silent_feed, None),
        threshold=0.015,
        end_silence_chunks=3,
        start_timeout_chunks=5,
        max_chunks=20,
    )
    assert out.size == 0

    # 2. Bicara lalu hening -> berhenti lebih awal (2 bicara + 3 hening = 5 chunk)
    mixed = [_chunk(5000), _chunk(5000), _chunk(10), _chunk(10), _chunk(10), _chunk(10)]
    mixed_feed = iter(mixed)
    out = wake.collect_speech(
        lambda: next(mixed_feed, None),
        threshold=0.015,
        end_silence_chunks=3,
        start_timeout_chunks=5,
        max_chunks=20,
    )
    assert out.size == 5 * wake.CHUNK

    # 3. Suara/noise terus-menerus -> berhenti di batas max_chunks (tidak hang)
    loud_feed = iter([_chunk(5000)] * 20)
    out = wake.collect_speech(
        lambda: next(loud_feed, None),
        threshold=0.015,
        end_silence_chunks=3,
        start_timeout_chunks=5,
        max_chunks=6,
    )
    assert out.size == 6 * wake.CHUNK


if __name__ == "__main__":
    test_is_affirmative()
    test_collect_speech_boundaries()
    print("PASS: wake confirmation & speech boundary work.")