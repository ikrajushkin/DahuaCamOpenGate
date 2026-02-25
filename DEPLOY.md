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

## 2. Настройка SSH Deploy Key (доступ к приватному репозиторию)

Репозиторий приватный. Для доступа сервера к GitHub используется SSH Deploy Key —
ключ с правами **только на чтение** одного репозитория.

### 2.1 Создать SSH-ключ от имени www-data

```bash
sudo mkdir -p /var/lib/www-data/.ssh
sudo ssh-keygen -t ed25519 -C "dahua-gate-deploy" \
    -f /var/lib/www-data/.ssh/id_ed25519 -N ""
sudo chown -R www-data:www-data /var/lib/www-data/.ssh
sudo chmod 700 /var/lib/www-data/.ssh
sudo chmod 600 /var/lib/www-data/.ssh/id_ed25519
```

### 2.2 Создать SSH-конфиг для www-data

```bash
sudo tee /var/lib/www-data/.ssh/config > /dev/null <<EOF
Host github.com
    IdentityFile /var/lib/www-data/.ssh/id_ed25519
    StrictHostKeyChecking no
EOF
sudo chmod 600 /var/lib/www-data/.ssh/config
sudo chown www-data:www-data /var/lib/www-data/.ssh/config
```

### 2.3 Скопировать публичный ключ

```bash
sudo cat /var/lib/www-data/.ssh/id_ed25519.pub
```

Скопировать весь вывод (строка вида `ssh-ed25519 AAAA... dahua-gate-deploy`).

### 2.4 Добавить ключ в GitHub

1. Открыть репозиторий на GitHub
2. Перейти: **Settings → Deploy keys → Add deploy key**
3. Заполнить:
   - **Title**: `prod-server` (или любое понятное название)
   - **Key**: вставить скопированный публичный ключ
   - **Allow write access**: ❌ не ставить
4. Нажать **Add key**

### 2.5 Проверить подключение

```bash
sudo -u www-data ssh -T git@github.com
```

Ожидаемый ответ (exit code 1 — это нормально для GitHub):
```
Hi ikrajushkin/DahuaCamOpenGate! You've successfully authenticated, but GitHub does not provide shell access.
```

Если вместо этого ошибка — проверить, что ключ добавлен в Deploy keys репозитория.

---

## 3. Клонирование репозитория

```bash
sudo mkdir -p /opt/dahua-gate
sudo chown www-data:www-data /opt/dahua-gate

sudo -u www-data git clone git@github.com:ikrajushkin/DahuaCamOpenGate.git /opt/dahua-gate
```

---

## 4. Виртуальное окружение и зависимости

```bash
cd /opt/dahua-gate
sudo -u www-data python3 -m venv env
sudo -u www-data env/bin/pip install --upgrade pip
sudo -u www-data env/bin/pip install -r requirements.txt
sudo -u www-data env/bin/pip install gunicorn
```

---

## 5. Настройка переменных окружения

Файлы `.env.dev` и `.env.prod` **не хранятся в репозитории** — их нужно создать вручную
на основе шаблона `.env.example`.

```bash
cat /opt/dahua-gate/.env.example          # посмотреть шаблон
```

### Для dev-окружения

```bash
sudo -u www-data cp /opt/dahua-gate/.env.example /opt/dahua-gate/.env.dev
sudo nano /opt/dahua-gate/.env.dev
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
sudo -u www-data cp /opt/dahua-gate/.env.example /opt/dahua-gate/.env.prod
sudo nano /opt/dahua-gate/.env.prod
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

## 6. Режим DEV — ручной запуск с отладкой

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

## 7. Режим PROD — запуск через Gunicorn

### 7.1 Ручной запуск (проверка перед настройкой службы)

```bash
cd /opt/dahua-gate
ENV_FILE=.env.prod env/bin/gunicorn --workers 2 --bind 0.0.0.0:5000 main:app
```

Убедиться что сервер отвечает, затем остановить Ctrl+C.

### 7.2 Автозапуск через systemd

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

## 8. Проверка работы prod-службы

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

## 9. Открытие порта в файрволе (если активен ufw)

```bash
sudo ufw allow 5000/tcp
sudo ufw status
```

---

## 10. Настройка скрипта обновления

Сделать `update.sh` исполняемым (однократно, после клонирования):

```bash
sudo chmod +x /opt/dahua-gate/update.sh
```

---

## 11. Обновление приложения из репозитория

Для обновления предусмотрен скрипт `update.sh`, который выполняет все шаги автоматически:

```bash
sudo /opt/dahua-gate/update.sh
```

Скрипт:
- проверяет SSH-доступ к GitHub перед началом работы
- проверяет наличие новых коммитов (без обновления, если версия актуальна)
- показывает список изменений и изменённых файлов
- обновляет зависимости только если изменился `requirements.txt`
- перезапускает службу и проверяет HTTP-ответ
- выводит итоговую версию (хэш и сообщение последнего коммита)

### 11.1 Проверить, что изменилось в репозитории (вручную)

```bash
cd /opt/dahua-gate

# Посмотреть новые коммиты, не скачивая изменения
sudo -u www-data git fetch
sudo -u www-data git log HEAD..origin/main --oneline

# Посмотреть, какие файлы изменятся
sudo -u www-data git diff HEAD origin/main --name-only
```

### 11.2 Получить обновление

```bash
sudo -u www-data git pull
```

### 11.3 Обновить зависимости (если изменился requirements.txt)

Выполнять только если `git diff` или `git log` показал изменения в `requirements.txt`:

```bash
sudo -u www-data env/bin/pip install -r requirements.txt
```

### 11.4 Перезапустить службу

```bash
sudo systemctl restart dahua-gate
```

### 11.5 Проверить успешность обновления

```bash
# Убедиться, что служба запустилась
sudo systemctl status dahua-gate

# Проверить HTTP-ответ
curl http://localhost:5000/health

# Проверить логи на наличие ошибок (последние 30 строк)
sudo journalctl -u dahua-gate -n 30
```

### 11.6 Откат к предыдущей версии (если что-то пошло не так)

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

/var/lib/www-data/.ssh/
├── id_ed25519        # Приватный SSH Deploy Key (только для чтения репозитория)
├── id_ed25519.pub    # Публичный ключ (добавлен в GitHub → Deploy keys)
└── config            # SSH-конфиг: привязка ключа к github.com
```
