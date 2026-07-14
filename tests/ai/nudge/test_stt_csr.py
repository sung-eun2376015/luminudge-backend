# test_stt_csr.py

from ai.nudge.stt_csr import STTResult, build_csr_event


def test_csr_positive_case():
    mission = {
        "type": "open_question",
        "prompt": "토끼가 어떻게 뛰고 있었지?",
        "expected_keywords": ["토끼", "깡충"],
    }

    stt_result = STTResult(
        transcript="토끼가 깡충깡충 뛰고 있었어",
        source="web_speech",
        confidence=0.92,
    )

    event = build_csr_event(stt_result, mission)

    assert event["event_type"] == "csr_evaluation"
    assert event["csr_score"] == 1.0
    assert event["is_contextual"] is True
    assert "토끼" in event["matched_keywords"]
    assert "깡충" in event["matched_keywords"]

    print("PASS: positive CSR case")
    print(event)


def test_csr_partial_case():
    mission = {
        "type": "open_question",
        "prompt": "토끼가 어떻게 뛰고 있었지?",
        "expected_keywords": ["토끼", "깡충"],
    }

    stt_result = STTResult(
        transcript="토끼가 뛰었어",
        source="web_speech",
        confidence=0.81,
    )

    event = build_csr_event(stt_result, mission)

    assert event["csr_score"] == 0.5
    assert event["is_contextual"] is True
    assert "토끼" in event["matched_keywords"]
    assert "깡충" in event["missing_keywords"]

    print("PASS: partial CSR case")
    print(event)


def test_csr_negative_case():
    mission = {
        "type": "open_question",
        "prompt": "토끼가 어떻게 뛰고 있었지?",
        "expected_keywords": ["토끼", "깡충"],
    }

    stt_result = STTResult(
        transcript="몰라",
        source="web_speech",
        confidence=0.5,
    )

    event = build_csr_event(stt_result, mission)

    assert event["csr_score"] == 0.0
    assert event["is_contextual"] is False

    print("PASS: negative CSR case")
    print(event)


if __name__ == "__main__":
    test_csr_positive_case()
    test_csr_partial_case()
    test_csr_negative_case()

    print("PASS: STT CSR logic works with mock transcripts.")
