# Активные проблемы и риски

> Этот документ содержит **только активные** проблемы и риски, требующие внимания.
> Устранённые проблемы — в git истории (commits, PR). Не дублируйте их здесь.

---

## Требующие реализации

### 1. Long Polling: окно потери обновлений

**Риск:** При перезапуске бота ~30 сек обновлений могут быть пропущены.

**Статус:** Допустимо для MVP. В будущем — переход на Webhook.

---

### 2. Graceful shutdown при Docker restart

**Риск:** Транзакции БД могут оборваться при Docker restart.

**Статус:** Обработчик SIGTERM реализован (`GracefulShutdown` в `main.py`). Проверить корректность обработки при `docker compose restart`.

---

## Активные проблемы (Аудит 27.05.2026)

### P1: Self-ban защита отсутствует

**Проблема:** Админ может случайно забанить сам себя, введя свой Telegram ID.

**Файл:** `app/handlers/admin/ban_user.py:41-45`

**Решение:** Добавить проверку:
```python
if target_telegram_id == message.from_user.id:
    await message.answer("Невозможно заблокировать самого себя.")
    await state.clear()
    return
```

---

### P1: Кнопка отмены на шаге запроса телефона

**Проблема:** Пользователь без username при создании заявки видит только «📱 Поделиться номером». Нет кнопки отмены.

**Файлы:** `app/handlers/client/buy.py:143-151`, `app/handlers/client/sell.py:142-150`

**Решение:** Добавить кнопку отмены в ReplyKeyboardMarkup:
```python
phone_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📱 Поделиться номером", request_contact=True)],
        [KeyboardButton(text="❌ Отмена")],
    ],
    resize_keyboard=True,
)
```

---

### P2: Inconsistency в использовании check_fsm_attempts()

**Проблема:** Разные обработчики используют `check_fsm_attempts()` по-разному:
- `ban_user.py` игнорирует возвращаемое значение
- `assign_roles.py` использует `should_continue`

**Файлы:** `app/handlers/admin/ban_user.py:36-39`, `app/handlers/admin/assign_roles.py:36-39`

**Решение:** Унифицировать:
```python
should_continue, _ = await check_fsm_attempts(state, message, "...")
if not should_continue:
    return
```

---

### P2: reset_fsm_attempts() не используется

**Проблема:** Функция определена в `helpers.py`, но нигде не вызывается. Счётчик попыток может накапливаться между FSM-сценариями.

**Файл:** `app/utils/helpers.py:51-56`

**Решение:** Вызывать перед началом каждого FSM-сценария:
```python
await reset_fsm_attempts(state)
await state.set_state(SomeStates.waiting_input)
```

---

## Рекомендации (не реализовано)

### Подмена номера телефона

При желании можно усилить защиту, добавив учёт попыток подмены через `check_fsm_attempts()` в `buy.py` / `sell.py`. На текущий момент проверка `message.contact.user_id != message.from_user.id` достаточна.

### Redis-кеш для флагов

Заменить in-memory dict в `bot_status.py` на Redis. Снижение нагрузки на PostgreSQL, синхронизация при масштабировании.

### Структурированное логирование

JSON-формат логов для Docker (Grafana Loki, ELK).

### Мониторинг

Prometheus метрики + Grafana дашборд + алерты при падении сервисов.

---

## Сводная таблица приоритетов

| Приоритет | Проблема | Файлы | Тип |
|-----------|----------|-------|-----|
| P1 | Self-ban защита | `ban_user.py` | Logic |
| P1 | Кнопка отмены на шаге телефона | `buy.py`, `sell.py` | UX |
| P2 | Inconsistency check_fsm_attempts | `ban_user.py` | Code quality |
| P2 | reset_fsm_attempts не используется | `helpers.py` + handlers | Code quality |

---

## См. также

- **Архитектура:** `architecture.md`
- **FSM-сценарии:** `scenarios.md`
