import requests
from requests.auth import HTTPDigestAuth
import json
from datetime import datetime

class DahuaCamera:
    def __init__(self, ip, username, password):
        self.ip = ip
        self.username = username
        self.password = password
        self.base_url = f"http://{ip}/cgi-bin"
        self.session = requests.Session()
  
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
        
        try:
            response = self.session.get(
                url,
                auth=HTTPDigestAuth(self.username, self.password),
                timeout=5
            )
            
            if response.status_code == 200:
                # Dahua обычно возвращает время в формате: "2024-02-05 14:30:45"
                camera_time = response.text.strip()
                
                # Валидация формата времени
                try:
                    parsed_time = datetime.strptime(camera_time, "%Y-%m-%d %H:%M:%S")
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
                    print(f"✓ Текущее время камеры: {camera_time}")
                else:
                    print(f"⚠ Получено время в нестандартном формате: {camera_time}")
                
                return result
            else:
                print(f"✗ Ошибка получения времени: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error_code": response.status_code,
                    "error_message": response.text.strip()
                }
                
        except requests.exceptions.Timeout:
            print("✗ Таймаут подключения к камере")
            return {"success": False, "error": "timeout"}
        except requests.exceptions.ConnectionError:
            print("✗ Ошибка подключения к камере")
            return {"success": False, "error": "connection_error"}
        except Exception as e:
            print(f"✗ Неизвестная ошибка: {e}")
            return {"success": False, "error": str(e)}
        
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

    def close_strobe(self, location=0):
        """
        Закрыть стробоскоп/ворота (шлагбаум)
        
        Args:
            location (int): Номер полосы (lane number), по умолчанию 0
            
        Returns:
            bool: True при успешном выполнении
        """
        url = f"{self.base_url}/cgi-bin/api/trafficSnap/closeStrobe"
        
        # Формируем JSON-тело запроса согласно документации
        payload = {
            "info": {
                "location": location  # Опциональный параметр, по умолчанию 0
            }
        }
        
        headers = {
            "Content-Type": "application/json; charset=utf-8"
        }
        
        try:
            response = self.session.post(
                url,
                data=json.dumps(payload),
                headers=headers,
                auth=HTTPDigestAuth(self.username, self.password),
                timeout=5
            )
            
            # Проверяем успешность операции
            if response.status_code == 200:
                # Dahua обычно возвращает "OK" в теле ответа
                if response.text.strip() == "OK" or response.json().get("Result", False):
                    print(f"✓ Стробоскоп/ворота успешно закрыты (полоса {location})")
                    return True
                else:
                    print(f"⚠ Команда выполнена, но ответ не подтверждён: {response.text}")
                    return False
            else:
                print(f"✗ Ошибка закрытия стробоскопа: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            print("✗ Таймаут подключения к камере")
            return False
        except requests.exceptions.ConnectionError:
            print("✗ Ошибка подключения к камере")
            return False
        except json.JSONDecodeError:
            # Некоторые камеры возвращают простой текст "OK" вместо JSON
            if response.text.strip() == "OK":
                print(f"✓ Стробоскоп/ворота успешно закрыты (полоса {location})")
                return True
            print(f"⚠ Неожиданный формат ответа: {response.text}")
            return False
        except Exception as e:
            print(f"✗ Неизвестная ошибка: {e}")
            return False
        
# Пример использования
if __name__ == "__main__":
    # Настройки камеры
    CAMERA_IP = "192.168.84.2"
    USERNAME = "admin"
    PASSWORD = "Donsmart2019"
    
    camera = DahuaCamera(CAMERA_IP, USERNAME, PASSWORD)

    # Получение текущего времени камеры
    print("=== Получение времени камеры ===")
    result = camera.get_current_time()
    
    if result["success"]:
        print(f"Время камеры: {result['camera_time']}")
        print(f"Локальное время: {result['local_time']}")
        
        # Расчет разницы во времени (опционально)
        try:
            cam_dt = datetime.strptime(result['camera_time'], "%Y-%m-%d %H:%M:%S")
            local_dt = datetime.strptime(result['local_time'], "%Y-%m-%d %H:%M:%S")
            diff = abs((cam_dt - local_dt).total_seconds())
            print(f"Разница: {diff:.0f} секунд")
            
            if diff > 60:
                print("⚠ Время камеры расходится с локальным более чем на 1 минуту!")
        except:
            pass
    
    '''
    # 1. Пробуем открыть ворота через trafficSnap (для ANPR)
    
    print("\n=== Попытка открыть ворота ===")
    if camera.open_strobe(channel=1, plate_number="A055AA77", open_type="Normal"):
        print("Успех!")
    
    pause(17000)
    # 2. Пробуем закрыть ворота через trafficSnap (для ANPR)
    print("\n=== Попытка закрыть ворота ===")
    if camera.close_strobe(location=0):
        print("Успех!")
    '''


    # 3. Альтернатива: активируем реле
    print("\n=== Активация реле тревоги ===")
    if camera.trigger_alarm_output(output_id=0, duration=3):
        print("Реле активировано!")
        pause(12000)
        camera.stop_alarm_output(output_id=0)
        print("Реле деактивировано!")
