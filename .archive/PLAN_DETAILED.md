# Детальный план реализации Telegram-бота для обмена USDT

> На основе `PLAN.md` + уточнения пользователя.
> Статус: **проект с нуля** — нет ни одной строки кода.

---

## 0. Решения по неоднозначностям PLAN.md

| Вопрос | Решение |
|--------|---------|
| Режим получения обновлений | **Long Polling** (без FastAPI webhook) |
| Завершение заявки | **Оператор подтверждает** через inline-кнопку, клиент получает чек-уведомление |
| Начальные данные | Всё задаётся через бот-меню админом при первом запуске. Seed-скрипт НЕ нужен |
| Развёртывание | **Один VPS + Docker Compose** (bot, postgres, redis, arq-worker) |
| Поддержка | Сначала через бот (пересылка в чаты уведомлений, оператор отвечает), позже можно переключить на внешний чат |

---

## 1. Архитектура приложения

### 1.1. Компоненты системы

```
┌─────────────────────────────────────────────────────────────┐
│                      Docker Compose                         │
│                                                             │
│  ┌─────────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │  Bot        │  │ ARQ      │  │PostgreSQL │  │  Redis  │ │
│  │  (Long      │  │ Worker   │  │   15      │  │  7-alpine│ │
│  │   Polling)  │  │ (tasks)  │  │           │  │         │ │
│  └──────┬──────┘  └────┬─────┘  └─────┬─────┘  └────┬────┘ │
│         │              │              │              │      │
│         └──────────────┴──────────────┴──────────────┘      │
│                    SQLAlchemy Async + ARQ                    │
└─────────────────────────────────────────────────────────────┘
```

### 1.2. Слои приложения

```
handlers/      → Aiogram handlers + FSM (получение сообщений, отправка ответов)
middlewares/   → Проверка ролей, статуса бота
services/      → Бизнес-логика (заказы, курсы, шифрование, уведомления)
repositories/  → Доступ к данным (SQLAlchemy queries)
models/        → SQLAlchemy ORM модели
tasks/         → Фоновые задачи (ARQ)
config/        → Конфигурация (pydantic-settings)
```

---

## 2. Структура проекта

