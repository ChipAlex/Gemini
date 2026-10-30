import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # загружает переменные из .env

api_key = os.environ["OPENAI_API_KEY"]
#Значение OPENAI_API_KEY в .env

# Клиент автоматически прочитает переменную окружения OPENAI_API_KEY
client = OpenAI(api_key=api_key)

#Вариант 1
# response = client.responses.create(
#     model="gpt-4o",          # или "gpt-4o" и т.п.
#     instructions="Ты — полезный ассистент, отвечай кратко.",  # системная инструкция
#     input="Объясни в одном предложении, что такое рекурсия."
# )
#
# print(response.output_text)

#Вариант 2
completion = client.chat.completions.create(
    model="gpt-5.2",
    messages=[
        {"role": "developer", "content": "Ты — полезный ассистент."},
        {"role": "user", "content": "Объясни в одном предложении, что такое рекурсия."}
    ]
)

print(completion.choices[0].message.content)

"""You have no credits remaining"""