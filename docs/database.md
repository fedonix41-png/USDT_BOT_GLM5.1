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

Хранит всех пользователей бота с их ролями.

| Столбец | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | `SERIAL` | `PRIMARY KEY` | Внутренний ID |
| `telegram_id` | `BIGINT` | `UNIQUE NOT NULL` | Telegram ID пользователя |
| `username` | `VARCHAR(255)` | `NULL` | Telegram @username |
| `full_name` | `VARCHAR(255)` | `NULL` | Полное имя из Telegram |
| `phone` | `VARCHAR(20)` | `NULL` | Номер телефона |
| `role` | `user_role` | `DEFAULT 'client'` | Роль пользователя |
| `is_blocked` | `BOOLEAN` | `DEFAULT FALSE` | Флаг блокировки |
| `balance` | `NUMERIC(10,2)` | `DEFAULT 0.00` | Баланс USDT |
| `fiat_balance` | `NUMERIC(10,2)` | `DEFAULT 0.00` | Баланс RUB |
| `referred_by` | `VARCHAR(255)` | `NULL` | Реферер (username) |
| `referrals_count` | `INTEGER` | `DEFAULT 0` | Количество рефералов |
| `referral_earned` | `NUMERIC(10,2)` | `DEFAULT 0.00` | Заработано с рефералов |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Дата регистрации |

**Связи:**
- `orders` → `Order.user_id` (один-ко-многим)
- `rates_set` → `Rate.set_by` (один-ко-многим)

**Особенности:**
- При `/start` пользователь создаётся с `role='client'`
- Если `telegram_id == SUPER_ADMIN_TELEGRAM_ID` → автоматически `role='super_admin'`
- `username` и `full_name` могут быть NULL (пользователь без username)

---

### orders — Заявки

Основная таблица — заявки на покупку и продажу USDT.

| Столбец | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | `SERIAL` | `PRIMARY KEY` | ID заявки |
| `user_id` | `INTEGER` | `FK → users.id NOT NULL` | Клиент, создавший заявку |
| `order_type` | `order_type` | `NOT NULL` | Тип: `buy` или `sell` |
| `amount_usdt` | `NUMERIC(18,8)` | `NOT NULL` | Сумма в USDT |
| `rate` | `NUMERIC(18,2)` | `NOT NULL` | Курс на момент создания (RUB/USDT) |
| `total_fiat` | `NUMERIC(18,2)` | `NOT NULL` | Сумма в фиате (amount_usdt × rate) |
| `status` | `order_status` | `DEFAULT 'created'` | Статус заявки |
| `payment_link_snapshot` | `TEXT` | `NULL` | Зашифрованные реквизиты на момент создания |
| `link_broken` | `BOOLEAN` | `DEFAULT FALSE` | Флаг жалобы на неработающую ссылку |
| `message_id` | `INTEGER` | `NULL` | ID сообщения с заявкой в чате клиента |
| `chat_id` | `BIGINT` | `NULL` | Chat ID клиента (для редактирования сообщения) |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Дата создания |
| `updated_at` | `TIMESTAMP` | `DEFAULT NOW() ON UPDATE NOW()` | Дата последнего обновления |

**Индексы:**

| Имя | Столбцы | Назначение |
|-----|---------|------------|
| `ix_orders_user_id` | `(user_id)` | Поиск заявок пользователя |
| `ix_orders_status_created` | `(status, created_at)` | Активные заявки за период, пагинация |
| `ix_orders_type_created` | `(order_type, created_at)` | Фильтрация по типу + статистика |

**Особенности:**
- `payment_link_snapshot` — зашифрованный AES-256-CBC текст (hex-строка). Хранит реквизиты на момент создания, чтобы при смене реквизитов админом старые заявки сохраняли оригинальные данные (историческая точность)
- `message_id` + `chat_id` — используются для редактирования сообщения клиента при обновлении реквизитов (сценарий "битая ссылка" → админ меняет реквизиты → ARQ обновляет сообщения всем клиентам с link_broken=True)
- `NUMERIC(18,8)` для USDT — поддержка дробных значений с высокой точностью (до 8 знаков)
- `NUMERIC(18,2)` для фиата — рубли с копейками (до 2 знаков)

