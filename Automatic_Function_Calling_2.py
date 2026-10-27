import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
#import requests


# 1. Определите функцию с аннотациями типов и docstring
def get_current_temperature(location: str) -> dict:
    """Получает текущую температуру для указанного местоположения.

    Args:
        location: Город и штат, например, San Francisco, CA.
    """
    # Здесь для примера возвращается фиксированное значение, в реальности можно вызвать API погоды
    return {"temperature": 25, "unit": "Celsius"}

# 2. Настройте клиент (не забудьте установить переменную окружения GEMINI_API_KEY)

load_dotenv()  # загружает переменные из .env

api_key = os.environ["GOOGLE_API_KEY"]
#Значение GOOGLE_API_KEY в .env

client = genai.Client(api_key=api_key)

#***************



#***************

# 3. Создайте чат-сессию и передайте инструменты в config
chat = client.chats.create(
    model="models/gemini-3.6-flash",  # используйте вашу модель
    config=types.GenerateContentConfig(
        tools=[get_current_temperature]
    )
)

# 4. Отправьте сообщение через chat.send_message, SDK автоматически завершит цикл вызова функций
response = chat.send_message("Какая температура в Бостоне?")
print(response.text)

