import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # загружает переменные из .env

# 1. Словарь с настройками для каждого провайдера
PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key": os.getenv("GROQ_API_KEY"),
        "model": "openai/gpt-oss-120b",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": os.getenv("GOOGLE_API_KEY"),
        "model": "gemini-3.6-flash",  # или другая доступная модель
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "model": "openrouter/free",
    },
}


def ask(provider_name: str, prompt: str) -> str:
    """Отправляет запрос выбранному провайдеру и возвращает ответ."""
    cfg = PROVIDERS[provider_name]

    client = OpenAI(
        base_url=cfg["base_url"],
        api_key=cfg["api_key"],
    )

    response = client.chat.completions.create(
        model=cfg["model"],
        messages=[{"role": "user", "content": prompt}],
    )

    return response.choices[0].message.content


# 2. Пример использования: сравнение ответов
prompt = "Объясни в одном предложении, что такое треугольник."

for name in ["groq", "gemini", "openrouter"]:
    print(f"\n--- {name} ---")
    try:
        print(ask(name, prompt))
    except Exception as e:
        print(f"Ошибка: {e}")