from ai.nudge.semantic_csr import (
    build_expected_text,
    calculate_semantic_csr,
    cosine_similarity,
)


MISSION = {
    "answer": "파란색",
    "expected_keywords": ["파란색"],
}


def test_cosine_similarity() -> None:
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_semantic_csr_uses_embedding_similarity() -> None:
    def fake_embedder(texts: list[str]) -> list[list[float]]:
        assert texts == ["방이 파랗게 변했어요", "파란색"]
        return [[1.0, 0.0], [0.9, 0.1]]

    result = calculate_semantic_csr(
        transcript="방이 파랗게 변했어요",
        mission=MISSION,
        embedder=fake_embedder,
    )

    assert result.method == "semantic_embedding"
    assert result.csr_score > 0.65
    assert result.fallback_reason is None


def test_embedding_failure_falls_back_to_keyword_csr() -> None:
    def failing_embedder(_: list[str]) -> list[list[float]]:
        raise RuntimeError("temporary embedding failure")

    result = calculate_semantic_csr(
        transcript="정답은 파란색이에요",
        mission=MISSION,
        embedder=failing_embedder,
    )

    assert result.method == "keyword_fallback"
    assert result.csr_score == 1.0
    assert result.fallback_reason == "temporary embedding failure"


def test_expected_text_uses_keywords_when_answer_is_unavailable() -> None:
    assert build_expected_text(
        {"answer": "없음", "expected_keywords": ["토끼", "깡충"]}
    ) == "토끼 깡충"


if __name__ == "__main__":
    test_cosine_similarity()
    test_semantic_csr_uses_embedding_similarity()
    test_embedding_failure_falls_back_to_keyword_csr()
    test_expected_text_uses_keywords_when_answer_is_unavailable()
    print("PASS: semantic embedding CSR + keyword fallback")
