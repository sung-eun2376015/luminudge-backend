# test_stt_adapter.py

from ai.nudge.stt_adapter import (
    build_mock_stt_payload,
    build_stt_result_from_payload,
    should_use_whisper_fallback,
)


def test_web_speech_payload_to_stt_result():
    payload = {
        "transcript": "토끼가 깡충 뛰었어",
        "source": "web_speech",
        "confidence": 0.91,
        "language": "ko-KR",
    }

    stt_result = build_stt_result_from_payload(payload)

    assert stt_result.transcript == "토끼가 깡충 뛰었어"
    assert stt_result.source == "web_speech"
    assert stt_result.confidence == 0.91
    assert stt_result.language == "ko-KR"

    print("PASS: web speech payload converted to STTResult")
    print(stt_result)


def test_mock_payload_to_stt_result():
    payload = build_mock_stt_payload("강아지가 공을 가지고 놀았어")

    stt_result = build_stt_result_from_payload(payload)

    assert stt_result.transcript == "강아지가 공을 가지고 놀았어"
    assert stt_result.source == "mock"
    assert stt_result.confidence == 1.0

    print("PASS: mock STT payload converted to STTResult")
    print(stt_result)


def test_empty_transcript_uses_whisper_fallback():
    payload = {
        "transcript": "",
        "source": "web_speech",
        "confidence": 0.9,
        "language": "ko-KR",
    }

    stt_result = build_stt_result_from_payload(payload)

    assert should_use_whisper_fallback(stt_result) is True

    print("PASS: empty transcript requests whisper fallback")


def test_low_confidence_uses_whisper_fallback():
    payload = {
        "transcript": "토끼",
        "source": "web_speech",
        "confidence": 0.3,
        "language": "ko-KR",
    }

    stt_result = build_stt_result_from_payload(payload)

    assert should_use_whisper_fallback(stt_result) is True

    print("PASS: low confidence requests whisper fallback")


def test_good_web_speech_does_not_use_whisper_fallback():
    payload = {
        "transcript": "토끼가 깡충 뛰었어",
        "source": "web_speech",
        "confidence": 0.88,
        "language": "ko-KR",
    }

    stt_result = build_stt_result_from_payload(payload)

    assert should_use_whisper_fallback(stt_result) is False

    print("PASS: good web speech result does not request fallback")


if __name__ == "__main__":
    test_web_speech_payload_to_stt_result()
    test_mock_payload_to_stt_result()
    test_empty_transcript_uses_whisper_fallback()
    test_low_confidence_uses_whisper_fallback()
    test_good_web_speech_does_not_use_whisper_fallback()

    print("PASS: STT adapter logic works.")
