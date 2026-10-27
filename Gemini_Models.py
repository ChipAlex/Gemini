import os
from dotenv import load_dotenv
from google import genai
#**************Список моделей в genai

load_dotenv()  # загружает переменные из .env

api_key = os.environ["GOOGLE_API_KEY"]
#Значение GOOGLE_API_KEY в .env

client = genai.Client(api_key=api_key)

# Инициализация клиента (ключ можно передать явно)
client = genai.Client()
for model in client.models.list():
    print(model)

    pager = client.models.list(config={'page_size': 10})
    print(pager.page_size)
    print(pager[0])
    pager.next_page()
    print(pager[0])