---

### rates — Курсы

История изменений курсов. Каждое изменение — новая запись (append-only).

| Столбец | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | `SERIAL` | `PRIMARY KEY` | ID записи |
| `rate_type` | `rate_type` | `NOT NULL` | Тип курса: `buy` или `sell` |
| `value` | `NUMERIC(18,2)` | `NOT NULL` | Значение курса (RUB/USDT) |
| `set_by` | `INTEGER` | `FK → users.id NOT NULL` | Админ, установивший курс |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Дата установки |

**Особенности:**
- Append-only: история сохраняется полностью — позволяет отслеживать все изменения и анализировать динамику
- Текущий курс = последняя запись с данным `rate_type`, `ORDER BY created_at DESC`
- При отсутствии записей сервис возвращает `None` — бот показывает «Курс не установлен»

---

### global_settings — Глобальные настройки

Хранилище ключ-значение для управления состоянием бота.

| Столбец | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `key` | `VARCHAR(255)` | `PRIMARY KEY` | Ключ настройки |
| `value` | `TEXT` | `NOT NULL` | Значение |

**Ключи и defaults:**

| Ключ | Default | Описание |
|------|---------|----------|
| `bot_enabled` | `"1"` | Глобальное включение бота для клиентов |
| `buy_enabled` | `"1"` | Разрешена покупка USDT |
| `sell_enabled` | `"1"` | Разрешена продажа USDT |
| `payment_link_buy` | `""` | Реквизиты оплаты для покупки (зашифровано) |
| `payment_link_sell` | `""` | Реквизиты для продажи (зашифровано) |

**Особенности:**
- Разрешительная логика: если ключ отсутствует в БД, сервис возвращает default (`"1"` для флагов, `""` для ссылок). Это позволяет боту работать сразу после деплоя, до первоначальной настройки админом
- Значения флагов кешируются в Redis с TTL 30 секунд — снижает нагрузку на PostgreSQL и поддерживает горизонтальное масштабирование
- `payment_link_*` — зашифрованы через AES-256-CBC (`EncryptionService`). Ключ шифрования хранится в `.env` (`ENCRYPTION_KEY`)

---

### notification_chats — Чаты уведомлений

Чаты/каналы, куда бот отправляет алерты о событиях (новые заявки, жалобы, назначение ролей).

| Столбец | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | `SERIAL` | `PRIMARY KEY` | ID записи |
| `chat_id` | `BIGINT` | `UNIQUE NOT NULL` | Telegram Chat ID |
| `added_by` | `INTEGER` | `FK → users.id NOT NULL` | Админ, добавивший чат |
| `is_active` | `BOOLEAN` | `DEFAULT TRUE` | Флаг активности чата |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Дата добавения |

**Особенности:**
- Перед добавлением бот проверяет, что он является админом в чате (`bot.get_chat_member`). Иначе — ошибка
- При ошибке отправки (`TelegramForbiddenError`, `TelegramNotFound`) — чат помечается `is_active=False`, ошибка логируется. Уведомление отправляется SuperAdmin
- Один и тот же чат невозможно добавить дважды (`UNIQUE` на `chat_id`)
- `is_active=False` — чат временно деактивирован (ошибки отправки), можно повторно добавить после исправления

---

### audit_logs — Аудит-лог

Фиксирует все действия администраторов для отслеживания изменений и расследования инцидентов.

| Столбец | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | `SERIAL` | `PRIMARY KEY` | ID записи |
| `user_id` | `INTEGER` | `FK → users.id NOT NULL` | Кто совершил действие |
| `action` | `VARCHAR(255)` | `NOT NULL` | Тип действия |
| `details` | `JSONB` | `NULL` | Детали изменения (параметры) |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Дата действия |

