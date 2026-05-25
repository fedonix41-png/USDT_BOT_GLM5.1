# Риски и рекомендации

## Риски

### 1. AES-256-CBC и ключ шифрования
При потере `ENCRYPTION_KEY` зашифрованные реквизиты невозможно восстановить.

**Меры:**
- Резервное копирование `.env` в безопасное место
- Документирование процедуры восстановления
- Вывод предупреждения при отсутствии ключа

### 2. Telegram API rate limits
При массовой рассылке обновлений ссылок возможен ответ 429 (Too Many Requests).

**Меры:**
- ARQ retry с exponential backoff (max_tries=3)
- Задержка между отправками сообщений (встроена в ARQ)
- Логирование ошибок для анализа

### 3. Отсутствие курса при первом запуске
Если админ не задал курс, клиент увидит «Курс не установлен».

**Меры:**
- Корректная обработка `None` в RateService
- Понятное сообщение для пользователя
- Напоминание в чатах уведомлений о необходимости настройки

### 4. Long Polling vs Webhook
При перезапуске бота есть окно ~30 секунд, когда обновления могут быть пропущены.

**Меры:**
- Для MVP это допустимо
- В будущем возможен переход на Webhook (с FastAPI)

---

## Рекомендации

### 1. Redis-кеш для флагов
Значения `bot_enabled`, `buy_enabled`, `sell_enabled` кешировать в Redis с TTL 30 секунд.

**Причина:** Снижение нагрузки на PostgreSQL при каждом сообщении.

### 2. Структурированное логирование
Использовать JSON-формат логов для Docker.

```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        })
```

### 3. Graceful shutdown
Обработка SIGTERM для корректного завершения:

```python
import signal

async def shutdown():
    await dp.stop_polling()
    await bot.session.close()
    await async_engine.dispose()

signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(shutdown()))
```

### 4. Healthcheck для bot-контейнера (опционально)
Добавить простой HTTP-эндпоинт на порту 8080 только для healthcheck.

```python
# app/health.py
from aiohttp import web

async def health(request):
    return web.Response(text="OK")

app = web.Application()
app.router.add_get("/health", health)
web.run_app(app, port=8080)
```

В `docker-compose.yml`:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### 5. Мониторинг (на будущее)
- Prometheus метрики: количество заявок, время ответа, ошибки API
- Grafana дашборд для визуализации
- Алерты при падении сервисов

---

## Порядок запуска

```bash
# 1. Скопировать и заполнить .env
cp .env.example .env
# Отредактировать: BOT_TOKEN, ENCRYPTION_KEY, SUPER_ADMIN_TELEGRAM_ID

# 2. Запустить инфраструктуру
docker-compose up -d postgres redis

# 3. Выполнить миграции
uv run alembic upgrade head

# 4. Запустить все сервисы
docker-compose up -d

# 5. Настроить от имени SuperAdmin:
#    - Курс покупки
#    - Курс продажи
#    - Реквизиты (ссылки)
#    - Добавить чат уведомлений
#    - Назначить операторов

# 6. Проверить логи
docker-compose logs -f bot
```
