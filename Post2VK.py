import os
from dotenv import load_dotenv
import vk_api
from vk_api.utils import get_random_id

load_dotenv()  # загружает переменные из .env



# --- Настройки ---
TOKEN=os.environ.get("VK_GROUP_TOKEN")
GROUP_ID = os.environ.get("VK_GROUP_ID")
#TOKEN = VK_GROUP_TOKEN
#GROUP_ID = -158296331  # ID вашей группы (обязательно с минусом!)
POST_TEXT = "Привет, сообщество! Это тестовый пост из P-n."

def main():
    # Авторизация
    vk_session = vk_api.VkApi(token=TOKEN)
    vk = vk_session.get_api()

    try:
        # Публикация поста
        response = vk.wall.post(
            owner_id=GROUP_ID,          # Стена группы (с минусом)
            from_group=1,               # Опубликовать от имени группы
            message=POST_TEXT,          # Текст поста
            random_id=get_random_id()   # Защита от дублирования
        )
        print(f"✅ Пост опубликован! ID записи: {response['post_id']}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()