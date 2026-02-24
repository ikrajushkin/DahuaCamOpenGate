# Развёртывание DahuaCamOpenGate на Ubuntu 22.04

## Требования

- Ubuntu 22.04 LTS
- Python 3.10+
- Доступ к камере Dahua по сети (порт 80)
- Порт 5000 открыт на сервере (или другой выбранный порт)

---

## 1. Подготовка системы

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git
```

---

## 2. Клонирование репозитория

```bash
sudo mkdir -p /opt/dahua-gate
sudo chown $USER:$USER /opt/dahua-gate

git clone https://github.com/ikrajushkin/DahuaCamOpenGate.git /opt/dahua-gate
cd /opt/dahua-gate
```

---

## 3. Виртуальное окружение и зависимости

```bash
python3 -m venv env
source env/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

---

## 4. Настройка конфигурации

Открыть файл `main.py` и скорректировать параметры подключения к камере:

```bash
nano main.py
```

Найти и изменить блок конфигурации:

```python
CAMERA_IP   = "192.168.84.2"   # IP-адрес камеры Dahua
USERNAME    = "admin"           # Логин камеры
PASSWORD    = "Donsmart2019"    # Пароль камеры
SERVER_HOST = "0.0.0.0"         # Слушать на всех интерфейсах
SERVER_PORT = 5000              # Порт HTTP-сервера
```

---

## 5. Проверка работы вручную

```bash
cd /opt/dahua-gate
source env/bin/activate

gunicorn --workers 2 --bind 0.0.0.0:5000 main:app
```

Проверить в другом терминале:

```bash
curl http://localhost:5000/health
# Ожидаемый ответ: {"status": "ok"}

curl http://localhost:5000/api/time
# Ожидаемый ответ: {"success": true, "camera_time": "..."}

curl -X POST http://localhost:5000/api/gate/open \
     -H "Content-Type: application/json" \
     -d '{"plate_number": "A001AA111"}'
# Ожидаемый ответ: {"success": true, "message": "Gate opened"}
```

Остановить Ctrl+C и перейти к настройке автозапуска.

---

## 6. Настройка автозапуска через systemd

Создать файл службы:

```bash
sudo nano /etc/systemd/system/dahua-gate.service
```

Содержимое файла:

```ini
[Unit]
Description=DahuaCamOpenGate HTTP Server
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/dahua-gate
ExecStart=/opt/dahua-gate/env/bin/gunicorn --workers 2 --bind 0.0.0.0:5000 main:app
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Назначить права на директорию пользователю `www-data`:

```bash
sudo chown -R www-data:www-data /opt/dahua-gate
```

Включить и запустить службу:

```bash
sudo systemctl daemon-reload
sudo systemctl enable dahua-gate
sudo systemctl start dahua-gate
```

---

## 7. Проверка статуса службы

```bash
# Статус
sudo systemctl status dahua-gate

# Логи службы (gunicorn)
sudo journalctl -u dahua-gate -f

# Логи приложения (camera.log)
tail -f /opt/dahua-gate/camera.log
```

---

## 8. Открытие порта в файрволе (если активен ufw)

```bash
sudo ufw allow 5000/tcp
sudo ufw status
```

---

## 9. Обновление приложения из репозитория

```bash
cd /opt/dahua-gate
sudo -u www-data git pull

sudo systemctl restart dahua-gate
sudo systemctl status dahua-gate
```

---

## Управление службой — шпаргалка

| Команда | Действие |
|---|---|
| `sudo systemctl start dahua-gate` | Запустить |
| `sudo systemctl stop dahua-gate` | Остановить |
| `sudo systemctl restart dahua-gate` | Перезапустить |
| `sudo systemctl status dahua-gate` | Статус |
| `sudo journalctl -u dahua-gate -f` | Логи в реальном времени |

---

## Структура файлов после развёртывания

```
/opt/dahua-gate/
├── env/              # Виртуальное окружение Python
├── main.py           # Основной файл приложения
├── requirements.txt  # Зависимости Python
├── swagger.yaml      # Описание API (OpenAPI 3.0)
├── camera.log        # Лог-файл приложения (создаётся при запуске)
└── DEPLOY.md         # Данная инструкция
```
