import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai


BASE_DIR = Path(__file__).resolve().parent


def load_prompt() -> str:
    path = BASE_DIR / "mission_prompt.txt"
    return path.read_text(encoding="utf-8")


def clean_json_text(raw_text: str) -> str:
    text = raw_text.strip()

    if text.startswith("```json"):
        text = text.replace("```json", "", 1).strip()

    if text.startswith("```"):
        text = text.replace("```", "", 1).strip()

    if text.endswith("```"):
        text = text[:-3].strip()

    return text


def build_user_input(
    captions: list[dict[str, Any]] | None = None,
    child_tier: str = "all",
    previous_response: dict[str, Any] | None = None,
    current_captions: list[dict[str, Any]] | None = None,
    previous_captions: list[dict[str, Any]] | None = None,
    current_text: str = "",
    previous_text: str = "",
    selected_context_text: str = "",
    suggested_context_source: str = "current",
) -> dict[str, Any]:
    """
    Gemini에 전달할 입력 데이터를 만든다.

    1주차 호환:
    - captions만 넘겨도 작동한다.

    2주차 확장:
    - current_captions / previous_captions
    - current_text / previous_text
    - selected_context_text
    - suggested_context_source
    """

    return {
        "child_tier": child_tier,
        "previous_response": previous_response,
        "captions": captions or [],
        "current_captions": current_captions or captions or [],
        "previous_captions": previous_captions or [],
        "current_text": current_text,
        "previous_text": previous_text,
        "selected_context_text": selected_context_text or current_text,
        "suggested_context_source": suggested_context_source,
    }


def generate_mission(
    captions: list[dict[str, Any]] | None = None,
    child_tier: str = "all",
    previous_response: dict[str, Any] | None = None,
    current_captions: list[dict[str, Any]] | None = None,
    previous_captions: list[dict[str, Any]] | None = None,
    current_text: str = "",
    previous_text: str = "",
    selected_context_text: str = "",
    suggested_context_source: str = "current",
) -> dict[str, Any]:
    """
    유튜브 자막과 아이 티어 정보를 받아 루미 미션 JSON을 생성한다.
    """

    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(".env 파일에 GEMINI_API_KEY가 없습니다.")

    client = genai.Client(api_key=api_key)

    system_prompt = load_prompt()
    user_input = build_user_input(
        captions=captions,
        child_tier=child_tier,
        previous_response=previous_response,
        current_captions=current_captions,
        previous_captions=previous_captions,
        current_text=current_text,
        previous_text=previous_text,
        selected_context_text=selected_context_text,
        suggested_context_source=suggested_context_source,
    )

    prompt = f"""
{system_prompt}

입력 데이터:
{json.dumps(user_input, ensure_ascii=False, indent=2)}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    raw_text = response.text.strip()
    cleaned_text = clean_json_text(raw_text)

    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError as error:
        raise ValueError(
            "Gemini 출력이 JSON 형식이 아닙니다.\n"
            f"원본 출력:\n{raw_text}"
        ) from error