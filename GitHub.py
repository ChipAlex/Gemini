import os
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()  # загружает переменные из .env


# Клиент указывает на эндпоинт GitHub Models
client = OpenAI(
    base_url="https://models.github.ai/inference",
    api_key=os.getenv("GITHUB_TOKEN"),
    default_query={"api-version": "2024-08-01-preview"}
)

# Запрос к модели (например, gpt-4o-mini — одна из доступных бесплатных моделей)
response = client.chat.completions.create(
    model="gpt-4o-mini",  # или "openai/gpt-4o", "meta-llama-3.1-8b-instruct" и т.д.
    messages=[{"role": "user", "content": "Привет!"}]
)

print(response.choices[0].message.content)
#print(response)
#print(type(response))