```
USDT_BOT_GLM5.1/
├── app/
│   ├── __init__.py
│   ├── main.py                          # Точка входа: запуск бота
│   ├── bot.py                           # Создание Bot + Dispatcher, регистрация роутеров
│   ├── config.py                        # Pydantic Settings (env vars)
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── engine.py                    # AsyncEngine + AsyncSessionMaker
│   │   ├── base.py                      # DeclarativeBase
│   │   └── models/
│   │       ├── __init__.py              # Экспорт всех моделей
│   │       ├── user.py                  # User ORM
│   │       ├── order.py                 # Order ORM
│   │       ├── rate.py                  # Rate ORM
│   │       ├── global_settings.py       # GlobalSettings ORM
│   │       ├── notification_chat.py     # NotificationChat ORM
│   │       └── audit_log.py            # AuditLog ORM
│   │
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base.py                      # Базовый репозиторий (CRUD generic)
│   │   ├── user_repo.py
│   │   ├── order_repo.py
│   │   ├── rate_repo.py
│   │   ├── settings_repo.py
│   │   ├── notification_repo.py
│   │   └── audit_repo.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── encryption.py               # AES-256-CBC шифрование/дешифрование
│   │   ├── user_service.py             # Регистрация, роли
│   │   ├── order_service.py            # Создание/отмена/завершение заявок
│   │   ├── rate_service.py             # Текущий курс, смена курса
│   │   ├── settings_service.py         # Флаги bot_enabled, buy_enabled, sell_enabled
│   │   ├── notification_service.py     # Отправка уведомлений в чаты
│   │   └── audit_service.py            # Логирование действий
│   │
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py                    # /start, регистрация, главное меню
│   │   ├── client/
│   │   │   ├── __init__.py
│   │   │   ├── buy.py                  # FSM: покупка USDT
│   │   │   ├── sell.py                 # FSM: продажа USDT
│   │   │   ├── rates.py                # Просмотр курсов
│   │   │   ├── support.py              # Поддержка
│   │   │   └── cancel_order.py         # Отмена заявки (inline callback)
│   │   ├── operator/
│   │   │   ├── __init__.py
│   │   │   ├── active_orders.py        # Активные заявки + пагинация
│   │   │   ├── complete_order.py       # Завершение заявки (inline callback)
│   │   │   └── statistics.py           # FSM: статистика за период
│   │   ├── admin/
│   │   │   ├── __init__.py
│   │   │   ├── change_rate.py          # FSM: смена курса
│   │   │   ├── change_links.py         # FSM: смена реквизитов
│   │   │   ├── toggle_flags.py         # Стоп/старт закуп, продажа, бот
│   │   │   ├── notification_chats.py   # Подменю управления чатами
│   │   │   └── assign_roles.py         # FSM: назначение ролей
│   │   └── common/
│   │       ├── __init__.py
│   │       └── broken_link.py          # Обработка «Ссылка не работает» (inline callback)
│   │
│   ├── middlewares/
│   │   ├── __init__.py
│   │   ├── bot_status.py               # Проверка bot_enabled (блокировка клиентов)
│   │   ├── role_guard.py               # Проверка прав роли на действие
│   │   └── db_session.py               # Инъекция DB-сессии в handler data
│   │
│   ├── keyboards/
│   │   ├── __init__.py
│   │   ├── client_kb.py                # ReplyKeyboardMarkup для Client
│   │   ├── operator_kb.py              # ReplyKeyboardMarkup для Operator
│   │   ├── admin_kb.py                 # ReplyKeyboardMarkup для Admin/SuperAdmin
│   │   └── inline_kb.py               # InlineKeyboardMarkup (заявки, пагинация, чаты)
│   │
│   ├── fsm/
│   │   ├── __init__.py
│   │   ├── order_states.py             # OrderCreation, OrderSell
│   │   ├── statistics_states.py        # StatisticsPeriod
│   │   ├── rate_states.py              # ChangeRate
│   │   ├── links_states.py            # ChangeLinks
│   │   ├── role_states.py             # AssignRole
│   │   └── support_states.py          # SupportChat
│   │
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── worker.py                   # ARQ worker config + Redis connection
│   │   └── jobs.py                     # Фоновые задачи (уведомления, обновление ссылок)
│   │
│   └── utils/
│       ├── __init__.py
│       ├── formatting.py              # Форматирование сообщений (HTML)
│       └── pagination.py             # Утилиты пагинации
│
├── migrations/
│   ├── alembic.ini
│   ├── env.py
│   ├── versions/
│   │   └── 001_initial.py             # Создание всех таблиц
│   └── script.py.mako
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_encryption.py
│   ├── test_order_service.py
│   ├── test_rate_service.py
│   ├── test_settings_service.py
│   └── test_handlers/
│       ├── __init__.py
│       ├── test_start.py
│       ├── test_buy.py
│       └── test_admin.py
│
├── pyproject.toml
├── uv.lock
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── .gitignore
├── .dockerignore
├── AGENTS.md
├── PLAN.md
└── PLAN_DETAILED.md                   # Этот файл
```

---

## 3. Зависимости и конфигурация

### 3.1. pyproject.toml

```toml
[project]
name = "usdt-bot"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "aiogram==3.15.*",
    "sqlalchemy[asyncio]==2.0.*",
    "asyncpg==0.30.*",
    "alembic==1.14.*",
    "redis==5.2.*",
    "arq==0.26.*",
    "pydantic-settings==2.7.*",
    "cryptography==44.0.*",
]

[project.optional-dependencies]
dev = [
    "pytest==8.3.*",
    "pytest-asyncio==0.24.*",
    "pytest-cov==6.0.*",
    "aiosqlite==0.20.*",    # Для тестов с in-memory SQLite
    "ruff==0.8.*",
]
```

### 3.2. .env.example

```env
# Telegram
BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11

# Database
DATABASE_URL=postgresql+asyncpg://usdt_bot:secret@postgres:5432/usdt_bot

# Redis
REDIS_URL=redis://redis:6379/0

# Encryption (32-byte hex key для AES-256)
ENCRYPTION_KEY=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef

# SuperAdmin Telegram ID (первый запуск)
SUPER_ADMIN_TELEGRAM_ID=123456789
```

### 3.3. config.py (Pydantic Settings)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    ENCRYPTION_KEY: str  # 64-char hex = 32 bytes AES-256
    SUPER_ADMIN_TELEGRAM_ID: int

    # Пагинация
    ORDERS_PER_PAGE: int = 5

    # ARQ
    ARQ_REDIS_URL: str = "redis://localhost:6379/1"

    class Config:
        env_file = ".env"
