import logging
import requests
from requests.auth import HTTPDigestAuth
from datetime import datetime

# Настройка логгера
logger = logging.getLogger("dahua_camera")
logger.setLevel(logging.DEBUG)

_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(_fmt)

_file_handler = logging.FileHandler("camera.log", encoding="utf-8")
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(_fmt)

logger.addHandler(_console_handler)
logger.addHandler(_file_handler)


class DahuaCamera:
    def __init__(self, ip, username, password):
        self.ip = ip
        self.username = username
        self.password = password
        self.base_url = f"http://{ip}/cgi-bin"
        self.session = requests.Session()
        logger.info("Инициализация камеры: ip=%s, user=%s", ip, username)

    def get_current_time(self):
        """
        Получить текущее время камеры

        Returns:
            dict: Словарь с результатами:
                - success (bool): Успешность операции
                - camera_time (str): Время камеры в формате "yyyy-mm-dd hh:mm:ss"
                - raw_response (str): Сырой ответ от камеры
                - local_time (str): Текущее локальное время для сравнения
        """
        url = f"{self.base_url}/global.cgi?action=getCurrentTime"
        logger.debug("Запрос времени камеры: GET %s", url)

        try:
            response = self.session.get(
                url,
                auth=HTTPDigestAuth(self.username, self.password),
                timeout=5
            )

            if response.status_code == 200:
                camera_time = response.text.strip()

                try:
                    datetime.strptime(camera_time, "%Y-%m-%d %H:%M:%S")
                    is_valid = True
                except ValueError:
                    is_valid = False

                result = {
                    "success": True,
                    "camera_time": camera_time,
                    "raw_response": response.text,
                    "local_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "is_valid_format": is_valid
                }

                if is_valid:
                    logger.info("Время камеры получено: %s", camera_time)
                else:
                    logger.warning("Время камеры в нестандартном формате: %s", camera_time)

                return result
            else:
                logger.error(
                    "Ошибка получения времени: HTTP %s — %s",
                    response.status_code, response.text.strip()
                )
                return {
                    "success": False,
                    "error_code": response.status_code,
                    "error_message": response.text.strip()
                }

        except requests.exceptions.Timeout:
            logger.error("Таймаут подключения к камере (get_current_time)")
            return {"success": False, "error": "timeout"}
        except requests.exceptions.ConnectionError:
            logger.error("Ошибка подключения к камере (get_current_time)")
            return {"success": False, "error": "connection_error"}
        except Exception as e:
            logger.exception("Неизвестная ошибка в get_current_time: %s", e)
            return {"success": False, "error": str(e)}

    def open_strobe(self, channel=1, plate_number="", open_type="Normal"):
        '''
        Открыть стробоскоп/ворота через Traffic Snap API

        Args:
            channel: канал
            plate_number: номер распознанного авто
            open_type: "Normal", "Emergency" и т.д.
        '''
        url = f"{self.base_url}/trafficSnap.cgi"
        params = {
            "action": "openStrobe",
            "channel": channel,
            "info.openType": open_type,
            "info.plateNumber": plate_number
        }
        logger.info(
            "Открытие ворот: channel=%s, plate='%s', type=%s",
            channel, plate_number, open_type
        )
        logger.debug("Запрос openStrobe: GET %s params=%s", url, params)

        try:
            response = self.session.get(
                url,
                params=params,
                auth=HTTPDigestAuth(self.username, self.password),
                timeout=5
            )

            if response.status_code == 200 and response.text.strip() == "OK":
                logger.info("Ворота открыты (plate='%s')", plate_number)
                return True
            else:
                logger.error(
                    "Не удалось открыть ворота: HTTP %s — %s",
                    response.status_code, response.text.strip()
                )
                return False

        except requests.exceptions.Timeout:
            logger.error("Таймаут подключения к камере (open_strobe)")
            return False
        except requests.exceptions.ConnectionError:
            logger.error("Ошибка подключения к камере (open_strobe)")
            return False
        except Exception as e:
            logger.exception("Неизвестная ошибка в open_strobe: %s", e)
            return False


# Пример использования
if __name__ == "__main__":
    CAMERA_IP = "192.168.84.2"
    USERNAME = "admin"
    PASSWORD = "Donsmart2019"

    logger.info("=== Запуск программы управления камерой ===")
    camera = DahuaCamera(CAMERA_IP, USERNAME, PASSWORD)

    # Получение текущего времени камеры
    logger.info("=== Получение времени камеры ===")
    result = camera.get_current_time()

    if result["success"]:
        logger.info("Время камеры: %s", result["camera_time"])
        logger.info("Локальное время: %s", result["local_time"])

        try:
            cam_dt = datetime.strptime(result["camera_time"], "%Y-%m-%d %H:%M:%S")
            local_dt = datetime.strptime(result["local_time"], "%Y-%m-%d %H:%M:%S")
            diff = abs((cam_dt - local_dt).total_seconds())
            logger.info("Разница времени: %.0f сек", diff)

            if diff > 60:
                logger.warning(
                    "Время камеры расходится с локальным на %.0f сек (более 1 мин)!", diff
                )
        except Exception:
            logger.debug("Не удалось вычислить разницу времени")

    # Пробуем открыть ворота через trafficSnap (для ANPR)
    logger.info("=== Попытка открыть ворота ===")
    #if camera.open_strobe(channel=1, plate_number="A001AA111", open_type="Normal"):
    #    logger.info("Успех!")
