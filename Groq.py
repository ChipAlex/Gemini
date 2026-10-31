import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # загружает переменные из .env
#api_key = os.environ["GROQ_API_KEY"]

# Ключ берём на console.groq.com
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY")
)

response = client.chat.completions.create(
    model="openai/gpt-oss-120b",  # бесплатная модель Groq
    messages=[{"role": "user", "content": "Объясни, что такое Треш"}]
)

print(response.choices[0].message.content)