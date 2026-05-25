# Схема базы данных

## Обзор

База данных PostgreSQL 15 содержит 6 таблиц, 4 enum-типа и набор индексов для оптимизации запросов. Управление схемой — через Alembic миграции.

---

## Enum типы

### RoleEnum

Роли пользователей с иерархией прав.

**Имя типа в PostgreSQL:** `user_role`

| Значение | Описание | Уровень |
|----------|----------|---------|
| `super_admin` | Суперадминистратор | 4 (максимальный) |
| `admin` | Администратор | 3 |
| `operator` | Оператор | 2 |
| `client` | Клиент | 1 (базовый) |

### OrderTypeEnum

Тип заявки.

**Имя типа в PostgreSQL:** `order_type`

| Значение | Описание |
|----------|----------|
| `buy` | Покупка USDT клиентом |
| `sell` | Продажа USDT клиентом |

### OrderStatusEnum

Статус заявки.

**Имя типа в PostgreSQL:** `order_status`

| Значение | Описание |
|----------|----------|
| `created` | Заявка создана, ожидает действий |
| `cancelled` | Заявка отменена (клиентом или оператором) |
| `completed` | Заявка завершена оператором |

### RateTypeEnum

Тип курса.

**Имя типа в PostgreSQL:** `rate_type`

| Значение | Описание |
|----------|----------|
| `buy` | Курс покупки (бот продаёт USDT) |
| `sell` | Курс продажи (бот покупает USDT) |

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
| `role` | `ENUM(RoleEnum)` | `DEFAULT 'client'` | Роль пользователя |
| `is_blocked` | `BOOLEAN` | `DEFAULT FALSE` | Флаг блокировки (зарезервировано) |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Дата регистрации |

**Связи:**
- `orders` → `Order.user_id` (один-ко-многим)
- `rates_set` → `Rate.set_by` (один-ко-многим)

**Особенности:**
- При `/start` пользователь создаётся с `role='client'`
- Если `telegram_id == SUPER_ADMIN_TELEGRAM_ID` → `role='super_admin'`
- `username` и `full_name` могут быть NULL (пользователь без username)

---

### orders — Заявки

Основная таблица — заявки на покупку и продажу USDT.

| Столбец | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | `SERIAL` | `PRIMARY KEY` | ID заявки |
| `user_id` | `INTEGER` | `FOREIGN KEY → users.id NOT NULL` | Клиент, создавший заявку |
| `order_type` | `ENUM(OrderTypeEnum)` | `NOT NULL` | Тип: `buy` или `sell` |
| `amount_usdt` | `NUMERIC(18,8)` | `NOT NULL` | Сумма в USDT |
| `rate` | `NUMERIC(18,2)` | `NOT NULL` | Курс на момент создания (RUB/USDT) |
| `total_fiat` | `NUMERIC(18,2)` | `NOT NULL` | Сумма в фиате (amount_usdt × rate) |
| `status` | `ENUM(OrderStatusEnum)` | `DEFAULT 'created'` | Статус заявки |
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

**Связи:**
- `user_id` → `users.id` (многие-к-одному)

**Особенности:**
- `payment_link_snapshot` — зашифрованный AES-256-CBC текст (hex-строка). Хранит реквизиты на момент создания, чтобы при смене реквизитов админом старые заявки сохраняли оригинальные данные
- `message_id` + `chat_id` — используются для редактирования сообщения клиента при обновлении реквизитов (битая ссылка)
- `NUMERIC(18,8)` для USDT — поддержка дробных значений с высокой точностью
- `NUMERIC(18,2)` для фиата — рубли с копейками

---

### rates — Курсы

История изменений курсов. Каждое изменение — новая запись (append-only).

| Столбец | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | `SERIAL` | `PRIMARY KEY` | ID записи |
| `rate_type` | `ENUM(RateTypeEnum)` | `NOT NULL` | Тип курса: `buy` или `sell` |
| `value` | `NUMERIC(18,2)` | `NOT NULL` | Значение курса (RUB/USDT) |
| `set_by` | `INTEGER` | `FOREIGN KEY → users.id NOT NULL` | Админ, установивший курс |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Дата установки |

**Связи:**
- `set_by` → `users.id` (многие-к-одному)

