import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # загружает переменные из .env

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

response = client.chat.completions.create(
    model="openrouter/free",  # бесплатная модель OPENROUTER
    messages=[{"role": "user", "content": "Привет"}]
)

print(response.choices[0].message.content)