```

---

## 4. Docker

### 4.1. docker-compose.yml

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: usdt_bot
      POSTGRES_USER: usdt_bot
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-secret}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U usdt_bot"]
      interval: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      retries: 5

  bot:
    build: .
    command: uv run python -m app.main
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  arq-worker:
    build: .
    command: uv run arq app.tasks.worker.WorkerSettings
    env_file: .env
    depends_on:
      redis:
        condition: service_healthy
      postgres:
        condition: service_healthy
    restart: unless-stopped

volumes:
  pgdata:
```

### 4.2. Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

CMD ["uv", "run", "python", "-m", "app.main"]
```

---

## 5. База данных: модели и миграции

### 5.1. SQLAlchemy модели

#### Enum типы

```python
import enum

class RoleEnum(str, enum.Enum):
    super_admin = "super_admin"
    admin = "admin"
    operator = "operator"
    client = "client"

class OrderTypeEnum(str, enum.Enum):
    buy = "buy"
    sell = "sell"

class OrderStatusEnum(str, enum.Enum):
    created = "created"
    cancelled = "cancelled"
    completed = "completed"

class RateTypeEnum(str, enum.Enum):
    buy = "buy"
    sell = "sell"
```

#### User

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(SERIAL, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum), default=RoleEnum.client)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    orders = relationship("Order", back_populates="user")
    rates_set = relationship("Rate", back_populates="set_by_user")
```

#### Order

```python
class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(SERIAL, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    order_type: Mapped[OrderTypeEnum] = mapped_column(Enum(OrderTypeEnum), nullable=False)
    amount_usdt: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total_fiat: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[OrderStatusEnum] = mapped_column(
        Enum(OrderStatusEnum), default=OrderStatusEnum.created
    )
    payment_link_snapshot: Mapped[str | None] = mapped_column(Text)
    link_broken: Mapped[bool] = mapped_column(Boolean, default=False)
    message_id: Mapped[int | None] = mapped_column(Integer)
    chat_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="orders")

    __table_args__ = (
        Index("ix_orders_user_id", "user_id"),
        Index("ix_orders_status_created", "status", "created_at"),
        Index("ix_orders_type_created", "order_type", "created_at"),
    )
```

#### Rate

```python
class Rate(Base):
    __tablename__ = "rates"

    id: Mapped[int] = mapped_column(SERIAL, primary_key=True)
    rate_type: Mapped[RateTypeEnum] = mapped_column(Enum(RateTypeEnum), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    set_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    set_by_user = relationship("User", back_populates="rates_set")
```

#### GlobalSettings

```python
class GlobalSettings(Base):
    __tablename__ = "global_settings"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
```

#### NotificationChat

```python
class NotificationChat(Base):
    __tablename__ = "notification_chats"

    id: Mapped[int] = mapped_column(SERIAL, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    added_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    added_by_user = relationship("User")
```

#### AuditLog

```python
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(SERIAL, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    user = relationship("User")
```

### 5.2. Ключи global_settings

При первом запуске админ через бот задаст все значения. Но приложение при старте должно корректно обрабатывать отсутствие записей.

| Ключ | Тип значения | Описание | Default при отсутствии |
|------|-------------|----------|------------------------|
| `bot_enabled` | `"1"` / `"0"` | Глобальное включение бота | `"1"` |
| `buy_enabled` | `"1"` / `"0"` | Разрешена покупка | `"1"` |
| `sell_enabled` | `"1"` / `"0"` | Разрешена продажа | `"1"` |
| `payment_link_buy` | Зашифрованный текст | Реквизиты для покупки | `""` |
| `payment_link_sell` | Зашифрованный текст | Реквизиты для продажи | `""` |

> **Важно:** если ключ отсутствует в БД, сервис возвращает default. Это позволяет боту работать даже до того как админ задал все настройки.

### 5.3. Миграции (Alembic)

- Первая миграция `001_initial.py` создаёт все 6 таблиц + индексы + enum-типы.
- Команда: `uv run alembic upgrade head`
- Для тестов: in-memory SQLite (без миграций, `create_all`).

---

## 6. Сервисы (бизнес-логика)

### 6.1. EncryptionService

```python
class EncryptionService:
    """AES-256-CBC шифрование/дешифрование.
    Ключ: 32 байта из ENCRYPTION_KEY (hex).
    IV: генерируется случайно при каждом шифровании, 
    prepend к ciphertext (первые 16 байт).
    """
    def __init__(self, key_hex: str): ...
    def encrypt(self, plaintext: str) -> str: ...   # → hex-строка (IV + ciphertext)
    def decrypt(self, cipher_hex: str) -> str: ...  # ← hex-строка → plaintext
```

