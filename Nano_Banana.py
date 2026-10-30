import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

#Вначале установить google-genai

load_dotenv()  # загружает переменные из .env

api_key = os.environ["GOOGLE_API_KEY"]
#Значение GOOGLE_API_KEY в .env

client = genai.Client(api_key=api_key)

#from google import genai
#from google.genai import types

client = genai.Client()

# 1. Загружаем исходное изображение
with open("foto/abby.jpg", "rb") as f:
    image_bytes = f.read()

# 2. Формулируем инструкцию для редактирования
prompt = """
Using the provided image, replace the color of this bra and panties to green
"""

# 3. Отправляем запрос модели редактирования изображений
response = client.models.generate_content(
    model="models/gemini-2.5-flash-image",  # или "gemini-3.1-flash-image"
    contents=[
        types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
        prompt,
    ],
)

# 4. Извлекаем и сохраняем результат
for part in response.parts:
    if part.inline_data is not None:
        # part.as_image() возвращает объект PIL.Image
        image = part.as_image()
        image.save("edited_photo.png")
        print("Готово: edited_photo.png")
        break
else:
    print("Модель не вернула изображение. Ответ:", response.text)

"""
Выдает ошибку по лимитам
"""