import sys
import time

from google import genai
from google.genai import types

from app.config import settings


def main(models: list[str]) -> None:
    if not settings.gemini_api_key:
        sys.exit("GEMINI_API_KEY не задан в .env")
    client = genai.Client(api_key=settings.gemini_api_key)
    for model in models:
        for attempt in range(1, 4):
            started = time.perf_counter()
            try:
                response = client.models.generate_content(
                    model=model,
                    contents="Ответь одним словом: привет",
                    config=types.GenerateContentConfig(max_output_tokens=50),
                )
                took = time.perf_counter() - started
                print(f"{model} #{attempt}: {took:.1f} с, ответ: {(response.text or '').strip()[:40]!r}")
            except Exception as exc:
                took = time.perf_counter() - started
                print(f"{model} #{attempt}: ошибка через {took:.1f} с: {type(exc).__name__}")


if __name__ == "__main__":
    main(sys.argv[1:] or [settings.gemini_model])
