import os
from dotenv import load_dotenv
import requests

load_dotenv()

# --- Настройки ---
# ВАЖНО: Теперь здесь должен быть ТОКЕН ПОЛЬЗОВАТЕЛЯ-АДМИНИСТРАТОРА
ACCESS_TOKEN = os.environ.get("VK_GROUP_TOKEN")
GROUP_ID = int(os.environ.get("VK_GROUP_ID", "0"))
API_VERSION = "5.199"
PHOTO_PATH = "foto/cat26_16.jpg"   # Путь к фотографии
API_URL = "https://api.vk.ru/method/"


# ===== ФУНКЦИЯ ВЫЗОВА VK API =====

def vk_api(method, params):
    params["access_token"] = ACCESS_TOKEN
    params["v"] = API_VERSION

    response = requests.post(
        API_URL + method,
        data=params,
        timeout=30
    ).json()

    if "error" in response:
        raise Exception(response["error"])

    return response["response"]


# ===== ШАГ 1. ПОЛУЧАЕМ АДРЕС ЗАГРУЗКИ =====

upload_info = vk_api(
    "photos.getWallUploadServer",
    {"group_id": GROUP_ID}
)

upload_url = upload_info["upload_url"]


# ===== ШАГ 2. ЗАГРУЖАЕМ ФОТОГРАФИЮ =====

with open(PHOTO_PATH, "rb") as photo_file:
    upload_response = requests.post(
        upload_url,
        files={"photo": photo_file},
        timeout=120
    ).json()

if "error" in upload_response:
    raise Exception(upload_response["error"])


# ===== ШАГ 3. СОХРАНЯЕМ ФОТО В VK =====

saved_photos = vk_api(
    "photos.saveWallPhoto",
    {
        "group_id": GROUP_ID,
        "photo": upload_response["photo"],
        "server": upload_response["server"],
        "hash": upload_response["hash"]
    }
)

photo = saved_photos[0]

# Формируем идентификатор фотографии
attachment = f"photo{photo['owner_id']}_{photo['id']}"


# ===== ШАГ 4. ПУБЛИКУЕМ ПОСТ НА СТЕНЕ ГРУППЫ =====

result = vk_api(
    "wall.post",
    {
        "owner_id": -GROUP_ID,
        "from_group": 1,
        "message": "Новая фотография в нашей группе!",
        "attachments": attachment
    }
)

print("Фотография успешно опубликована!")
print("ID публикации:", result["post_id"])
