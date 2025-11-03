# вайб-кодинг.рус — фронтенд (GitHub Pages) + FastAPI backend

Этот репозиторий содержит:
- Статический сайт для домена «вайб-кодинг.рус» (index.html, styles.css, main.js, privacy.html, robots.txt, sitemap.xml, CNAME)
- Небольшой FastAPI‑бекенд для проксирования запросов к AgentRouter (api.py)

Фронтенд развёртывается на GitHub Pages с кастомным доменом, бэкенд — на любом PaaS (Render/Railway/Fly.io/веб‑сервер).

---

## 1) Хостинг фронтенда (GitHub Pages + CNAME)

1. В ветке gh-pages (или main → Settings → Pages) включите GitHub Pages для корня репо.
2. Файл CNAME уже присутствует и содержит домен: «вайб-кодинг.рус».
3. Настройте DNS у регистратора:
   - Вариант A (рекомендация GitHub): CNAME-запись для «@» → username.github.io (для корневого домена — используйте A/AAAA записи из документации GitHub Pages).
   - Либо A‑записи на IP GitHub Pages: 185.199.108.153/109/110/111 (проверьте актуальные IP в доках GitHub).
4. Дождитесь обновления DNS, затем проверьте загрузку сайта по https://вайб-кодинг.рус/
5. Канонический адрес и OG‑метаданные уже указывают на кастомный домен.

Примечание по заголовкам безопасности на статическом хостинге:
- На GitHub Pages нельзя выставить серверные заголовки (CSP, Permissions-Policy, и т.д.). В index.html добавлены эквиваленты через meta http-equiv, но браузеры могут применять их ограниченно.
- Если нужна строгая CSP/Permissions-Policy, используйте прокси/CDN с поддержкой серверных заголовков (например, Cloudflare с Transform Rules или Netlify/Vercel c файлом конфигурации).

---

## 2) Бэкенд (FastAPI) — деплой и конфигурация

Исходники: api.py, requirements.txt

Быстрый запуск локально:
- Python 3.10+
- pip install -r requirements.txt
- uvicorn api:app --host 0.0.0.0 --port 8000
- Проверка: GET http://localhost:8000/health → {"status":"ok"}

Обязательные переменные окружения:
- AGENTROUTER_API_KEY — API ключ для https://api.agentrouter.org
- AGENTROUTER_MODEL — модель (по умолчанию gpt-5)
- CORS_ORIGINS — список разрешённых Origin через запятую
- RATE_LIMIT_WINDOW_SEC — окно лимитирования (сек), по умолчанию 60
- RATE_LIMIT_MAX_REQUESTS — запросов в окне, по умолчанию 10
- MAX_MESSAGE_LEN — макс. длина входного сообщения, по умолчанию 1000

Эндпоинты:
- GET /health — проверка работоспособности
- POST /api/chat — { "message": "..." } → { "reply": "..." }

Защита и заголовки:
- Rate limit по IP (простые ведра в памяти)
- Валидация сообщения (длина, базовый анти‑спам)
- Серверные заголовки: Referrer-Policy, Permissions-Policy, X-Content-Type-Options, X-Frame-Options

### Рекомендованный деплой: Render

1) Создайте Web Service из этого репозитория.
2) Build Command: pip install -r requirements.txt
3) Start Command: uvicorn api:app --host 0.0.0.0 --port $PORT
4) Переменные окружения:
   - AGENTROUTER_API_KEY=... (обяз.)
   - AGENTROUTER_MODEL=gpt-5
   - CORS_ORIGINS=https://vibecoding.github.io,https://<ваш_домен_в_punycode>
   - RATE_LIMIT_WINDOW_SEC=60
   - RATE_LIMIT_MAX_REQUESTS=10
   - MAX_MESSAGE_LEN=1000
5) Получите продакшен URL, например: https://vibe-api.onrender.com

### Railway / Fly.io / VPS

