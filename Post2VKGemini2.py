import os
from dotenv import load_dotenv
import vk_api

load_dotenv()  # загружает переменные из .env

# --- Настройки ---
#    url = "https://vk.com/lip_faberlic"

# --- Настройки ---
TOKEN = os.environ.get("VK_GROUP_TOKEN")
GROUP_ID = int(os.environ.get("VK_GROUP_ID", "0"))
API_VERSION = "5.199"

if not TOKEN:
    raise ValueError("Критическая ошибка: VK_GROUP_TOKEN не найден в .env!")
if GROUP_ID == 0:
    raise ValueError("Критическая ошибка: VK_GROUP_ID не найден в .env!")

def post_to_wall(message: str, attachments: str = None):
    """Публикует запись на стену сообщества через официальный SDK."""
    try:
        # Инициализируем сессию VK с использованием токена
        vk_session = vk_api.VkApi(token=TOKEN.strip(), api_version=API_VERSION)

        # Получаем объект для работы с методами API
        vk = vk_session.get_api()

        # Формируем параметры запроса
        params = {
            "owner_id": -GROUP_ID,  # Минус для сообществ
            "from_group": 1,        # От имени сообщества
            "message": message
        }

        if attachments:
            params["attachments"] = attachments

        # Вызываем метод wall.post напрямую как функцию Python
        response = vk.wall.post(**params)

        print(f"Успешно опубликовано! ID поста: {response.get('post_id')}")

    except vk_api.exceptions.ApiError as error:
        # Этот блок перехватит официальную ошибку от VK API
        print(f"Ошибка VK API #{error.code}: {error.message}")
    except Exception as e:
        # Этот блок перехватит другие ошибки (например, проблемы с сетью)
        print(f"Произошла системная ошибка: {e}")

if __name__ == "__main__":
    post_to_wall("Привет! Это автоматический пост через официальный SDK.")