- Используется библиотека `cryptography` (`Cipher`, `algorithms`, `modes`, `padding`).
- IV — случайные 16 байт, записываются перед ciphertext.
- Результат — hex-строка для хранения в TEXT-поле БД.

### 6.2. UserService

```python
class UserService:
    async def get_or_create(self, session, telegram_id, username, full_name) -> User
    async def get_by_telegram_id(self, session, telegram_id) -> User | None
    async def set_role(self, session, user_id, role, set_by_user_id) -> User  # + audit
    async def is_super_admin(self, session, telegram_id) -> bool
```

- При `/start`: если пользователя нет → создать с `role=client`, если это `SUPER_ADMIN_TELEGRAM_ID` → роль `super_admin`.
- `set_role` логирует в `audit_logs`.

### 6.3. RateService

```python
class RateService:
    async def get_current_rate(self, session, rate_type: RateTypeEnum) -> Decimal | None
    async def set_rate(self, session, rate_type, value, set_by_user_id) -> Rate  # + audit
    async def get_rate_history(self, session, rate_type, limit=10) -> list[Rate]
```

- `get_current_rate` — последняя запись в таблице `rates` с данным `rate_type`, отсортированная по `created_at DESC`.
- Если записей нет — возвращает `None` (бот сообщит: «Курс не установлен»).

### 6.4. SettingsService

```python
class SettingsService:
    async def get(self, session, key: str) -> str | None
    async def set(self, session, key: str, value: str, user_id: int | None = None) -> None
    async def is_bot_enabled(self, session) -> bool
    async def is_buy_enabled(self, session) -> bool
    async def is_sell_enabled(self, session) -> bool
    async def get_payment_link(self, session, order_type: OrderTypeEnum) -> str
    async def set_payment_link(self, session, order_type, link: str, user_id: int) -> None
```

- `get_payment_link` — читает `payment_link_buy`/`payment_link_sell` из `global_settings`, расшифровывает через `EncryptionService`.
- `set_payment_link` — шифрует и сохраняет.
- Если ключ отсутствует — `is_bot_enabled`/`is_buy_enabled`/`is_sell_enabled` возвращают `True` (разрешительный default).

### 6.5. OrderService

```python
class OrderService:
    async def create_order(self, session, user_id, order_type, amount_usdt, rate, 
                           payment_link, message_id, chat_id) -> Order
    async def cancel_order(self, session, order_id, user_id) -> Order
    async def complete_order(self, session, order_id, operator_user_id) -> Order
    async def mark_link_broken(self, session, order_id) -> Order
    async def get_active_orders(self, session, offset, limit) -> list[Order]
    async def count_active_orders(self, session) -> int
    async def get_broken_link_orders(self, session) -> list[Order]
    async def get_statistics(self, session, start, end) -> dict
```

- `create_order` — рассчитывает `total_fiat = amount_usdt * rate`, сохраняет зашифрованный `payment_link_snapshot`.
- `cancel_order` — проверяет что `status == created` и `user_id` совпадает (или роль=admin+).
- `complete_order` — меняет статус на `completed`, логирует.
- `get_statistics` — SQL-агрегация: `COUNT`, `SUM` по `order_type`, `WHERE created_at BETWEEN :start AND :end AND status IN ('created', 'completed')`.

### 6.6. NotificationService

```python
class NotificationService:
    async def send_to_all_chats(self, bot, session, text: str) -> list[bool]
    async def notify_new_order(self, bot, session, order: Order) -> None
    async def notify_broken_link(self, bot, session, order: Order, user: User) -> None
    async def notify_order_completed(self, bot, session, order: Order) -> None
    async def notify_role_assigned(self, bot, session, user: User, role: str) -> None
```

- Каждая отправка — ARQ-задача (retry 3 раза, затем лог ошибки).
- Если чат недоступен (Forbidden, BadRequest) — логировать, не удалять чат из БД.

### 6.7. AuditService

```python
class AuditService:
    async def log(self, session, user_id, action, details: dict | None = None) -> AuditLog
```

---

## 7. Middleware

### 7.1. DBSessionMiddleware

- В каждом handler'е доступна `session: AsyncSession` через `data["session"]`.
- Реализация: `BaseMiddleware` на Aiogram 3.x — открывает сессию перед обработкой, коммитит после, откатывает при ошибке.

### 7.2. BotStatusMiddleware

- Проверяет `bot_enabled` в `global_settings` (с кешированием в Redis на 30 сек).
- Если бот отключён и `user.role == client` — перехватывает сообщение, отвечает «Бот временно недоступен» и не пропускает дальше.
- Операторы и админы работают всегда.

