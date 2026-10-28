import os
from dotenv import load_dotenv
from google import genai
#Вначале установить google-genai

load_dotenv()  # загружает переменные из .env

api_key = os.environ["GOOGLE_API_KEY"]
#Значение GOOGLE_API_KEY в .env

client = genai.Client(api_key=api_key)

#from google.genai import types

# 1. Создайте клиент (ключ берётся из переменной окружения GEMINI_API_KEY)
client = genai.Client()

# 2. Загрузите локальное изображение через Files API
#    (подходит для большинства случаев, включая файлы > 20 MB)
uploaded_file = client.files.upload(file="foto/abby.jpg")

# 3. Отправьте изображение и текстовый запрос модели
response = client.models.generate_content(
    model="gemini-3.6-flash",  # или ваша модель, например gemini-3.6-flash
    contents=[
        uploaded_file,
        "Что изображено на этой фотографии? Опиши кратко.",
    ],
)

# 4. Выведите ответ
print(response.text)