import os
from dotenv import load_dotenv
from google import genai
#Вначале установить google-genai

load_dotenv()  # загружает переменные из .env

api_key = os.environ["GOOGLE_API_KEY"]
#Значение GOOGLE_API_KEY в .env

client = genai.Client(api_key=api_key)

#Инициализация клиента (ключ можно передать явно)
client = genai.Client()


# Отправка запроса
"""Работают: models/gemini-3.6-flash, 
    models/gemini-3.8-flash,
    gemini-flash-latest актуальная быстрая модель, но проходит не всегда
"""
response = client.models.generate_content(
#model="gemini-flash-latest",  # актуальная быстрая модель, но проходит не всегда

model="models/gemini-3.6-flash",
contents="Действуй как автор контента. Напиши вступление на 150 слов для поста в блоге о преимуществах утренних прогулок. Используй теплый, разговорный тон"
)

# Вывод ответа
print(response.text)



#if __name__ == '__main__':
#    mk_unswer()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
