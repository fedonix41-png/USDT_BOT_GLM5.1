# Roadmap проекта

## Текущий статус

**MVP завершён.** Бот работает в Docker Compose: Long Polling, PostgreSQL, Redis, ARQ Worker.

**Реализовано:**
- 16 handlers (client, operator, admin)
- 6 сервисов (Encryption, User, Order, Rate, Settings, Notification)
- FSM для многошаговых сценариев
- Шифрование реквизитов (AES-256-CBC)
- Уведомления через ARQ-очередь

---

## Приоритеты развития

| # | P | Задача | Статус |
|---|---|--------|--------|
| 1 | P0 | Graceful shutdown (SIGTERM) | ✅ |
| 2 | P0 | Глобальный обработчик ошибок aiogram | ✅ |
| 3 | P0 | Проверка `is_blocked` в UserMiddleware | ✅ |
| 4 | P1 | Обработка потери соединения с БД | ✅ |
| 5 | P1 | ThrottlingMiddleware (антиспам) | ✅ |
| 6 | P1 | Лимит попыток FSM-ввода (3 попытки) | ✅ |
| 7 | P2 | Redis-кеш флагов вместо in-memory dict | ✅ |
| 8 | P2 | Структурированное JSON-логирование | ✅ |
| 9 | P2 | Healthcheck HTTP-эндпоинт для bot-контейнера | ✅ |
| 10 | P2 | Улучшение обработки уведомлений | ✅ |
| 11 | P3 | Web-админка (REST API) | ❌ |
| 12 | P3 | Мониторинг (Prometheus + Grafana) | ❌ |
| 13 | P3 | Интеграция с криптобиржей | ❌ |
| 14 | P3 | Мультивалютность | ❌ |
| 15 | P3 | Другие каналы уведомлений (email, SMS) | ❌ |

---

## P0 — Критично для production

### 1. Graceful shutdown (SIGTERM)

**Проблема:** `main.py` не обрабатывает SIGTERM. При Docker `restart` транзакции БД могут оборваться, Long Polling прерывается без чистого завершения.

**Решение:**
```python
# app/main.py
import signal

async def shutdown():
    await dp.stop_polling()
    await bot.session.close()
    await async_engine.dispose()

signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(shutdown()))
```

**Файлы:** `app/main.py`

---

### 2. Глобальный обработчик ошибок aiogram

**Проблема:** Необработанные исключения в handlers молча проглатываются — пользователь не получает ответа, ошибка не логируется.

**Решение:**
```python
# app/bot.py
@dp.errors()
async def error_handler(event: ErrorEvent):
    logger.error(f"Error: {event.exception}", exc_info=True)
    if event.update.message:
        await event.update.message.answer("Произошла ошибка, попробуйте позже")
    elif event.update.callback_query:
        await event.update.callback_query.answer("Ошибка", show_alert=True)
```

**Файлы:** `app/bot.py`

---

### 3. Проверка `is_blocked` в UserMiddleware

**Проблема:** Поле `is_blocked` существует в модели User, но нигде не проверяется. Нет механизма блокировки клиентов.

**Решение:**
```python
# app/middlewares/user_middleware.py
if user.is_blocked and user.role not in (RoleEnum.admin, RoleEnum.super_admin):
    await event.answer("Вы заблокированы. Обратитесь в поддержку.")
    return
```

**Файлы:** `app/middlewares/user_middleware.py`

---

## P1 — Важно для стабильности

### 4. Обработка потери соединения с БД

**Проблема:** Если PostgreSQL недоступен, `DBSessionMiddleware` выбросит исключение — пользователь не получит ответа.

**Решение:** В `DBSessionMiddleware.__call__` обернуть создание сессии в `try/except`, при ошибке отправить «Сервис временно недоступен».

**Файлы:** `app/middlewares/db_session.py`

---

### 5. ThrottlingMiddleware (антиспам)

**Проблема:** Нет защиты от спама — пользователь может отправлять сообщения с любой частотой.

**Решение:**
- Создать `app/middlewares/throttling.py`
- Лимиты: 1 сообщение/сек для команд, 5 сообщений/мин для FSM-ввода
- Механизм: in-memory dict с `time.monotonic()` или Redis

**Файлы:** `app/middlewares/throttling.py` (новый)

---

### 6. Лимит попыток FSM-ввода (3 попытки)

**Проблема:** При невалидном вводе в FSM пользователь может бесконечно вводить неверные данные.

**Решение:**
- В каждом FSM handler'е хранить счётчик попыток в `state.proxy()`
- После 3 невалидных вводов: `await state.clear()`, отправить «Слишком много ошибок»

