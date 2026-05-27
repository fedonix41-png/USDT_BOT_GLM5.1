# Схема базы данных

> **SSOT:** Этот документ — единственный источник истины для схемы БД, таблиц и enum-типов.
> При упоминании enum в других документах используйте ссылку: `см. database.md#enum-типы`.

---

## Обзор

База данных PostgreSQL 15 содержит 7 таблиц, 4 enum-типа и набор индексов для оптимизации запросов. Управление схемой — через Alembic миграции.

---

## Enum-типы (Единственный источник истины)

> **Важно:** Все enum-типы описаны только здесь. При упоминании в моделях или modules.md используйте ссылку на этот раздел.

### RoleEnum

**Имя типа в PostgreSQL:** `user_role`

| Значение | Описание | Уровень |
|----------|----------|---------|
| `super_admin` | Суперадминистратор | 4 (максимальный) |
| `admin` | Администратор | 3 |
| `operator` | Оператор | 2 |
| `client` | Клиент | 1 (базовый) |

### OrderTypeEnum

**Имя типа в PostgreSQL:** `order_type`

| Значение | Описание |
|----------|----------|
| `buy` | Покупка USDT клиентом |
| `sell` | Продажа USDT клиентом |

### OrderStatusEnum

**Имя типа в PostgreSQL:** `order_status`

| Значение | Описание |
|----------|----------|
| `created` | Заявка создана, ожидает действий |
| `cancelled` | Заявка отменена (клиентом или оператором) |
| `completed` | Заявка завершена оператором |

### RateTypeEnum

**Имя типа в PostgreSQL:** `rate_type`

| Значение | Описание |
|----------|----------|
| `buy` | Курс покупки (бот продаёт USDT) |
| `sell` | Курс продажи (бот покупает USDT) |

### Правила объявления Enum в SQLAlchemy

```python
# ПРАВИЛЬНО — имя совпадает с миграцией:
role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum, name="user_role"), ...)

# НЕПРАВИЛЬНО — SQLAlchemy сгенерирует "roleenum", которого нет в БД:
role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum), ...)
```

---

## Таблицы

### users — Пользователи

| Столбец | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | `SERIAL` | `PRIMARY KEY` | Внутренний ID |
| `telegram_id` | `BIGINT` | `UNIQUE NOT NULL` | Telegram ID |
| `username` | `VARCHAR(255)` | `NULL` | Telegram @username |
| `full_name` | `VARCHAR(255)` | `NULL` | Полное имя из Telegram |
| `role` | `user_role` | `DEFAULT 'client'` | Роль пользователя |
| `is_blocked` | `BOOLEAN` | `DEFAULT FALSE` | Флаг блокировки |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Дата регистрации |

**Особенности:**
- При `/start` создаётся с `role='client'`
- Если `telegram_id == SUPER_ADMIN_TELEGRAM_ID` → `role='super_admin'`

---

### orders — Заявки

| Столбец | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | `SERIAL` | `PRIMARY KEY` | ID заявки |
| `user_id` | `INTEGER` | `FK → users.id NOT NULL` | Клиент |
| `order_type` | `order_type` | `NOT NULL` | Тип: buy/sell |
| `amount_usdt` | `NUMERIC(18,8)` | `NOT NULL` | Сумма USDT |
| `rate` | `NUMERIC(18,2)` | `NOT NULL` | Курс RUB/USDT |
| `total_fiat` | `NUMERIC(18,2)` | `NOT NULL` | Сумма в рублях |
| `status` | `order_status` | `DEFAULT 'created'` | Статус |
| `payment_link_snapshot` | `TEXT` | `NULL` | Зашифрованные реквизиты |
| `link_broken` | `BOOLEAN` | `DEFAULT FALSE` | Флаг жалобы |
| `message_id` | `INTEGER` | `NULL` | ID сообщения клиента |
| `chat_id` | `BIGINT` | `NULL` | Chat ID клиента |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Дата создания |
| `updated_at` | `TIMESTAMP` | `ON UPDATE NOW()` | Дата обновления |

**Индексы:**

| Имя | Столбцы | Назначение |
|-----|---------|------------|
| `ix_orders_user_id` | `(user_id)` | Поиск заявок пользователя |
| `ix_orders_status_created` | `(status, created_at)` | Активные заявки, пагинация |
| `ix_orders_type_created` | `(order_type, created_at)` | Фильтрация по типу |

---

### rates — Курсы

| Столбец | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | `SERIAL` | `PRIMARY KEY` | ID записи |
| `rate_type` | `rate_type` | `NOT NULL` | Тип: buy/sell |
| `value` | `NUMERIC(18,2)` | `NOT NULL` | Курс RUB/USDT |
| `set_by` | `INTEGER` | `FK → users.id NOT NULL` | Админ |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Дата установки |

**Особенности:**
- Append-only: история сохраняется полностью
- Текущий курс = последняя запись с данным `rate_type`, `ORDER BY created_at DESC`

---

### global_settings — Глобальные настройки

| Столбец | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `key` | `VARCHAR(255)` | `PRIMARY KEY` | Ключ |
| `value` | `TEXT` | `NOT NULL` | Значение |

**Ключи и defaults:**

