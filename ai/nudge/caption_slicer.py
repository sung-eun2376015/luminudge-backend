from typing import Dict, List, Tuple


Caption = Dict[str, object]


VAGUE_PHRASES = [
    "우와",
    "와",
    "멋지다",
    "잘했어요",
    "좋아요",
    "다음에는 무엇이 나올까요",
    "무엇이 나올까요",
    "볼까요",
    "가볼까요",
]


CLEAR_KEYWORDS = [
    "토끼",
    "강아지",
    "고양이",
    "새",
    "동물",
    "사과",
    "바나나",
    "빨간",
    "파란",
    "노란",
    "색",
    "하나",
    "둘",
    "셋",
    "숫자",
    "깡충",
    "뛰",
    "날아",
    "춤",
    "박수",
    "손",
]


def slice_captions_by_time(
    captions: List[Caption],
    current_time: float,
    current_window_sec: float = 12.0,
    previous_window_sec: float = 25.0,
) -> Tuple[List[Caption], List[Caption]]:
    """
    자막 타임라인과 현재 영상 시간을 기준으로
    current_captions와 previous_captions를 나눈다.

    current_captions:
    - current_time 직전 current_window_sec 초 안에 있는 자막
    - 현재 장면 또는 막 지나간 장면을 나타냄

    previous_captions:
    - current_captions보다 더 이전에 나온 명확한 장면 후보
    - current_time 직전 previous_window_sec 초 범위에서 current 구간을 제외한 자막
    """

    current_start = max(0, current_time - current_window_sec)
    previous_start = max(0, current_time - previous_window_sec)

    current_captions = []
    previous_captions = []

    for caption in captions:
        start = float(caption.get("start", 0))
        end = float(caption.get("end", start))

        # 현재 시간 이후의 자막은 아직 보지 않은 내용이므로 제외
        if start > current_time:
            continue

        # 현재 구간: current_time 직전 current_window_sec 초 안에 걸친 자막
        if end >= current_start and start <= current_time:
            current_captions.append(caption)

        # 이전 구간: previous_window_sec 안에는 있지만 current 구간보다 앞선 자막
        elif end >= previous_start and end < current_start:
            previous_captions.append(caption)

    return current_captions, previous_captions


def captions_to_text(captions: List[Caption]) -> str:
    """
    자막 리스트를 Gemini에 넣기 좋은 하나의 문자열로 합친다.
    """
    return " ".join(str(caption.get("text", "")).strip() for caption in captions).strip()


def has_clear_context(text: str) -> bool:
    """
    자막 안에 동물, 색, 숫자, 동작처럼
    미션으로 만들기 좋은 단서가 있는지 확인한다.
    """

    normalized_text = text.replace(" ", "")

    for keyword in CLEAR_KEYWORDS:
        if keyword in normalized_text:
            return True

    return False


def is_mostly_vague(text: str) -> bool:
    """
    자막이 감탄사, 전환 문장, 의미가 약한 문장 위주인지 확인한다.
    """

    normalized_text = text.replace(" ", "")

    if not normalized_text:
        return True

    has_vague_phrase = any(
        phrase.replace(" ", "") in normalized_text
        for phrase in VAGUE_PHRASES
    )

    has_clear_keyword = has_clear_context(normalized_text)

    # 명확한 키워드가 있으면 애매한 자막으로 보지 않는다.
    if has_clear_keyword:
        return False

    return has_vague_phrase


def choose_context_source(
    current_captions: List[Caption],
    previous_captions: List[Caption],
) -> str:
    """
    current와 previous 자막을 보고 어떤 맥락을 Gemini에 우선 사용할지 추천한다.

    판단 기준:
    - 가장 최근 current 자막이 명확하면 current
    - 가장 최근 current 자막이 애매하면 previous
    - previous도 명확하지 않으면 generic

    반환값:
    - current: 현재 자막이 명확함
    - previous: 현재 자막은 애매하지만 직전 자막이 명확함
    - generic: 둘 다 명확하지 않아 일반 참여 미션이 적절함
    """

    current_text = captions_to_text(current_captions)
    previous_text = captions_to_text(previous_captions)

    latest_current_text = ""

    if current_captions:
        latest_current_text = str(current_captions[-1].get("text", "")).strip()

    # 가장 최근 자막이 명확하면 현재 장면을 사용한다.
    if latest_current_text and not is_mostly_vague(latest_current_text):
        return "current"

    # 가장 최근 자막이 애매해도, current 전체가 명확하고
    # previous가 비어 있다면 current를 사용할 수밖에 없다.
    if current_text and not is_mostly_vague(current_text) and not previous_text:
        return "current"

    # 최근 자막이 애매하면 직전 명확한 장면을 사용한다.
    if previous_text and not is_mostly_vague(previous_text):
        return "previous"

    return "generic"


def build_caption_context(
    captions: List[Caption],
    current_time: float,
    current_window_sec: float = 12.0,
    previous_window_sec: float = 25.0,
) -> Dict[str, object]:
    """
    Gemini 미션 생성에 넘기기 좋은 입력 구조를 만든다.
    """

    current_captions, previous_captions = slice_captions_by_time(
        captions=captions,
        current_time=current_time,
        current_window_sec=current_window_sec,
        previous_window_sec=previous_window_sec,
    )

    context_source = choose_context_source(
        current_captions=current_captions,
        previous_captions=previous_captions,
    )

    current_text = captions_to_text(current_captions)
    previous_text = captions_to_text(previous_captions)

    if context_source == "current":
        selected_context_text = current_text
    elif context_source == "previous":
        selected_context_text = previous_text
    else:
        selected_context_text = ""

    return {
        "current_time": current_time,
        "current_captions": current_captions,
        "previous_captions": previous_captions,
        "current_text": current_text,
        "previous_text": previous_text,
        "selected_context_text": selected_context_text,
        "suggested_context_source": context_source,
    }