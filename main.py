import logging
import os
import requests
from requests.auth import HTTPDigestAuth
from datetime import datetime
from flask import Flask, jsonify, request
from dotenv import load_dotenv

load_dotenv(os.getenv("ENV_FILE", ".env"))

# ---------------------------------------------------------------------------
# Настройка логгера
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Класс управления камерой Dahua
# ---------------------------------------------------------------------------
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
        Получить текущее время камеры.

        Returns:
            dict:
                - success (bool)
                - camera_time (str): "yyyy-mm-dd hh:mm:ss"
                - raw_response (str)
                - local_time (str)
                - is_valid_format (bool)
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
        """
        Открыть ворота через Traffic Snap API.

        Args:
            channel (int): Канал камеры.
            plate_number (str): Номер автомобиля.
            open_type (str): "Normal", "Emergency" и т.д.

        Returns:
            bool: True — ворота открыты, False — ошибка.
        """
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


# ---------------------------------------------------------------------------
# Конфигурация (из переменных окружения)
# ---------------------------------------------------------------------------
CAMERA_IP   = os.environ["CAMERA_IP"]
USERNAME    = os.environ["CAMERA_USERNAME"]
PASSWORD    = os.environ["CAMERA_PASSWORD"]
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "5000"))

# ---------------------------------------------------------------------------
# Flask-приложение
# ---------------------------------------------------------------------------
app    = Flask(__name__)
camera = DahuaCamera(CAMERA_IP, USERNAME, PASSWORD)


@app.route("/health", methods=["GET"])
def health():
    """Проверка работоспособности сервера."""
    logger.debug("GET /health")
    return jsonify({"status": "ok"}), 200


@app.route("/api/time", methods=["GET"])
def api_get_time():
    """
    Получить текущее время камеры.

    Response 200:
        {
            "success": true,
            "camera_time": "2026-02-24 12:00:00",
            "local_time":  "2026-02-24 12:00:05",
            "is_valid_format": true,
            "raw_response": "2026-02-24 12:00:00"
        }

    Response 502 (ошибка со стороны камеры):
        {"success": false, "error": "timeout"}
    """
    logger.info("GET /api/time — запрос времени камеры")
    result = camera.get_current_time()

    if result.get("success"):
        return jsonify(result), 200
    else:
        return jsonify(result), 502


@app.route("/api/gate/open", methods=["POST"])
def api_open_gate():
    """
    Открыть ворота.

    Request body (JSON, все поля опциональны):
        {
            "channel":      1,
            "plate_number": "A001AA111",
            "open_type":    "Normal"
        }

    Response 200:
        {"success": true, "message": "Gate opened"}

    Response 502 (ошибка со стороны камеры):
        {"success": false, "message": "Failed to open gate"}
    """
    body = request.get_json(silent=True) or {}

    channel      = body.get("channel",      1)
    plate_number = body.get("plate_number", "")
    open_type    = body.get("open_type",    "Normal")

    logger.info(
        "POST /api/gate/open — channel=%s, plate='%s', type=%s",
        channel, plate_number, open_type
    )

    success = camera.open_strobe(
        channel=channel,
        plate_number=plate_number,
        open_type=open_type
    )

    if success:
        return jsonify({"success": True,  "message": "Gate opened"}),          200
    else:
        return jsonify({"success": False, "message": "Failed to open gate"}),  502


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info("=== Запуск HTTP-сервера на %s:%s ===", SERVER_HOST, SERVER_PORT)
    app.run(host=SERVER_HOST, port=SERVER_PORT)