### 7.3. RoleGuardMiddleware

- Проверяет, что у пользователя достаточно прав для действия.
- Используется как фильтр на роутерах: `router.message.filter(RoleFilter(min_role=RoleEnum.admin))`.
- Иерархия: `super_admin > admin > operator > client`.

---

## 8. Handlers (детальные сценарии)

### 8.1. /start и регистрация

```
Пользователь → /start
│
├─ Проверить: пользователь есть в БД?
│  ├─ Нет → создать с role=client (или super_admin, если telegram_id == SUPER_ADMIN_TELEGRAM_ID)
│  └─ Да → загрузить
│
└─ Отправить приветствие + меню по роли
```

**Приветственное сообщение:**
```
👋 Добро пожаловать в бот обмена USDT!

Ваш текущий статус: {role}

Выберите действие:
```

### 8.2. Клиент: Покупка USDT

**FSM: `OrderBuyStates`**

```
Состояния:
  waiting_amount    → ожидание ввода суммы
  confirm_order     → подтверждение (автоматический переход после валидации)

Переходы:
  [💰 Купить USDT] → bot_status_middleware проверяет buy_enabled
    ↓ (если отключено) → «Покупка USDT временно приостановлена.»
    ↓ (если включено)
  Установить state = waiting_amount
  Отправить: «Введите сумму в USDT, которую хотите купить.»

  Пользователь вводит сумму →
    Валидация: число > 0, ≤ 100000
    ↓ (ошибка) → «Введите корректную сумму (от 0.01 до 100000 USDT).»
    ↓ (ок)
  Получить текущий курс покупки (rate_type='buy')
    ↓ (курс не установлен) → «Курс покупки не установлен. Обратитесь позже.» + сброс FSM
  Получить payment_link_buy → расшифровать
    ↓ (ссылка не задана) → «Реквизиты не настроены. Обратитесь позже.» + сброс FSM
  Создать Order в БД
  Отправить сообщение с заявкой (сохранить message_id, chat_id в Order)
  Отправить inline-кнопки: [🔗 Ссылка не работает] [❌ Отменить заявку]
  Уведомить чаты через ARQ
  Сбросить FSM
```

**Формат сообщения с заявкой:**
```
📌 Заявка на покупку USDT #{id}

Сумма: {amount} USDT
Курс: {rate} RUB/USDT
К оплате: {total_fiat} RUB

Реквизиты оплаты:
{payment_link}

После оплаты ожидайте подтверждения оператором.
```

### 8.3. Клиент: Продажа USDT

Аналогично покупке, но:
- Проверяется `sell_enabled`
- Курс `rate_type='sell'`
- Реквизиты `payment_link_sell`
- Текст: «Заявка на продажу USDT»
- Клиент должен перевести USDT на указанные реквизиты бота

### 8.4. Клиент: Просмотр курсов

```
[📊 Курсы] →
  Получить текущие курсы (buy, sell)
  Отправить:
  «📊 Актуальные курсы:
  Покупка: {buy_rate} RUB/USDT
  Продажа: {sell_rate} RUB/USDT»
```

Если курс не установлен — показать «Не установлен».

### 8.5. Клиент: Поддержка

**FSM: `SupportStates`**

```
Состояния:
  waiting_message → ожидание сообщения от клиента

Переходы:
  [📞 Поддержка] → state = waiting_message
  Отправить: «Напишите ваш вопрос, и мы ответим в ближайшее время.»

  Пользователь отправляет текст →
    Переслать сообщение в чаты уведомлений:
      «📩 Обращение в поддержку от @{username} (ID: {telegram_id}):
      {message_text}»
    Ответить клиенту: «Ваше сообщение передано в поддержку. Ожидайте ответа.»
    Сбросить FSM
```

> **Расширение:** в будущем вместо пересылки можно отправить ссылку на внешний чат `t.me/support_chat`.

### 8.6. Клиент: Отмена заявки (inline callback)

```
[❌ Отменить заявку] →
  Callback data: "order_cancel:{order_id}"
  Проверить: заказ существует, статус = created, user_id совпадает
  Изменить статус на cancelled
  Редактировать сообщение: «❌ Заявка #{id} отменена.»
```

### 8.7. Клиент: Жалоба на ссылку (inline callback)

