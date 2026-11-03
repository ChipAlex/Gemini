import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # загружает переменные из .env

#Вариант 1 Работает ****************
# client = OpenAI(
#     base_url="https://openrouter.ai/api/v1",
#     api_key=os.getenv("OPENROUTER_API_KEY")
# )
#
# response = client.chat.completions.create(
#     model="openrouter/free",  # бесплатная модель OPENROUTER
#     messages=[{"role": "user", "content": "Привет"}]
# )
#
# print(response.choices[0].message.content)


#********Вариант 2 Работает *****************
# 1. Инициализация клиента OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
)

# 2. Вызов бесплатной модели
completion = client.chat.completions.create(
    # Опциональные, но рекомендуемые заголовки для OpenRouter
    # (помогают в рейтингах и обходе жестких лимитов)
    extra_headers={
        "HTTP-Referer": "https://ru48.ru",
        "X-Title": "My Python AI App",
    },

    # Указываем бесплатную модель (обязательно с суффиксом :free)
    model="openrouter/free",

    messages=[
        {
            "role": "system",
            "content": "Ты полезный AI-ассистент. Отвечай кратко и по делу."
        },
        {
            "role": "user",
            "content": "Что такое четырехугольник?"
        }
    ],
)

# 3. Вывод ответа
print(completion.choices[0].message.content)