# gotify2apprise

[![Docker](https://img.shields.io/docker/v/mfandreich/gotify2apprise?logo=docker&label=Docker)](https://hub.docker.com/r/mfandreich/gotify2apprise)

[English](readme.md) | Русский

Homelab-мост уведомлений: **listeners** (Gotify, опционально SMTP) → YAML **routes** → **receivers** (Apprise), с историей в SQLite, ретраями и небольшим веб-UI.

Хобби-проект, сделан совместно с [Cursor](https://cursor.com).

```
Gotify WS / SMTP
        │
        ▼
  listeners  ──►  routes (id ∪ tags, фильтры приоритета)
        │
        ▼
  очередь SQLite  ──►  receivers (Apprise)  с backoff
        │
        ▼
     NiceGUI  (конфиг, retry, статистика)
```

UI лучше держать за reverse proxy. Логин в приложении — один локальный пользователь, это не production-grade auth.

## Требования

- Python 3.12+ или Docker
- YAML-конфиг (`version: 2`)
- Для Gotify: **клиентский** токен (не app token)

## Окружение

| Переменная | По умолчанию | Описание |
|---|---|---|
| `CONF_FILE` | `/etc/gotify2apprise/config.yaml` | Путь к YAML v2 |
| `DATA_DIR` | `/var/lib/gotify2apprise` | SQLite и файл секрета сессии |
| `UI_HOST` / `UI_PORT` | `0.0.0.0` / `8080` | Bind веб-UI |
| `STORAGE_SECRET` | пишется в `DATA_DIR/.storage_secret` | Подпись сессии NiceGUI |
| `ADMIN_USER` / `ADMIN_PASSWORD` | `admin` / случайный (один раз в лог) | Создание единственного пользователя UI, если БД пустая |
| `AUTO_MIGRATE_V1` | `false` | Если `true`, конвертирует v1 YAML на месте (пишет `.bak.v1`) |
| `GOTIFY_HOST` / `GOTIFY_TOKEN` | — | Опционально; подставляются как `${GOTIFY_HOST}` / `${GOTIFY_TOKEN}` в YAML |
| `TITLE_TEMPLATE` / `MESSAGE_TEMPLATE` | — | Устарело; лучше `defaults` в YAML |
| `MESSAGE_RETENTION_DAYS` | `30` | Удаление старых сообщений |
| `MAX_MESSAGES_PER_CHANNEL` | `500` | Лимит на listener |

`GOTIFY_HOST` — это host[:port] **без** схемы. Для `https`/`wss` на Gotify-listener поставьте `ssl: true`.

## Конфигурация (YAML v2)

См. [config.example.yaml](config.example.yaml). Три списка: `listeners`, `receivers`, `routes`. Теги на сущностях — метки. В маршруте `listeners` / `listener_tags` (и аналоги в `to`) — это **OR**: объединение явных id и любой включённой сущности, у которой пересекается хотя бы один тег.

```yaml
version: 2
listeners:
  - id: gotify-main
    type: gotify
    tags: [alerts]
    options:
      host: "${GOTIFY_HOST}"
      client_token: "${GOTIFY_TOKEN}"
      ssl: false
      app_tokens: [all]    # или конкретные app-токены Gotify
receivers:
  - id: telegram-alerts
    type: apprise
    tags: [alerts]
    options:
      urls:
        - tgram://BOT_TOKEN/CHAT_ID
routes:
  - id: gotify-to-telegram
    from:
      listeners: [gotify-main]
    to:
      receivers: [telegram-alerts]
    filter:
      min_priority: warn   # int или info|warn|crit
    templates:
      title: "[$priorityStr] $title"
      body: "$message"
    delivery:
      max_attempts: 5  # 0 = ретраи без лимита; для exponential тогда обязателен max_delay_sec
      initial_delay_sec: 30
      backoff: exponential   # или fixed
      max_delay_sec: 3600
```

Корзины приоритета: **info** 0–3, **warn** 4–7, **crit** 8–10. Целое в `priorities` означает ровно это значение.

Плейсхолдеры шаблонов: `$title` `$message` `$appid` `$priority` `$priorityStr`.

`defaults.datetime_format` задаёт формат времени в веб-UI (UTC). По умолчанию `%Y-%m-%d %H:%M:%S.%f`. Здесь `%f` — **миллисекунды, три знака** (не микросекунды Python). Если ключ не указан, берётся дефолт.

`max_attempts: 0` — ретраи без лимита. Для exponential тогда **обязателен** `max_delay_sec` (иначе пауза росла бы бесконечно). Для `fixed` кап можно не писать.

`${ENV}` и `${ENV:-default}` подставляются при загрузке.

Форвардинг обратно в Gotify (`gotify://…` URL Apprise) может зациклиться — так не делайте.

### SMTP-listener

Только для внутренней сети (без auth и TLS в этой версии фичи):

```yaml
- id: smtp-local
  type: smtp
  tags: [mail]
  options:
    host: 0.0.0.0
    port: 2525
    default_priority: 5
```

Тема письма → title, тело → message. `X-Priority` 1–5 мапится в стиль Gotify 10…0. Порт публикуйте только в доверенной Docker-сети. В UI конфига можно вставить этот сниппет.

## Миграция с v1

v1 `applications[]` в рантайме **не читается**.

```bash
python -m gotify2apprise.legacy.migrate_v1 --in-place /path/to/config.yaml
# или
python scripts/migrate_config_v1_to_v2.py config.yaml -o config.v2.yaml
```

Либо `AUTO_MIGRATE_V1=true`: бэкап `config.yaml.bak.v1`, запись v2, продолжение старта. Целые значения в старом `priorities` теперь совпадают с этим числом (баг v1 **не** сохраняется).

## Docker Compose

Образ: [`mfandreich/gotify2apprise`](https://hub.docker.com/r/mfandreich/gotify2apprise). Скопируйте [config.example.yaml](config.example.yaml) в `config.yaml`, затем:

```bash
docker compose up -d
# или собрать локально:
docker compose up -d --build
```

UI: `http://localhost:8080`. Пароль админа меняется в Settings.

## Локальный запуск

```bash
pip install -r requirements.txt
export DATA_DIR=./data CONF_FILE=./config.yaml
export ADMIN_USER=admin ADMIN_PASSWORD=changeme
export GOTIFY_HOST=localhost:80 GOTIFY_TOKEN=your_client_token
python -m gotify2apprise.main
```

Тесты: `pip install -r requirements-dev.txt && pytest`.

## Лицензия

MIT — см. [license](license).
