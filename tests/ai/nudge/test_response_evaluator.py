# test_response_evaluator.py

from ai.nudge.response_evaluator import evaluate_response_from_stt_payload


def test_response_evaluation_positive_case():
    mission = {
        "type": "open_question",
        "prompt": "토끼가 어떻게 뛰고 있었지?",
        "expected_keywords": ["토끼", "깡충"],
    }

    stt_payload = {
        "transcript": "토끼가 깡충 뛰었어",
        "source": "web_speech",
        "confidence": 0.93,
        "language": "ko-KR",
    }

    event = evaluate_response_from_stt_payload(stt_payload, mission)

    assert event["event_type"] == "response_evaluation"
    assert event["needs_whisper_fallback"] is False
    assert event["csr"]["csr_score"] == 1.0
    assert event["csr"]["is_contextual"] is True

    print("PASS: response evaluation positive case")
    print(event)


def test_response_evaluation_low_confidence_case():
    mission = {
        "type": "open_question",
        "prompt": "토끼가 어떻게 뛰고 있었지?",
        "expected_keywords": ["토끼", "깡충"],
    }

    stt_payload = {
        "transcript": "토끼",
        "source": "web_speech",
        "confidence": 0.35,
        "language": "ko-KR",
    }

    event = evaluate_response_from_stt_payload(stt_payload, mission)

    assert event["needs_whisper_fallback"] is True
    assert event["csr"]["csr_score"] == 0.5

    print("PASS: response evaluation low confidence case")
    print(event)


def test_response_evaluation_empty_transcript_case():
    mission = {
        "type": "open_question",
        "prompt": "토끼가 어떻게 뛰고 있었지?",
        "expected_keywords": ["토끼", "깡충"],
    }

    stt_payload = {
        "transcript": "",
        "source": "web_speech",
        "confidence": 0.9,
        "language": "ko-KR",
    }

    event = evaluate_response_from_stt_payload(stt_payload, mission)

    assert event["needs_whisper_fallback"] is True
    assert event["csr"]["csr_score"] == 0.0
    assert event["csr"]["is_contextual"] is False

    print("PASS: response evaluation empty transcript case")
    print(event)


if __name__ == "__main__":
    test_response_evaluation_positive_case()
    test_response_evaluation_low_confidence_case()
    test_response_evaluation_empty_transcript_case()

    print("PASS: response evaluator connects STT payload to CSR event.")
