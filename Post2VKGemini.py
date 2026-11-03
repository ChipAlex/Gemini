import os
from dotenv import load_dotenv
import requests

load_dotenv()  # загружает переменные из .env

# --- Настройки ---
#    url = "https://vk.com/lip_faberlic"

TOKEN=os.environ.get("VK_GROUP_TOKEN")
GROUP_ID = int(os.environ.get("VK_GROUP_ID", "0"))
API_VERSION = "5.199"          # Актуальная версия API

# Сразу проверяем, прочитались ли данные из .env
if not TOKEN:
    raise ValueError("Критическая ошибка: Переменная VK_GROUP_TOKEN не найдена в .env или пуста!")
if GROUP_ID == 0:
    raise ValueError("Критическая ошибка: Переменная VK_GROUP_ID не найдена в .env или равна 0!")


def post_to_wall(message: str, attachments: str = None):
    """Публикует запись на стену сообщества, передавая токен прямо в URL."""
    clean_token = TOKEN.strip()

    # ИСПРАВЛЕНО: Токен и версия API намертво вшиваются прямо в строку URL
    url = f"https://vk.com/lip_faberlic{clean_token}&v={API_VERSION}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    # Данные поста передаются в теле POST-запроса
    payload = {
        "owner_id": -GROUP_ID,
        "from_group": 1,
        "message": message,
    }

    if attachments:
        payload["attachments"] = attachments

    # Отправляем POST запрос. Параметры авторизации в URL, данные - в data
    res = requests.post(url, data=payload, headers=headers)

    try:
        response = res.json()
    except requests.exceptions.JSONDecodeError:
        print("!!! КРИТИЧЕСКАЯ ОШИБКА: VK всё ещё сбрасывает запрос в HTML !!!")
        print(res.text[:300])
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
