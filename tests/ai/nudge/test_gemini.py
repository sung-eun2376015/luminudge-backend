import json
import sys
from pathlib import Path

from ai.nudge.mission_generator import generate_mission


BASE_DIR = Path(__file__).resolve().parent
SAMPLE_DIR = BASE_DIR.parents[2] / "fixtures" / "nudge"
OUTPUT_DIR = BASE_DIR / "outputs"


def load_sample(sample_name: str):
    sample_path = SAMPLE_DIR / f"{sample_name}.json"

    if not sample_path.exists():
        raise FileNotFoundError(
            f"샘플 파일을 찾을 수 없습니다: {sample_path}\n"
            f"예: python test_gemini.py animal"
        )

    return json.loads(sample_path.read_text(encoding="utf-8"))


def save_result(sample_name: str, result):
    OUTPUT_DIR.mkdir(exist_ok=True)

    output_path = OUTPUT_DIR / f"{sample_name}_result.json"
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"저장 완료: {output_path}")


def main():
    if len(sys.argv) < 2:
        print("사용법: python test_gemini.py [샘플이름]")
        print("예시: python test_gemini.py animal")
        print("가능한 샘플: animal, color, number, dance, vague")
        sys.exit(1)

    sample_name = sys.argv[1]
    captions = load_sample(sample_name)

    result = generate_mission(
        captions=captions,
        child_tier="all",
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    save_result(sample_name, result)


if __name__ == "__main__":
    main()
