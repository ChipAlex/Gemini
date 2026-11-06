import os
from dotenv import load_dotenv
import requests
import vk_api

load_dotenv()

# --- Настройки ---
# ВАЖНО: Теперь здесь должен быть ТОКЕН ПОЛЬЗОВАТЕЛЯ-АДМИНИСТРАТОРА
TOKEN = os.environ.get("VK_GROUP_TOKEN")
GROUP_ID = int(os.environ.get("VK_GROUP_ID", "0"))
API_VERSION = "5.199"


def upload_photo(vk, photo_path: str) -> str:
    """Загружает локальное фото на сервер ВК от имени администратора."""
    if not os.path.exists(photo_path):
        raise FileNotFoundError(f"Файл по пути {photo_path} не найден!")

    # ИСПРАВЛЕНО: Передаем group_id, чтобы пользовательский токен знал, куда загружать
    upload_server = vk.photos.getWallUploadServer(group_id=GROUP_ID)
    upload_url = upload_server["upload_url"]

    # Отправляем файл на сервер ВК
    with open(photo_path, "rb") as photo_file:
        files = {"photo": photo_file}
        upload_response = requests.post(upload_url, files=files).json()

    # Сохраняем фото на стене группы
    save_response = vk.photos.saveWallPhoto(
        group_id=GROUP_ID,
        photo=upload_response["photo"],
        server=upload_response["server"],
        hash=upload_response["hash"],
    )[0] # Метод возвращает список, берем первый элемент

    # Формируем строку вложения
    attachment = f"photo{save_response['owner_id']}_{save_response['id']}"
    return attachment


def post_to_wall(message: str, photo_path: str = None):
    """Публикует запись на стену сообщества от лица администратора."""
    try:
        vk_session = vk_api.VkApi(token=TOKEN.strip(), api_version=API_VERSION)
        vk = vk_session.get_api()

        attachments = []

        if photo_path:
            print(f"Загружаю фото: {photo_path}...")
            photo_attachment = upload_photo(vk, photo_path)
            attachments.append(photo_attachment)

        params = {
            "owner_id": -GROUP_ID, # Публикуем в группу (минус обязателен)
            "from_group": 1,       # 1 - от имени группы, 0 - от имени пользователя
            "message": message,
        }

        if attachments:
            params["attachments"] = ",".join(attachments)

        response = vk.wall.post(**params)
        print(f"Успешно опубликовано от имени группы! ID поста: {response.get('post_id')}")

    except vk_api.exceptions.ApiError as error:
        # ИСПРАВЛЕНО: Правильное чтение ошибки из объекта ApiError в vk_api
        print(f"Ошибка VK API #{error.code}: {error.error.get('error_msg')}")
    except Exception as e:
        print(f"Произошла системная ошибка: {e}")


if __name__ == "__main__":
    PATH_TO_IMAGE = "foto/cat26_16.jpg"

    post_to_wall(
        message="Привет! Это автоматический пост с картинкой через токен администратора.",
        photo_path=PATH_TO_IMAGE,
    )