**Типы действий (action):**

| Значение | Описание | Пример details |
|----------|----------|----------------|
| `change_rate_buy` | Изменение курса покупки | `{"old": "95.50", "new": "96.00"}` |
| `change_rate_sell` | Изменение курса продажи | `{"old": "94.00", "new": "94.50"}` |
| `change_link_buy` | Изменение реквизитов покупки | `{"type": "buy"}` |
| `change_link_sell` | Изменение реквизитов продажи | `{"type": "sell"}` |
| `toggle_bot` | Отключение/включение бота | `{"value": "0"}` |
| `toggle_buy` | Стоп/старт закупа | `{"value": "0"}` |
| `toggle_sell` | Стоп/старт продажи | `{"value": "1"}` |
| `assign_role` | Назначение роли | `{"target_user_id": 123, "role": "operator"}` |
| `add_notification_chat` | Добавление чата уведомлений | `{"chat_id": -1001234567890}` |
| `remove_notification_chat` | Удаление чата уведомлений | `{"chat_id": -1001234567890}` |

**Особенности:**
- `details` в формате JSONB — позволяет хранить структурированные данные и выполнять SQL-запросы по полям (например, найти все изменения курса конкретного пользователя)
- В ORM используется `JSONBCompat` — кросс-диалектный тип (JSONB на PostgreSQL, JSON на SQLite для тестов)
- Append-only: записи только добавляются, никогда не удаляются и не изменяются — полная история для аудита

---

### api_tokens — Токены REST API

Хранит refresh токены для JWT-аутентификации в REST API.

| Столбец | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | `SERIAL` | `PRIMARY KEY` | ID записи |
| `user_id` | `INTEGER` | `FK → users.id ON DELETE CASCADE` | Пользователь |
| `token_hash` | `VARCHAR(64)` | `NOT NULL` | SHA-256 хеш refresh токена |
| `jti` | `VARCHAR(36)` | `UNIQUE NOT NULL` | JWT ID (уникальный идентификатор) |
| `expires_at` | `TIMESTAMP` | `NOT NULL` | Дата истечения |
| `revoked` | `BOOLEAN` | `DEFAULT FALSE` | Флаг отзыва токена |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Дата создания |

**Индексы:**

| Имя | Столбцы | Назначение |
|-----|---------|------------|
| `ix_api_tokens_user_id` | `(user_id)` | Поиск токенов пользователя |
| `ix_api_tokens_jti` | `(jti)` | Поиск по JWT ID |

**Особенности:**
- Хранится SHA-256 хеш токена, а не сам токен — безопасность при утечке БД. Оригинальный токен невозможно восстановить
- Ротация токенов: при использовании refresh токена старый отзывается (`revoked=True`), создаётся новый. Защита от кражи токена
- `ON DELETE CASCADE` — при удалении пользователя все его токены автоматически удаляются

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
       │           │   │ api_tokens       │
       ├───────────┼──►│ id (PK)          │
       │           │   │ user_id (FK)     │
       │           │   │ token_hash       │
       │           │   │ jti (UNIQUE)     │
       │           │   │ expires_at       │
       │           │   │ revoked          │
       │           │   │ created_at       │
       │           │   └──────────────────┘
       │           │
       │           │   ┌──────────────────┐
       │           │   │ global_settings   │
       │           │   ├──────────────────┤
       │           │   │ key (PK)         │
       │           │   │ value            │
       │           │   └──────────────────┘
       │           │
       └───────────┘    (нет FK на users —
                         автономное хранилище)
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
| `004_add_phone_to_users.py` | Добавление поля `phone` в `users` |
| `005_add_user_balances.py` | Добавление полей `balance`, `fiat_balance`, `referred_by`, `referrals_count`, `referral_earned` в `users` |

---

## См. также

- **Архитектура:** `architecture.md`
- **Структура файлов:** `modules.md`
- **Роли и права:** `roles.md`
