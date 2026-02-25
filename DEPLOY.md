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

## 4. Настройка переменных окружения

Файлы `.env.dev` и `.env.prod` **не хранятся в репозитории** — их нужно создать вручную
на основе шаблона `.env.example`.

```bash
cat .env.example          # посмотреть шаблон
```

### Для dev-окружения

```bash
cp .env.example .env.dev
nano .env.dev
```

Содержимое `.env.dev`:

```env
CAMERA_IP=192.168.84.2
CAMERA_USERNAME=admin
CAMERA_PASSWORD=ваш_пароль

SERVER_HOST=127.0.0.1
SERVER_PORT=5000
```

### Для prod-окружения

```bash
cp .env.example .env.prod
nano .env.prod
```

Содержимое `.env.prod`:

```env
CAMERA_IP=192.168.84.2
CAMERA_USERNAME=admin
CAMERA_PASSWORD=ваш_пароль

SERVER_HOST=0.0.0.0
SERVER_PORT=5000
```

> **SERVER_HOST**: `127.0.0.1` — только локальный доступ (dev), `0.0.0.0` — доступ из сети (prod).

---

## 5. Режим DEV — ручной запуск с отладкой

Используется при разработке и отладке. Flask dev-сервер, автоперезагрузка при изменении кода.

```bash
cd /opt/dahua-gate
source env/bin/activate

ENV_FILE=.env.dev python main.py
```

Проверка:

```bash
curl http://127.0.0.1:5000/health
curl http://127.0.0.1:5000/api/time
curl -X POST http://127.0.0.1:5000/api/gate/open \
     -H "Content-Type: application/json" \
     -d '{"plate_number": "A001AA111"}'
```

---

## 6. Режим PROD — запуск через Gunicorn

### 6.1 Ручной запуск (проверка перед настройкой службы)

```bash
cd /opt/dahua-gate
source env/bin/activate

ENV_FILE=.env.prod gunicorn --workers 2 --bind 0.0.0.0:5000 main:app
```

Убедиться что сервер отвечает, затем остановить Ctrl+C.

### 6.2 Автозапуск через systemd

Назначить права на директорию:

```bash
sudo chown -R www-data:www-data /opt/dahua-gate
```

Создать файл службы:

```bash
sudo nano /etc/systemd/system/dahua-gate.service
```

Содержимое:

```ini
[Unit]
Description=DahuaCamOpenGate HTTP Server
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/dahua-gate
Environment="ENV_FILE=.env.prod"
ExecStart=/opt/dahua-gate/env/bin/gunicorn --workers 2 --bind 0.0.0.0:5000 main:app
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Включить и запустить:

```bash
sudo systemctl daemon-reload
sudo systemctl enable dahua-gate
sudo systemctl start dahua-gate
```

---

## 7. Проверка работы prod-службы

```bash
# Статус
sudo systemctl status dahua-gate

# Логи gunicorn (stdout/stderr)
sudo journalctl -u dahua-gate -f

# Логи приложения (camera.log)
tail -f /opt/dahua-gate/camera.log

# HTTP-проверка
curl http://localhost:5000/health
```

---

## 8. Открытие порта в файрволе (если активен ufw)

```bash
sudo ufw allow 5000/tcp
sudo ufw status
```

---

## 9. Обновление приложения из репозитория

Для обновления предусмотрен скрипт `update.sh`, который выполняет все шаги автоматически:

```bash
sudo /opt/dahua-gate/update.sh
```

Скрипт:
- проверяет наличие новых коммитов (без обновления, если версия актуальна)
- показывает список изменений и изменённых файлов
- обновляет зависимости только если изменился `requirements.txt`
- перезапускает службу и проверяет HTTP-ответ
- выводит итоговую версию (хэш и сообщение последнего коммита)

Подготовить скрипт к запуску (однократно, после клонирования):

```bash
chmod +x /opt/dahua-gate/update.sh
```

---

### 9.1 Проверить, что изменилось в репозитории (вручную)

```bash
cd /opt/dahua-gate

# Посмотреть новые коммиты, не скачивая изменения
sudo -u www-data git fetch
sudo -u www-data git log HEAD..origin/main --oneline

# Посмотреть, какие файлы изменятся
sudo -u www-data git diff HEAD origin/main --name-only
```

### 9.2 Получить обновление

```bash
sudo -u www-data git pull
```

### 9.3 Обновить зависимости (если изменился requirements.txt)

Выполнять только если `git diff` или `git log` показал изменения в `requirements.txt`:

```bash
sudo -u www-data env/bin/pip install -r requirements.txt
```

### 9.4 Перезапустить службу

```bash
sudo systemctl restart dahua-gate
```

### 9.5 Проверить успешность обновления

```bash
# Убедиться, что служба запустилась
sudo systemctl status dahua-gate

# Проверить HTTP-ответ
curl http://localhost:5000/health

# Проверить логи на наличие ошибок (последние 30 строк)
sudo journalctl -u dahua-gate -n 30
```

### 9.6 Откат к предыдущей версии (если что-то пошло не так)

```bash
# Посмотреть историю коммитов
sudo -u www-data git log --oneline -10

# Откатиться к конкретному коммиту (заменить <hash> на нужный)
sudo -u www-data git checkout <hash>

# Перезапустить службу
sudo systemctl restart dahua-gate
sudo systemctl status dahua-gate
```

Вернуться на актуальную версию после отката:

```bash
sudo -u www-data git checkout main
sudo -u www-data git pull
sudo systemctl restart dahua-gate
```

---

## Сравнение режимов запуска

| Параметр            | DEV                            | PROD                              |
|---------------------|--------------------------------|-----------------------------------|
| Команда запуска     | `ENV_FILE=.env.dev python main.py` | `gunicorn ... main:app`       |
| Сервер              | Flask dev-сервер (Werkzeug)    | Gunicorn                          |
| Файл окружения      | `.env.dev`                     | `.env.prod`                       |
| SERVER_HOST         | `127.0.0.1` (только localhost) | `0.0.0.0` (все интерфейсы)        |
| Воркеры             | 1                              | 2+                                |
| Автоперезагрузка    | Да (при изменении кода)        | Нет                               |
| Автозапуск systemd  | Нет                            | Да                                |
| Отладчик Werkzeug   | Включён                        | Выключен                          |

---

## Управление prod-службой — шпаргалка

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
├── .env.example      # Шаблон переменных окружения (в репозитории)
├── .env.dev          # Dev-конфигурация с учётными данными (НЕ в репозитории)
├── .env.prod         # Prod-конфигурация с учётными данными (НЕ в репозитории)
├── swagger.yaml      # Описание API (OpenAPI 3.0)
├── update.sh         # Скрипт обновления из GitHub и перезапуска службы
├── camera.log        # Лог-файл приложения (создаётся при запуске)
└── DEPLOY.md         # Данная инструкция
```
