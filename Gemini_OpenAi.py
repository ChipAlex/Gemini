import os
from dotenv import load_dotenv
from openai import OpenAI

#from google import genai
#Вначале установить google-genai

load_dotenv()  # загружает переменные из .env

#api_key = os.environ["GOOGLE_API_KEY"]
#Значение GOOGLE_API_KEY в .env

#client = genai.Client(api_key=api_key)



# Ключ Groq получается на console.groq.com
client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.getenv("GOOGLE_API_KEY")
)

response = client.chat.completions.create(
    model="gemini-3.6-flash",
    messages=[{"role": "user", "content": "Привет, объясни рекурсию"}]
)

print(response.choices[0].message.content)