```
[🔗 Ссылка не работает] →
  Callback data: "order_broken_link:{order_id}"
  Установить link_broken = True
  Ответить alert: «Мы уже меняем ссылку. Новая ссылка будет отправлена сюда же.»
  Отправить в чаты уведомлений через ARQ:
    «⚠️ Клиент @{username} жалуется на неработающую ссылку в заявке #{id}»
```

### 8.8. Оператор: Активные заявки

```
[📋 Активные заявки] →
  Получить Orders со status='created', за последние 24ч, ORDER BY created_at DESC
  Пагинация: по 5 заявок на страницу
  Кнопки: [◀️ Назад] [Вперёд ▶️] (если есть страницы)
  
  Формат каждого заказа:
  ━━━━━━━━━━━━━━━━━━━━
  Заявка #{id} | 🟢 Покупка
  Клиент: @{username} (ID: {telegram_id})
  Сумма: {amount} USDT
  К оплате: {total_fiat} RUB
  Дата: {created_at:%d.%m.%Y %H:%M}
  ━━━━━━━━━━━━━━━━━━━━

  Inline-кнопки под каждой заявкой:
  [✅ Завершить] [❌ Отменить]
```

### 8.9. Оператор: Завершение заявки

```
[✅ Завершить] →
  Callback data: "order_complete:{order_id}"
  Изменить статус на completed
  Редактировать сообщение оператора: «✅ Заявка #{id} завершена оператором @{operator}.»
  Отправить клиенту:
    «✅ Ваша заявка #{id} на {order_type} {amount} USDT подтверждена!
    К оплате: {total_fiat} RUB
    Оператор: @{operator}
    Спасибо за обращение!»
```

### 8.10. Оператор: Статистика за период

**FSM: `StatisticsStates`**

```
Состояния:
  waiting_start_date → ожидание даты начала
  waiting_end_date   → ожидание даты окончания

Переходы:
  [📈 Статистика] → state = waiting_start_date
  Отправить: «Введите начальную дату (формат: ДД.ММ.ГГГГ):»

  Пользователь вводит дату →
    Валидация: формат DD.MM.YYYY, корректная дата
    ↓ (ошибка) → «Неверный формат даты. Введите в формате ДД.ММ.ГГГГ:»
    Сохранить start_date
  state = waiting_end_date
  Отправить: «Введите конечную дату (формат: ДД.ММ.ГГГГ):»

  Пользователь вводит дату →
    Валидация: формат, end_date >= start_date
    ↓ (ошибка) → «Неверная дата. Конечная дата должна быть >= начальной.»

  Получить статистику из OrderService.get_statistics()
  Отправить:
  «📊 Статистика с {start} по {end}:
  Покупок: {count_buy} на сумму {sum_buy} USDT
  Продаж: {count_sell} на сумму {sum_sell} USDT
  Всего заявок: {total}»
  Сбросить FSM
```

### 8.11. Админ: Смена курса

**FSM: `ChangeRateStates`**

```
Состояния:
  waiting_new_rate → ожидание нового курса

Переходы:
  [🔄 Сменить курс (покупка)] → state = waiting_new_rate
  Текущий курс: {current_rate} RUB/USDT
  Отправить: «Текущий курс покупки: {current_rate} RUB/USDT
  Введите новый курс:»

  Пользователь вводит курс →
    Валидация: число > 0, до 2 знаков после запятой
    ↓ (ошибка) → «Введите корректный курс (положительное число):»
  Сохранить в Rate + audit_log
  Ответить: «Курс покупки изменён на {new_rate} RUB/USDT»
  Сбросить FSM
```

Аналогично для «Сменить курс (продажа)».

### 8.12. Админ: Смена реквизитов

**FSM: `ChangeLinksStates`**

```
Состояния:
  choosing_type    → выбор типа (покупка/продажа)
  waiting_new_link → ввод новых реквизитов

Переходы:
  [🔗 Сменить реквизиты] → state = choosing_type
  Inline-кнопки: [🟢 Покупка] [🔴 Продажа]

  Пользователь выбирает тип →
    Сохранить link_type
  state = waiting_new_link
  Отправить: «Введите новые реквизиты для {покупки|продажи}:»

  Пользователь вводит ссылку →
    Зашифровать и сохранить в global_settings
    Если есть заявки с link_broken=True данного типа →
      Запустить ARQ-задачу: обновить сообщения клиентов (заменить реквизиты, сбросить флаг)
    Ответить: «Реквизиты для {покупки|продажи} обновлены.»
    Сбросить FSM
```