**Особенности:**
- Текущий курс определяется как последняя запись с данным `rate_type`, `ORDER BY created_at DESC`
- История сохраняется полностью — позволяет отслеживать все изменения
- При отсутствии записей сервис возвращает `None` — бот показывает «Курс не установлен»

---

### global_settings — Глобальные настройки

Хранилище ключ-значение для управления состоянием бота.

| Столбец | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `key` | `VARCHAR(255)` | `PRIMARY KEY` | Ключ настройки |
| `value` | `TEXT` | `NOT NULL` | Значение |

**Ключи:**

| Ключ | Тип значения | Описание | Default при отсутствии |
|------|-------------|----------|------------------------|
| `bot_enabled` | `"1"` или `"0"` | Глобальное включение/отключение бота для клиентов | `"1"` (включён) |
| `buy_enabled` | `"1"` или `"0"` | Разрешена ли покупка USDT | `"1"` (разрешена) |
| `sell_enabled` | `"1"` или `"0"` | Разрешена ли продажа USDT | `"1"` (разрешена) |
| `payment_link_buy` | Зашифрованный текст (hex) | Реквизиты оплаты для покупки | `""` (пусто) |
| `payment_link_sell` | Зашифрованный текст (hex) | Реквизиты для продажи | `""` (пусто) |

**Особенности:**
- Если ключ отсутствует в БД, сервис возвращает default (разрешительный для флагов, пустую строку для ссылок)
- Это позволяет боту работать даже до первоначальной настройки админом
- Значения флагов кешируются в Redis с TTL 30 секунд
- `payment_link_*` — зашифрованы через AES-256-CBC (`EncryptionService`)

---

### notification_chats — Чаты уведомлений

Чаты/каналы, куда бот отправляет алерты о событиях.

| Столбец | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | `SERIAL` | `PRIMARY KEY` | ID записи |
| `chat_id` | `BIGINT` | `UNIQUE NOT NULL` | Telegram Chat ID |
| `added_by` | `INTEGER` | `FOREIGN KEY → users.id NOT NULL` | Админ, добавивший чат |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Дата добавления |

**Связи:**
- `added_by` → `users.id` (многие-к-одному)

**Особенности:**
- Перед добавлением бот проверяет, что он является админом в чате (`bot.get_chat_member`)
- При ошибке отправки (Forbidden, BadRequest) — чат не удаляется, ошибка логируется
- Один и тот же чат невозможно добавить дважды (`UNIQUE` на `chat_id`)

---

### audit_logs — Аудит-лог

Фиксирует все действия администраторов для отслеживания изменений.

| Столбец | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | `SERIAL` | `PRIMARY KEY` | ID записи |
| `user_id` | `INTEGER` | `FOREIGN KEY → users.id NOT NULL` | Кто совершил действие |
| `action` | `VARCHAR(255)` | `NOT NULL` | Тип действия |
| `details` | `JSONB` | `NULL` | Детали изменения (параметры) |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Дата действия |

**Связи:**
- `user_id` → `users.id` (многие-к-одному)

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
- `details` в формате JSONB — позволяет хранить структурированные данные и выполнять запросы по полям
- Записи только добавляются (append-only), никогда не удаляются и не изменяются

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
       └───────────┘    (нет FK на users —
                         автономное хранилище)
```

---

## Миграции

### Alembic

- Конфигурация: `migrations/alembic.ini`, `migrations/env.py`
- Первая миграция: `migrations/versions/001_initial.py`
  - Создаёт все 6 таблиц
  - Создаёт 4 enum-типа (`RoleEnum`, `OrderTypeEnum`, `OrderStatusEnum`, `RateTypeEnum`)
  - Создаёт индексы на таблице `orders`
- Команда применения: `uv run alembic upgrade head`
- Новая миграция: `uv run alembic revision --autogenerate -m "описание"`
- Для тестов: in-memory SQLite с `create_all()` (без миграций)

**Важно:** имена PostgreSQL enum-типов в ORM-моделях должны совпадать с именами в миграции. При использовании `Enum(RoleEnum)` SQLAlchemy генерирует имя по имени класса в нижнем регистре (`roleenum`), но миграция создаёт тип `user_role`. Поэтому в ORM-моделях необходимо явно указывать `name=`:

```python
# Правильно — имя совпадает с миграцией:
role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum, name="user_role"), ...)

# Неправильно — SQLAlchemy сгенерирует "roleenum", которого нет в БД:
role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum), ...)
```
