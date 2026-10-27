import os
from dotenv import load_dotenv
from google import genai
from google.genai import types


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

# 3. Передайте саму функцию в tools (не JSON-объявление)
config = types.GenerateContentConfig(
    tools=[get_current_temperature]
)

# 4. Отправьте запрос
response = client.models.generate_content(
    model="models/gemini-3.6-flash",
    contents="Какая температура в Бостоне?",
    config=config,
)

# SDK автоматически вызывает функцию и передаёт результат обратно модели, в итоге возвращая текст
print(response.text)

"""Работае, но выдает предупреждение:
Direct use of automatic function calling (AFC) in Models.generate_content is not recommended. 
Instead, we recommend to use AFC in Chat.send_message. Similarly, 
direct use of AFC in Models.generate_content_stream is not recommended. 
Instead, we recommend to use AFC in Chat.send_message_stream.
"""