**ARQ-задача `update_broken_links`:**
1. Найти все Orders с `link_broken=True`, `status=created`, `order_type` совпадает.
2. Для каждого: отредактировать сообщение клиента (по `chat_id` + `message_id`), заменив реквизиты.
3. Установить `link_broken=False`.

### 8.13. Админ: Стоп/старт закупа и продажи

```
[⏸ Стоп закуп] →
  Инвертировать buy_enabled в global_settings
  Если стало 0: «🛑 Покупка USDT остановлена.»
  Если стало 1: «✅ Покупка USDT возобновлена.»
  Обновить текст кнопки меню (переключатель)
```

Аналогично для «Стоп продажа».

### 8.14. Админ: Отключить/включить бота

```
[🛑 Отключить бота] →
  Инвертировать bot_enabled
  Если стало 0: «🛑 Бот отключён для клиентов. Администраторы могут продолжать работу.»
  Если стало 1: «✅ Бот включён.»
```

### 8.15. Админ: Чаты уведомлений

```
[➕ Чаты уведомлений] → подменю:
  [📋 Список чатов] → вывести список сохранённых чатов
  [➕ Добавить чат] →
    «Перешлите сообщение из нужного чата или введите Chat ID:»
    Проверить: бот — админ в чате (bot.get_chat_member)
    Сохранить в notification_chats
    «✅ Чат {chat_id} добавлен для уведомлений.»
  [➖ Удалить чат] →
    Показать список inline-кнопками
    Удалить выбранный
```

### 8.16. Админ: Назначение ролей

**FSM: `AssignRoleStates`**

```
Состояния:
  waiting_target_user → ожидание Telegram ID или пересланного контакта

Переходы:
  [👤 Сделать Оператором] → state = waiting_target_user
  Отправить: «Введите Telegram ID пользователя или перешлите его контакт:»

  Пользователь вводит ID →
    Найти User в БД
    ↓ (не найден) → «Пользователь не найден. Он должен сначала запустить бота (/start).»
  Установить role = operator
  Отправить пользователю: «👤 Вы назначены Оператором бота обмена USDT.»
  Ответить админу: «✅ Пользователь @{username} теперь Оператор.»
  + audit_log + уведомление в чаты
```

Аналогично для «👑 Сделать Админом» (только у SuperAdmin).

---

## 9. Фоновые задачи (ARQ)

### 9.1. Worker конфигурация

```python
class WorkerSettings:
    functions = [send_notification, update_broken_links]
    redis_settings = RedisSettings.from_dsn(settings.ARQ_REDIS_URL)
    max_tries = 3
```

### 9.2. Задачи

| Функция | Триггер | Описание |
|---------|---------|----------|
| `send_notification` | Создание заявки, жалоба, роль, завершение | Отправка сообщения во все чаты из `notification_chats`. Retry × 3. |
| `update_broken_links` | Админ меняет ссылку | Найти все Orders с `link_broken=True`, обновить сообщения клиентов. |

---

## 10. Клавиатуры

### 10.1. Reply-клавиатуры

Меню пересоздаётся при каждом ответе, отражая актуальные флаги:
- Если `buy_enabled=False` → кнопка `[🛑 Закуп остановлен]` вместо `[💰 Купить USDT]`
- Если `sell_enabled=False` → кнопка `[🛑 Продажа остановлена]` вместо `[💸 Продать USDT]`
- Аналогично для админских кнопок-переключателей

### 10.2. Inline-клавиатуры

| Клавиатура | Callback-префикс | Использование |
|------------|-------------------|---------------|
| Заявка (клиент) | `order_cancel:{id}`, `order_broken_link:{id}` | Под сообщением с заявкой |
| Заявка (оператор) | `order_complete:{id}`, `order_cancel:{id}` | В списке активных заявок |
| Пагинация | `page:{type}:{offset}` | Список заявок, список чатов |
| Выбор типа ссылки | `link_type:{buy\|sell}` | Смена реквизитов |
| Удаление чата | `chat_del:{id}` | Список чатов для удаления |

---

## 11. Фазы реализации

### Фаза 1: Фундамент (2-3 дня)
1. Инициализация проекта: `pyproject.toml`, `.gitignore`, `.env.example`
2. Docker: `docker-compose.yml`, `Dockerfile`
3. Конфигурация: `app/config.py`
4. База данных: модели SQLAlchemy + `alembic` начальная миграция
5. Шифрование: `EncryptionService`