| Ключ | Default | Описание |
|------|---------|----------|
| `bot_enabled` | `"1"` | Глобальное включение бота |
| `buy_enabled` | `"1"` | Разрешена покупка |
| `sell_enabled` | `"1"` | Разрешена продажа |
| `payment_link_buy` | `""` | Реквизиты (зашифровано) |
| `payment_link_sell` | `""` | Реквизиты (зашифровано) |

---

### notification_chats — Чаты уведомлений

| Столбец | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | `SERIAL` | `PRIMARY KEY` | ID |
| `chat_id` | `BIGINT` | `UNIQUE NOT NULL` | Telegram Chat ID |
| `added_by` | `INTEGER` | `FK → users.id NOT NULL` | Админ |
| `is_active` | `BOOLEAN` | `DEFAULT TRUE` | Активность |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Дата добавления |

---

### audit_logs — Аудит-лог

| Столбец | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | `SERIAL` | `PRIMARY KEY` | ID |
| `user_id` | `INTEGER` | `FK → users.id NOT NULL` | Кто |
| `action` | `VARCHAR(255)` | `NOT NULL` | Тип действия |
| `details` | `JSONB` | `NULL` | Параметры |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Дата |

**Типы действий:**

| Action | Пример details |
|--------|----------------|
| `change_rate_buy` | `{"old": "95.50", "new": "96.00"}` |
| `change_rate_sell` | `{"old": "94.00", "new": "94.50"}` |
| `change_link_buy` | `{"type": "buy"}` |
| `change_link_sell` | `{"type": "sell"}` |
| `toggle_bot` | `{"value": "0"}` |
| `toggle_buy` | `{"value": "0"}` |
| `toggle_sell` | `{"value": "1"}` |
| `assign_role` | `{"target_user_id": 123, "role": "operator"}` |
| `add_notification_chat` | `{"chat_id": -1001234567890}` |
| `remove_notification_chat` | `{"chat_id": -1001234567890}` |

---

### api_tokens — Токены REST API

| Столбец | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | `SERIAL` | `PRIMARY KEY` | ID |
| `user_id` | `INTEGER` | `FK → users.id ON DELETE CASCADE` | Пользователь |
| `token_hash` | `VARCHAR(64)` | `NOT NULL` | SHA-256 хеш |
| `jti` | `VARCHAR(36)` | `UNIQUE NOT NULL` | JWT ID |
| `expires_at` | `TIMESTAMP` | `NOT NULL` | Истечение |
| `revoked` | `BOOLEAN` | `DEFAULT FALSE` | Отозван |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Создание |

**Индексы:**

| Имя | Столбцы |
|-----|---------|
| `ix_api_tokens_user_id` | `(user_id)` |
| `ix_api_tokens_jti` | `(jti)` |

---

## Диаграмма связей

```
┌──────────────┐       ┌──────────────┐
│    users     │       │    rates     │
├──────────────┤       ├──────────────┤
│ id (PK)      │◄──┐   │ id (PK)      │
│ telegram_id  │   │   │ rate_type    │
│ username     │   │   │ value        │
│ full_name    │   │   │ set_by (FK)──┼──┘
│ role         │   │   │ created_at   │
│ is_blocked   │   │   └──────────────┘
│ created_at   │   │
└──────┬───────┘   │   ┌──────────────────┐
       │           │   │  audit_logs      │
       │           │   ├──────────────────┤
       │           │   │ id (PK)          │
       ├───────────┼──►│ user_id (FK)     │
       │           │   │ action           │
       │           │   │ details (JSONB)  │
       │           │   │ created_at       │
       │           │   └──────────────────┘
       │           │
       │           │   ┌──────────────────────┐
       │           │   │ notification_chats   │
       │           │   ├──────────────────────┤
       │           │   │ id (PK)              │
       ├───────────┼──►│ chat_id (UNIQUE)     │
       │           │   │ added_by (FK)        │
       │           │   │ is_active            │
       │           │   │ created_at           │
       │           │   └──────────────────────┘
       │           │
       │           │   ┌──────────────────┐
       │           │   │    orders        │
       │           │   ├──────────────────┤
       ├───────────┼──►│ id (PK)          │
       │           │   │ user_id (FK)     │
       │           │   │ order_type       │
       │           │   │ amount_usdt      │
       │           │   │ rate             │
       │           │   │ total_fiat       │
       │           │   │ status           │
       │           │   │ payment_link_... │
       │           │   │ link_broken      │
       │           │   │ message_id       │
       │           │   │ chat_id          │
       │           │   │ created_at       │
       │           │   │ updated_at       │
       │           │   └──────────────────┘
       │           │
       │           │   ┌──────────────────┐
       │           │   │ global_settings   │
       │           │   ├──────────────────┤
       │           │   │ key (PK)         │
       │           │   │ value            │
       │           │   └──────────────────┘
       │           │
       └───────────┘
```

---

## Миграции

### Команды

```bash
# Применить все миграции
uv run alembic upgrade head

# Создать новую миграцию
uv run alembic revision --autogenerate -m "описание"

# Откатить последнюю миграцию
uv run alembic downgrade -1
```

### Существующие миграции

| Файл | Назначение |
|------|------------|
| `001_initial.py` | Создание всех таблиц, enum-типов, индексов |
| `002_add_is_active_notification.py` | Добавление `is_active` в `notification_chats` |
| `003_add_api_tokens.py` | Создание таблицы `api_tokens` |

---

## См. также

- **Архитектура:** `architecture.md`
- **Структура файлов:** `modules.md`
- **Роли и права:** `roles.md`
