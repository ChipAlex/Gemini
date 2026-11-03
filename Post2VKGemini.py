import os
from dotenv import load_dotenv
import requests

load_dotenv()  # загружает переменные из .env

# --- Настройки ---
TOKEN=os.environ.get("VK_GROUP_TOKEN")
GROUP_ID = int(os.environ.get("VK_GROUP_ID", "0"))
API_VERSION = "5.199"          # Актуальная версия API

# Сразу проверяем, прочитались ли данные из .env
if not TOKEN:
    raise ValueError("Критическая ошибка: Переменная VK_GROUP_TOKEN не найдена в .env или пуста!")
if GROUP_ID == 0:
    raise ValueError("Критическая ошибка: Переменная VK_GROUP_ID не найдена в .env или равна 0!")


def post_to_wall(message: str, attachments: str = None):
    """Публикует запись на стену сообщества."""
    url = "https://vk.com/lip_faberlic"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    # Все параметры для VK API передаем строго в Query String
    query_params = {
        "access_token": TOKEN,
        "v": API_VERSION,
        "owner_id": -GROUP_ID,  # Минус обязателен для групп
        "from_group": 1,
        "message": message,
    }

    if attachments:
        query_params["attachments"] = attachments

    # ИСПРАВЛЕНО: Вместо data=params используем params=query_params
    res = requests.post(url, params=query_params, headers=headers)

    print(f"Статус-код: {res.status_code}")
    print(f"Тип контента: {res.headers.get('Content-Type')}")

    try:
        response = res.json()
    except requests.exceptions.JSONDecodeError:
        print("!!! СЕРВЕР ВСЕ ЕЩЕ ВЕРНУЛ НЕ JSON !!!")
        print(res.text[:500])
        return

    if "response" in response:
        print(f"Успешно опубликовано! ID поста: {response['response']['post_id']}")
    else:
        error_msg = response.get("error", {}).get("error_msg", "Неизвестная ошибка")
        error_code = response.get("error", {}).get("error_code", "Нет кода")
        print(f"Ошибка VK API #{error_code}: {error_msg}")


if __name__ == "__main__":
    post_to_wall("Привет! Это автоматический пост на стене группы.")

# # --- ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ ---
#
# # Пример 1: Обычный текстовый пост
# post_to_wall("Привет! Это автоматический пост на стене группы.")
#
# # Пример 2: Пост со ссылкой или уже загруженной во ВК картинкой
# # Формат вложений для фото: photo<owner_id>_<photo_id>
# post_to_wall(
#     message="Пост с прикрепленным фото и ссылкой!",
#     attachments="photo-215838550_457239021,https://ya.ru"
# )
