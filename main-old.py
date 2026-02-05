import os
import json
import requests
from requests.auth import HTTPDigestAuth
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler

# Определяем путь к конфигурационному файлу
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, 'config.json')

# Загружаем конфигурацию из JSON-файла
try:
    with open(config_path, 'r', encoding='utf-8') as config_file:
        config = json.load(config_file)
except Exception as e:
    print(f"Ошибка при загрузке конфигурации: {str(e)}")
    # Используем значения по умолчанию
    config = {
        "cameras": [],
        "logging": {
            "mode": "debug",
            "file": "traffic_log.log",
            "max_size_kb": 512,
            "backup_count": 1
        }
    }

# Извлекаем настройки логирования
logging_config = config.get("logging", {})
LOGGING_MODE = logging_config.get("mode", "debug")
LOG_FILE = logging_config.get("file", "traffic_log.log")
MAX_LOG_SIZE = logging_config.get("max_size_kb", 512) * 1024  # Конвертируем KB в байты
LOG_BACKUP_COUNT = logging_config.get("backup_count", 1)

# Извлекаем список камер
cameras = config.get("cameras", [])

# Настройка логгера
logger = logging.getLogger('TrafficLog')
logger.setLevel(logging.DEBUG)  # Логгер всегда принимает все уровни

# Форматтер для всех логов
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Обработчик для файла (с ротацией)
file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=MAX_LOG_SIZE,
    backupCount=LOG_BACKUP_COUNT,
    encoding='utf-8'
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Обработчик для консоли
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Установка уровня логирования для обработчиков
if LOGGING_MODE == 'debug':
    file_handler.setLevel(logging.DEBUG)
    console_handler.setLevel(logging.DEBUG)
else:  # production
    file_handler.setLevel(logging.INFO)
    console_handler.setLevel(logging.INFO)

def process_camera(camera):
    """
    Обрабатывает одну камеру: получает список пропусков, проверяет срок действия и удаляет просроченные.
    
    Args:
        camera (dict): Данные камеры для обработки
    """
    #camera_base_url = f"http://{camera['ip']}:{camera['port']}"
    camera_base_url = f"http://{camera['ip']}"
    #request_url = f"{camera_base_url}/cgi-bin/accessControl.cgi?action=getDoorStatus"
    #request_url = f"{camera_base_url}/cgi-bin/global.cgi?action=getCurrentTime"
    #request_url = f"{camera_base_url}/cgi-bin/accessControl.cgi?action=openDoor&channel=1&UserID=101&Type=Remote"
    #request_url = f"{camera_base_url}/cgi-bin/userManager.cgi?action=getUserInfoAll"
    request_url = f"{camera_base_url}/cgi-bin/eventManager.cgi?action=getExposureEvents"
    
    logger.info(f"\n===== Начало обработки камеры {camera['ip']}:{camera['port']} =====")
    logger.debug(f"Параметры подключения: {camera_base_url}, пользователь: {camera['username']}")
    logger.debug(f"URL для получения списка: {request_url}")
    
    # Получаем данные через Digest Auth
    logger.info("Выполняю запрос к камере")
    response = requests.get(request_url, auth=HTTPDigestAuth(camera['username'], camera['password']))
    
    # Логируем ответ
    logger.debug(f"HTTP-статус: {response.status_code}")
    logger.debug(f"Заголовки ответа: {response.headers}")
    logger.debug(f"Текст ответа: {response.text}")
 

def main():
    """Основная функция программы"""
    # Логируем старт работы
    logger.debug(f"Режим логирования: {LOGGING_MODE}")
    
    # Обрабатываем каждую камеру
    for camera in cameras:
        try:
            process_camera(camera)
        except Exception as e:
            logger.exception(f"Критическая ошибка при обработке камеры {camera['ip']}:{camera['port']}: {str(e)}")
            logger.error(f"===== Обработка камеры {camera['ip']}:{camera['port']} завершена с ошибкой =====")
    
    logger.info("===== Работа скрипта завершена =====")


if __name__ == "__main__":
    main()