import math
import os
from dataclasses import dataclass
from typing import Any, Callable

from dotenv import load_dotenv
from google import genai
from google.genai import types

from ai.nudge.stt_csr import calculate_keyword_overlap_csr, extract_expected_keywords


EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSION = 768
EmbeddingFunction = Callable[[list[str]], list[list[float]]]


@dataclass
class SemanticCSRResult:
    csr_score: float
    method: str
    expected_text: str
    fallback_reason: str | None = None


def build_expected_text(mission: dict[str, Any]) -> str:
    """Build a short reference answer that can be compared with the transcript."""
    answer = str(mission.get("answer") or "").strip()
    if answer and answer != "없음":
        return answer

    expected_keywords = extract_expected_keywords(mission)
    return " ".join(expected_keywords).strip()


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        raise ValueError("임베딩 벡터의 길이가 올바르지 않습니다")

    dot_product = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        raise ValueError("임베딩 벡터의 크기는 0일 수 없습니다")

    # 부동소수점 오차로 범위를 아주 조금 벗어나는 경우를 보정한다.
    return max(-1.0, min(1.0, dot_product / (left_norm * right_norm)))


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Create semantic-similarity embeddings with the existing Gemini API key."""
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(".env 파일에 GEMINI_API_KEY가 없습니다.")

    client = genai.Client(api_key=api_key)
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type="SEMANTIC_SIMILARITY",
            output_dimensionality=EMBEDDING_DIMENSION,
        ),
    )

    embeddings = response.embeddings or []
    vectors = [list(embedding.values or []) for embedding in embeddings]
    if len(vectors) != len(texts) or any(not vector for vector in vectors):
        raise ValueError("Gemini 임베딩 응답이 올바르지 않습니다")
    return vectors


def calculate_semantic_csr(
    transcript: str,
    mission: dict[str, Any],
    embedder: EmbeddingFunction | None = None,
) -> SemanticCSRResult:
    """
    Compare the child's transcript with the expected answer semantically.

    Gemini/API failure falls back to the existing keyword-overlap CSR so a
    temporary external failure does not break the mission response endpoint.
    """
    normalized_transcript = transcript.strip()
    expected_text = build_expected_text(mission)
    expected_keywords = extract_expected_keywords(mission)

    if not normalized_transcript or not expected_text:
        keyword_score, _, _ = calculate_keyword_overlap_csr(
            normalized_transcript,
            expected_keywords,
        )
        return SemanticCSRResult(
            csr_score=keyword_score,
            method="keyword_fallback",
            expected_text=expected_text,
            fallback_reason="비교할 답변 또는 기대 답변이 없습니다",
        )

    embedding_function = embedder or embed_texts
    try:
        transcript_vector, expected_vector = embedding_function(
            [normalized_transcript, expected_text]
        )
        # CSR API 계약은 0~1이므로 음수 유사도는 0으로 보정한다.
        score = max(0.0, cosine_similarity(transcript_vector, expected_vector))
        return SemanticCSRResult(
            csr_score=round(score, 3),
            method="semantic_embedding",
            expected_text=expected_text,
        )
    except Exception as error:
        keyword_score, _, _ = calculate_keyword_overlap_csr(
            normalized_transcript,
            expected_keywords,
        )
        return SemanticCSRResult(
            csr_score=keyword_score,
            method="keyword_fallback",
            expected_text=expected_text,
            fallback_reason=str(error),
        )
