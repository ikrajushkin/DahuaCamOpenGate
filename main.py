import requests
from requests.auth import HTTPDigestAuth

class DahuaCamera:
    def __init__(self, ip, username, password):
        self.ip = ip
        self.username = username
        self.password = password
        self.base_url = f"http://{ip}/cgi-bin"
    
    def open_door(self, channel=1, user_id=None, open_type="Remote"):
        """
        Открыть дверь/ворота
        
        Args:
            channel: номер канала двери (начинается с 1)
            user_id: ID пользователя (опционально)
            open_type: тип открытия ("Remote" по умолчанию)
        
        Returns:
            bool: True если успешно
        """
        url = f"{self.base_url}/accessControl.cgi"
        params = {
            "action": "openDoor",
            "channel": channel,
            "Type": open_type
        }
        
        if user_id is not None:
            params["UserID"] = user_id
        
        try:
            response = requests.get(
                url,
                params=params,
                auth=HTTPDigestAuth(self.username, self.password),
                timeout=5
            )
            
            if response.status_code == 200 and response.text.strip() == "OK":
                print(f"✓ Ворота {channel} успешно открыты!")
                return True
            else:
                print(f"✗ Ошибка открытия ворот: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Ошибка подключения: {e}")
            return False
    
    def close_door(self, channel=1, user_id=None, close_type="Remote"):
        """Закрыть дверь/ворота"""
        url = f"{self.base_url}/accessControl.cgi"
        params = {
            "action": "closeDoor",
            "channel": channel,
            "Type": close_type
        }
        
        if user_id is not None:
            params["UserID"] = user_id
        
        response = requests.get(
            url,
            params=params,
            auth=HTTPDigestAuth(self.username, self.password)
        )
        
        return response.status_code == 200 and response.text.strip() == "OK"
    
    def get_door_status(self, channel=1):
        """Получить статус двери"""
        url = f"{self.base_url}/accessControl.cgi"
        params = {
            "action": "getDoorStatus",
            "channel": channel
        }
        
        response = requests.get(
            url,
            params=params,
            auth=HTTPDigestAuth(self.username, self.password)
        )
        
        # Возвращает данные в формате key=value
        return response.text


# Пример использования
if __name__ == "__main__":
    # Настройки камеры
    CAMERA_IP = "192.168.84.2"
    USERNAME = "admin"
    PASSWORD = "admin123"
    
    # Создание объекта камеры
    camera = DahuaCamera(CAMERA_IP, USERNAME, PASSWORD)
    
    # Открытие ворот на канале 1
    camera.open_door(channel=1)
    
    # Проверка статуса
    status = camera.get_door_status(channel=1)
    print(f"Статус ворот: {status}")