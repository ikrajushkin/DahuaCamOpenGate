import requests
from requests.auth import HTTPDigestAuth

class DahuaCamera:
    def __init__(self, ip, username, password):
        self.ip = ip
        self.username = username
        self.password = password
        self.base_url = f"http://{ip}/cgi-bin"
        self.session = requests.Session()
    
    def check_access_control_support(self):
        """Проверить поддержку Access Control"""
        url = f"{self.base_url}/magicBox.cgi?action=getProductDefinition"
        
        try:
            response = self.session.get(
                url,
                auth=HTTPDigestAuth(self.username, self.password),
                timeout=5
            )
            
            if response.status_code == 200:
                print("Информация о продукте:")
                print(response.text)
                
                # Проверяем наличие ключевых слов
                if "access" in response.text.lower() or "door" in response.text.lower():
                    print("✓ Access Control может быть поддерживаем")
                else:
                    print("✗ Access Control не поддерживается")
                return True
            else:
                print(f"Ошибка получения информации: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Ошибка: {e}")
            return False
    
    def get_capability(self):
        """Получить capabilities устройства"""
        url = f"{self.base_url}/magicBox.cgi?action=getCapability"
        
        try:
            response = self.session.get(
                url,
                auth=HTTPDigestAuth(self.username, self.password),
                timeout=5
            )
            
            if response.status_code == 200:
                print("Capabilities:")
                print(response.text)
                return response.text
            return None
            
        except Exception as e:
            print(f"Ошибка: {e}")
            return None
    
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

    def trigger_alarm_output(self, output_id=0, duration=3):
        """
        Активировать выход реле (аларм)
        
        Args:
            output_id: ID выхода (обычно 0)
            duration: длительность в секундах
        """
        url = f"{self.base_url}/alarm.cgi?action=startAlarm"
        params = {
            "channel": output_id,
            "duration": duration
        }
        
        try:
            response = self.session.get(
                url,
                params=params,
                auth=HTTPDigestAuth(self.username, self.password),
                timeout=5
            )
            
            if response.status_code == 200 and response.text.strip() == "OK":
                print(f"✓ Реле {output_id} активировано на {duration} сек")
                return True
            else:
                print(f"✗ Ошибка активации реле: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            return False


    def stop_alarm_output(self, output_id=0):
        """Остановить выход реле"""
        url = f"{self.base_url}/alarm.cgi?action=stopAlarm"
        params = {"channel": output_id}
        
        response = self.session.get(
            url,
            params=params,
            auth=HTTPDigestAuth(self.username, self.password)
        )
        
        return response.status_code == 200 and response.text.strip() == "OK"
    
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
        
        try:
            response = self.session.get(
                url,
                params=params,
                auth=HTTPDigestAuth(self.username, self.password),
                timeout=5
            )
            
            if response.status_code == 200 and response.text.strip() == "OK":
                print(f"✓ Ворота открыты для номера {plate_number}")
                return True
            else:
                print(f"✗ Ошибка: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            return False

# Пример использования
if __name__ == "__main__":
    # Настройки камеры
    CAMERA_IP = "192.168.84.2"
    USERNAME = "admin"
    PASSWORD = "Donsmart2019"
    
    camera = DahuaCamera(CAMERA_IP, USERNAME, PASSWORD)
    
    # 1. Проверяем поддержку
    #print("=== Проверка поддержки ===")
    #camera.check_access_control_support()
    
    # 2. Получаем capabilities
    #print("\n=== Capabilities ===")
    #camera.get_capability()
    
    # 3. Пробуем открыть ворота через trafficSnap (для ANPR)
    print("\n=== Попытка открыть ворота ===")
    if camera.open_strobe(channel=1, plate_number="A055AA77", open_type="Normal"):
        print("Успех!")
    '''else:
        # 4. Альтернатива: активируем реле
        print("\n=== Активация реле ===")
        if camera.trigger_alarm_output(output_id=0, duration=3):
            print("Реле активировано!")
            pause(3000)
            camera.stop_alarm_output(output_id=0)'''