# OneDash Telegram Bot

Репозиторий содержит Telegram-бота для управления VPS через OneDash API и существующие статические файлы сайта.

## Структура

- `bot/` — точка входа и инфраструктура бота
- `api_client.py` — асинхронный клиент OneDash API
- `handlers/` — aiogram handlers и FSM-сценарии
- `keyboards/` — inline keyboard builders
- `config.py` — загрузка конфигурации из `.env`
- `deploy/onedash-bot.service` — systemd unit
- `deploy/onedash-bot.logrotate` — пример logrotate
- `.env.example` — пример переменных окружения
- `tests/` — unit-тесты

## Возможности

- whitelist по `ADMIN_USER_ID`
- главное меню: баланс, серверы, создание VPS, пополнение баланса, тарифы
- просмотр списка VPS и карточки сервера
- перезагрузка VPS с подтверждением
- переустановка ОС с подтверждением
- смена тарифа заказа с подтверждением
- клонирование VPS в существующие целевые VPS с подтверждением
- создание VPS через FSM-сценарий
- debounce-защита от повторных нажатий
- логирование в консоль и файл с ротацией

## Важно по OneDash API

Документация 2.0 использует актуальные эндпоинты `https://api.rdp-onedash.ru/api/*`.
Для чувствительных операций OneDash требует:

- IP whitelist для API-ключа
- `confirm=true` в запросах создания, клонирования, смены тарифа и переустановки

## Быстрый старт локально

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m bot
```

## Переменные окружения

Смотрите `.env.example`:

- `TELEGRAM_BOT_TOKEN`
- `ONEDASH_API_KEY`
- `ADMIN_USER_ID`
- `ONEDASH_API_BASE_URL`
- `ONEDASH_REQUEST_TIMEOUT`
- `BOT_LOG_FILE`
- `BOT_LOG_LEVEL`
- `BOT_CACHE_TTL_SECONDS`
- `BOT_DEBOUNCE_TTL_SECONDS`

## Тесты

```bash
python -m unittest discover -s tests -v
```

Краткий отчёт: `TEST_REPORT.md`.

## Деплой через systemd

1. Скопируйте проект на сервер в `/opt/onedash-bot`.
2. Создайте виртуальное окружение и установите зависимости:
   ```bash
   cd /opt/onedash-bot
   python3 -m venv .venv
   . .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Создайте `/opt/onedash-bot/.env` по примеру `.env.example`.
4. Создайте каталог логов:
   ```bash
   mkdir -p /var/log/onedash-bot
   ```
5. Установите unit-файл:
   ```bash
   cp deploy/onedash-bot.service /etc/systemd/system/onedash-bot.service
   systemctl daemon-reload
   systemctl enable --now onedash-bot.service
   ```
6. При необходимости установите logrotate:
   ```bash
   cp deploy/onedash-bot.logrotate /etc/logrotate.d/onedash-bot
   ```
7. Проверка:
   ```bash
   systemctl status onedash-bot.service
   journalctl -u onedash-bot.service -f
   ```

## Примечания

- Бот использует long polling.
- Платёжные ссылки и VPS-пароли не логируются.
- Для Windows-систем в мастере создания есть опция отключения ярлыка OneDash на рабочем столе.
- По актуальной документации клонирование работает в существующие целевые VPS, а не создаёт новый сервер из параметров.
