import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # загружает переменные из .env

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

response = client.chat.completions.create(
    # Бесплатная модель Qwen на OpenRouter
    model="qwen/qwen3-next-80b-a3b-instruct:free",
    messages=[{"role": "user", "content": "Привет! Объясни, что такое API."}]
)

print(response.choices[0].message.content)


#В данный момент нет free моделей