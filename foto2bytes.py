import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

#Вначале установить google-genai

load_dotenv()  # загружает переменные из .env

api_key = os.environ["GOOGLE_API_KEY"]
#Значение GOOGLE_API_KEY в .env

client = genai.Client(api_key=api_key)

client = genai.Client()

# 1. Прочитать локальное изображение в байты
image_path = "foto/abby.jpg"
with open(image_path, "rb") as f:
    image_bytes = f.read()

# 2. Создать Part из байтов, указав MIME-тип
image_part = types.Part.from_bytes(
    data=image_bytes,
    mime_type="image/jpeg"  # PNG: image/png, WEBP: image/webp
)

# 3. Отправить в модель вместе с текстовым запросом
response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents=[
        image_part,
        "Что изображено на этой фотографии? Опиши кратко."
    ],
)

print(response.text)