**Затронутые FSM:** `OrderBuyStates`, `OrderSellStates`, `ChangeRateStates`, `ChangeLinksStates`, `StatisticsStates`, `AssignRoleStates`, `SupportStates`

---

## P2 — Полезно для операционной эффективности

### 7. Redis-кеш флагов вместо in-memory dict

**Проблема:** `BotStatusMiddleware` использует in-memory dict. При запуске нескольких инстансов кеш не синхронизируется.

**Решение:** Заменить `_bot_enabled_cache` dict на чтение из Redis (база 0, ключ `bot_enabled`/`buy_enabled`/`sell_enabled`, TTL 30 сек).

**Файлы:** `app/middlewares/bot_status.py`

---

### 8. Структурированное JSON-логирование

**Проблема:** Текстовый формат логов неудобно парсить в Docker-окружении (Grafana Loki, ELK).

**Решение:**
```python
import logging, json
class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        })
```

**Файлы:** `app/main.py`

---

### 9. Healthcheck HTTP-эндпоинт

**Проблема:** Docker не может определить, жив ли бот — при зависании Long Polling контейнер работает, но не обрабатывает сообщения.

**Решение:**
- Запустить aiohttp web на порту 8080 рядом с Long Polling
- `GET /health` → 200 OK + проверка DB ping (`SELECT 1`)

**Файлы:** `app/health.py` (новый), `docker-compose.yml`

---

### 10. Улучшение обработки уведомлений

**Проблема:** При провале отправки (ARQ max_tries=3) чат остаётся в таблице `notification_chats`, следующие уведомления теряются.

**Решение:**
- Добавить поле `is_active` в `NotificationChat` + миграция
- При исчерпании попыток: `is_active = False`, уведомить SuperAdmin

**Файлы:** `app/database/models/notification_chat.py`, `app/tasks/jobs.py`

---

## P3 — Расширение функциональности

### 11. Web-админка (REST API)
REST API для управления курсами, заявками, пользователями. Требует авторизации, отдельного HTTP-сервера.

### 12. Мониторинг (Prometheus + Grafana)
Метрики (заявки, время ответа, ошибки), дашборд, алерты.

### 13. Интеграция с криптобиржей
`ExchangeService` — автоматическая проверка платежей, курс из API биржи.

### 14. Мультивалютность
Расширение `order_type` (BTC, ETH и др.), динамические реквизиты, отдельные курсы.

### 15. Другие каналы уведомлений
Расширение `NotificationService` для email, SMS.

---

## Пост-деплойные фиксы

| Баг | Причина | Исправление |
|-----|---------|-------------|
| Enum `name=` mismatch | ORM генерирует `roleenum`, миграция — `user_role` | Явный `name="user_role"` в `Enum()` |
| ARQ `RedisSettings` перемещён | В ARQ v0.26.x перенесён в `arq.connections` | Импорт `from arq.connections import RedisSettings` |
| `ARQ_REDIS_URL` в Docker | `localhost` не резолвится в контейнере | `redis://redis:6379/1` в environment |

---

## Пробелы в реализации

| Пробел | Где | Влияние |
|--------|-----|---------|
| ~~`is_blocked` не проверяется~~ | ~~`user_middleware.py`~~ | ~~Нет блокировки клиентов~~ ✅ |
| ~~In-memory кеш вместо Redis~~ | ~~`bot_status.py`~~ | ~~Несинхронизация при масштабировании~~ ✅ |
| ~~Нет глобального error handler~~ | ~~`bot.py`~~ | ~~Молчаливое зависание при ошибках~~ ✅ |
| ~~Нет SIGTERM обработки~~ | ~~`main.py`~~ | ~~Потеря данных при restart~~ ✅ |
| ~~Нет throttling~~ | ~~Все handlers~~ | ~~Уязвимость к спаму~~ ✅ |
| ~~Нет healthcheck~~ | ~~bot контейнер~~ | ~~Невозможность обнаружить зависание~~ ✅ |
| ~~Необработанные ошибки уведомлений~~ | ~~`jobs.py`~~ | ~~Потеря уведомлений при ошибках~~ ✅ |

---

## Порядок реализации

```
P0 (блокирующие)  →  P1 (стабильность)  →  P2 (эффективность)  →  P3 (расширение)
1. SIGTERM            4. DB errors          7. Redis-кеш          11. Web-админка
2. Error handler      5. Throttling         8. JSON-логи          12. Мониторинг
3. is_blocked         6. FSM limits         9. Healthcheck        13. Криптобиржа
                                            10. Notifications     14. Мультивалютность
                                                                  15. Email/SMS
```