- Railway: аналогично Render (Start: uvicorn api:app --host 0.0.0.0 --port $PORT).
- Fly.io: fly launch → переменные окружения → fly deploy (можно добавить Dockerfile при необходимости).
- VPS (Ubuntu): python3 -m venv venv; source venv/bin/activate; pip install -r requirements.txt; gunicorn -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:8000 api:app; повесьте Nginx как обратный прокси с TLS.

---

## 3) CORS для «вайб-кодинг.рус» (IDN/Пуникод)

Браузеры отправляют Origin для IDN‑доменов в punycode. Чтобы CORS работал корректно, в CORS_ORIGINS нужно указать домен в punycode.

Как получить punycode для «вайб-кодинг.рус»:
- Любой онлайн‑конвертер IDNA/punycode (например, https://www.punycoder.com/)
- Или в Python:
  - print("ваш-домен.рус".encode("idna").decode("ascii"))

В итоге задайте переменную:
- CORS_ORIGINS=https://vibecoding.github.io,https://<punycode-домен>

По умолчанию (без CORS_ORIGINS) включены базовые источники:
- https://vibecoding.github.io, http://localhost:8000, http://127.0.0.1:8000
Рекомендуется задать CORS_ORIGINS явно для продакшена.

---

## 4) Привязка фронтенда к бэкенду

Текущая версия сайта не содержит чат‑виджета (удалён по требованиям безопасности/UX). Поэтому прямой вызов /api/chat с фронтенда не используется.

Если вы планируете вернуть чат:
- Добавьте UI поля ввода и кнопку «Отправить»
- В main.js реализуйте sendMessage(), отправляющий POST на ваш прод‑URL бэкенда (/api/chat)
- Добавьте ваш прод URL в список разрешённых источников CORS_ORIGINS на бэкенде
- Не размещайте публичные API‑ключи в фронтенде

---

## 5) Lighthouse и доступность (аудит)

Проверьте сайт после деплоя:
- Chrome DevTools → Lighthouse: Performance, Accessibility, Best Practices, SEO
- Проверьте:
  - Читаемость на мобильных (контраст/размеры шрифтов, кликабельные области)
  - Ссылки/кнопки имеют фокус‑стили (реализовано в styles.css)
  - Якорные переходы не перекрываются хедером (scroll-margin-top настроен)
  - iframes и изображения с loading="lazy", корректные alt‑теги
  - JSON‑LD FAQ (в head) парсится валидаторами

---

## 6) Приватность и аналитика

- Аналитика Яндекс.Метрики загружается только после согласия пользователя (баннер в main.js).
- Политика конфиденциальности: privacy.html
- Отключение/изменение трекинга — редактируйте main.js (setupAnalyticsConsent, track).

---

## 7) Безопасность статического хоста (важно)

- CSP/Permissions-Policy, заданные через <meta http-equiv>, могут применяться не полностью, зависят от браузера.
- На GitHub Pages нельзя выставлять server-side заголовки. Для строгой политики используйте:
  - Cloudflare (Transform/Response Headers) перед GitHub Pages
  - Netlify / Vercel с конфигурацией заголовков (например, _headers)
- На бэкенде (FastAPI) заголовки уже выставляются в middleware security_headers().

---

## 8) Тесты и диагностика

- Бэкенд: curl https://<ваш-backend>/health
- CORS preflight:
  - curl -i -X OPTIONS https://<ваш-backend>/api/chat -H "Origin: https://<ваш-frontend>" -H "Access-Control-Request-Method: POST"
- Логи бэкенда (Render/Railway): используйте встроенную консоль провайдера.

---

## 9) Обновления контента/SEO

- Развёрнутая статья «Что такое вайбкодинг» размещена выше фолда.
- Дополнены блог‑разделы: 5 шагов, сравнение инструментов, кейсы по Telegram‑боту.
- Добавлен блок «Полезные материалы» (книги/курсы/каналы).
- Canonical/OG/Twitter теги указывают на кастомный домен, robots.txt и sitemap.xml обновлены.

Если потребуется, вынесите критический CSS в <head> и минифицируйте assets. Текущие размеры небольшие, поэтому дополнительная оптимизация опциональна.