### Фаза 2: Ядро бота (2-3 дня)
6. Bot instance + Dispatcher: `app/bot.py`, `app/main.py`
7. Middleware: DB-сессия, BotStatus, RoleGuard
8. Регистрация и главное меню: `/start` handler
9. Клавиатуры: все Reply и Inline
10. UserService + репозиторий

### Фаза 3: Клиентские функции (2-3 дня)
11. Покупка USDT (FSM)
12. Продажа USDT (FSM)
13. Просмотр курсов
14. Отмена заявки (inline)
15. Жалоба на ссылку (inline)
16. Поддержка (FSM)

### Фаза 4: Операторские функции (1-2 дня)
17. Активные заявки + пагинация
18. Завершение заявки
19. Статистика за период (FSM)

### Фаза 5: Админские функции (2-3 дня)
20. Смена курсов (FSM)
21. Смена реквизитов (FSM) + ARQ-задача обновления битых ссылок
22. Стоп/старт закупа и продажи
23. Отключение/включение бота
24. Управление чатами уведомлений
25. Назначение ролей (FSM)

### Фаза 6: Уведомления и ARQ (1-2 дня)
26. ARQ worker + Redis
27. Задачи: send_notification, update_broken_links
28. Интеграция с handlers

### Фаза 7: Тестирование и полировка (2-3 дня)
29. Unit-тесты: EncryptionService, UserService, OrderService, RateService
30. Integration-тесты: handlers с mock Bot
31. Ручное тестирование всех сценариев
32. Обработка edge cases, error handling
33. Логирование (structlog или logging)

### Итого: ~12-17 дней

---

## 12. Тестирование

### 12.1. Unit-тесты

| Модуль | Что проверяем |
|--------|--------------|
| `EncryptionService` | encrypt → decrypt roundtrip, пустая строка, длинный текст, неверный ключ |
| `OrderService` | create, cancel, complete, mark_broken, statistics |
| `RateService` | set_rate, get_current_rate, история |
| `SettingsService` | get/set флагов, шифрование ссылок |
| `UserService` | get_or_create, set_role, is_super_admin |

### 12.2. Integration-тесты (handlers)

- Используем `aiogram` tests (mock Bot, mock update)
- Проверяем FSM-переходы, тексты ответов, callback-обработку

### 12.3. Запуск тестов

```bash
# Unit + integration
uv run pytest tests/ -v --cov=app --cov-report=term-missing

# Только unit
uv run pytest tests/test_services/ -v
```

---

## 13. Риски и рекомендации

### Риски

1. **AES-256-CBC и ключ**: при потере `ENCRYPTION_KEY` зашифрованные реквизиты невозможно восстановить. Рекомендуется резервное копирование `.env`.
2. **Telegram API rate limits**: при массовой рассылке обновлений ссылок возможен 429. ARQ retry с backoff решает это.
3. **Отсутствие курса при первом запуске**: если админ не задал курс, клиент увидит «Курс не установлен». Это ожидаемо, но нужно чётко обработать.
4. **Long Polling vs Webhook**: Long Polling проще, но при перезапуске бота есть окно ~30 сек, когда обновления могут быть пропущены. Для MVP это допустимо.

### Рекомендации

1. **Redis-кеш для флагов**: `bot_enabled`, `buy_enabled`, `sell_enabled` кешировать в Redis на 30 сек, чтобы не ходить в PostgreSQL на каждое сообщение.
2. **Структурированное логирование**: использовать `logging` с JSON-форматом для Docker.
3. **Graceful shutdown**: обработка SIGTERM — завершить текущие задачи, закрыть сессии БД.
4. **Healthcheck для bot-контейнера**: простой HTTP-эндпоинт на FastAPI (порт 8080) только для healthcheck, не для webhook. Это опционально — можно обойтись `service_healthy` в docker-compose.
5. **Мониторинг**: в будущем — Prometheus метрики (количество заявок, время ответа).

---

## 14. Порядок запуска (после реализации)

```bash
# 1. Скопировать и заполнить .env
cp .env.example .env
# Отредактировать BOT_TOKEN, ENCRYPTION_KEY, SUPER_ADMIN_TELEGRAM_ID

# 2. Запустить инфраструктуру
docker-compose up -d postgres redis

# 3. Выполнить миграции
uv run alembic upgrade head

# 4. Запустить всё
docker-compose up -d

# 5. Зайти в бот как SuperAdmin, настроить:
#    - Курс покупки
#    - Курс продажи
#    - Реквизиты (ссылки)
#    - Добавить чат уведомлений
#    - Назначить операторов

# 6. Проверить логи
docker-compose logs -f bot
```
