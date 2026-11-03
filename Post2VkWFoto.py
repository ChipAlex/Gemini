import os
from dotenv import load_dotenv
import vk_api
from vk_api import VkUpload
from vk_api.utils import get_random_id

load_dotenv()  # загружает переменные из .env
й = VKWebAppGetCommunityToken()
# --- Настройки ---
TOKEN=os.environ.get("VK_GROUP_TOKEN")
#TOKEN = VK_GROUP_TOKEN
#GROUP_ID = -158296331  # ID вашей группы (обязательно с минусом!)
#GROUP_ID = os.environ.get("VK_GROUP_ID")
GROUP_ID = int(os.environ.get("VK_GROUP_ID", "0"))
POST_TEXT = "Добрый вечер"

def main():
    vk_session = vk_api.VkApi(token=TOKEN)
    vk = vk_session.get_api()
    upload = VkUpload(vk_session)

    # 1. Загружаем фото на сервер VK (в системный альбом)
    # Передаём путь к файлу и ID группы (без минуса)
    #q=abs(int(GROUP_ID))

    photo = upload.photo_wall(
        photos="foto/cat26_16.jpg",
        group_id=GROUP_ID
    )

    # 2. Формируем строку вложения
    # photo[0] содержит owner_id и id загруженного фото
    attachment = f"photo{photo[0]['owner_id']}_{photo[0]['id']}"

    # 3. Публикуем пост с вложением
    response = vk.wall.post(
        owner_id=-GROUP_ID,
        from_group=1,
        message=POST_TEXT,
        attachments=attachment,
        random_id=get_random_id()
    )
    print(f"Пост с фото опубликован! ID: {response['post_id']}")

if __name__ == "__main__":
    main()
