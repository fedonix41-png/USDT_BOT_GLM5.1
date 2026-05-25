# Структура проекта

```
app/
├── config.py           # Pydantic Settings — все переменные окружения
├── bot.py              # Dispatcher, роутеры, middleware registration
├── main.py             # Entry point — запуск Long Polling
│
├── database/
│   ├── engine.py       # AsyncEngine, AsyncSessionMaker
│   ├── base.py         # DeclarativeBase
│   ├── types.py        # JSONBCompat (PostgreSQL JSONB / SQLite JSON)
│   └── models/         # ORM модели
│       ├── user.py, order.py, rate.py
│       ├── global_settings.py
│       ├── notification_chat.py, audit_log.py
│
├── repositories/       # Слой доступа к данным
│   ├── base.py         # Generic CRUD (get_by_id, get_all, create, update, delete)
│   ├── user_repo.py    # get_by_telegram_id, exists_by_telegram_id
│   ├── order_repo.py   # get_active_orders, get_statistics, get_broken_link_orders
│   ├── rate_repo.py    # get_current_rate, get_rate_history
│   ├── settings_repo.py # get/set по ключу
│   ├── notification_repo.py # get_all_chat_ids
│   └── audit_repo.py   # log
│
├── services/           # Бизнес-логика
│   ├── encryption.py   # AES-256-CBC шифрование (encrypt/decrypt)
│   ├── user_service.py # get_or_create, set_role, is_super_admin
│   ├── order_service.py # create_order, cancel_order, complete_order, get_statistics
│   ├── rate_service.py # get_current_rate, set_rate
│   ├── settings_service.py # is_bot_enabled, get_payment_link, set_payment_link
│   ├── notification_service.py # send_to_all_chats, notify_*
│   └── audit_service.py # log
│
├── handlers/           # Aiogram handlers
│   ├── start.py        # /start — регистрация, меню по роли
│   ├── client/         # buy.py, sell.py, rates.py, cancel_order.py, support.py
│   ├── operator/       # active_orders.py, complete_order.py, statistics.py
│   ├── admin/          # change_rate.py, change_links.py, toggle_flags.py,
│   │                   # notification_chats.py, assign_roles.py
│   └── common/         # broken_link.py, cancel.py (глобальная отмена FSM), calendar.py
│
├── middlewares/
│   ├── db_session.py       # Инъекция AsyncSession в data["session"]
│   ├── user_middleware.py  # Загрузка user в data["user"]
│   ├── bot_status.py       # Проверка bot_enabled (кеш 30 сек)
│   └── role_guard.py       # RoleFilter — проверка min_role
│
├── keyboards/
│   ├── client_kb.py    # ReplyKeyboard для клиента
│   ├── operator_kb.py  # ReplyKeyboard для оператора
│   ├── admin_kb.py     # ReplyKeyboard + inline-панель управления
│   ├── cancel_kb.py    # Клавиатура отмены + get_main_keyboard()
│   ├── calendar_kb.py  # Inline-календарь для выбора дат
│   └── inline_kb.py    # Inline-клавиатуры (пагинация, заявки, чаты)
│
├── fsm/                # FSM-состояния
│   ├── order_states.py     # OrderBuyStates, OrderSellStates
│   ├── statistics_states.py # StatisticsStates (waiting_start_date, waiting_end_date)
│   ├── rate_states.py      # ChangeRateStates
│   ├── links_states.py     # ChangeLinksStates
│   ├── role_states.py      # AssignRoleStates
│   └── support_states.py   # SupportStates
│
├── tasks/              # ARQ фоновые задачи
│   ├── worker.py       # WorkerSettings, RedisSettings
│   └── jobs.py         # send_notification, update_broken_links
│
└── utils/
    ├── formatting.py   # HTML-экранирование для Telegram
    ├── pagination.py   # Утилиты пагинации
    └── helpers.py      # get_settings_flags
```

---

## Слои и зависимости

```
handlers/ → services/ → repositories/ → models/
    │           │
    └───────────┴──→ middlewares/ (предварительная обработка)
    │
    └──→ keyboards/ (UI)
    │
    └──→ fsm/ (состояния)
    │
    └──→ tasks/ (ARQ jobs)
```

**Поток данных:**
1. Handler получает update от aiogram
2. Middleware: DBSession → User → BotStatus → RoleGuard
3. Handler вызывает Service (бизнес-логика)
4. Service вызывает Repository (данные)
5. Repository работает с Model (ORM)
6. Handler отправляет ответ через Bot API или ставит ARQ-задачу

---

## Middleware: порядок выполнения

```
Request → DBSessionMiddleware (outermost)
        → UserMiddleware
        → BotStatusMiddleware
        → RoleGuardMiddleware (innermost)
        → Handler
```

**Важно:** DBSessionMiddleware должен быть первым (outermost), чтобы все последующие middleware имели доступ к `session`.

---

## FSM-сценарии

| FSM | States | Назначение |
|-----|--------|------------|
| OrderBuyStates | waiting_amount, confirm_order | Покупка USDT |
| OrderSellStates | waiting_amount, confirm_order | Продажа USDT |
| StatisticsStates | waiting_start_date, waiting_end_date | Статистика за период |
| ChangeRateStates | waiting_new_rate | Смена курса |
| ChangeLinksStates | choosing_type, waiting_new_link | Смена реквизитов |
| AssignRoleStates | waiting_target_user | Назначение роли |
| SupportStates | waiting_message | Обращение в поддержку |

**Навигация:** Все FSM поддерживают кнопку «❌ Отмена» — при выходе восстанавливается основное меню по роли.

**Ввод дат:** Через inline-календарь (calendar_kb.py + handlers/common/calendar.py), не через текст.

---

## ARQ-задачи

| Задача | Триггер | Действие |
|--------|---------|----------|
| send_notification | Создание заявки, жалоба, назначение роли, завершение | Отправка сообщения в чат (max_tries=3) |
| update_broken_links | Смена реквизитов админом | Редактирование сообщений клиентов с битой ссылкой |

---

## Ключевые конфигурации

### config.py (Settings)

```python
BOT_TOKEN: str
DATABASE_URL: str
REDIS_URL: str = "redis://localhost:6379/0"
ENCRYPTION_KEY: str  # 64-char hex = 32 bytes AES-256
SUPER_ADMIN_TELEGRAM_ID: int
ORDERS_PER_PAGE: int = 5
ARQ_REDIS_URL: str = "redis://localhost:6379/1"
```

### global_settings (ключи)

| Ключ | Значение | Назначение |
|------|----------|------------|
| bot_enabled | "1"/"0" | Глобальное включение бота |
| buy_enabled | "1"/"0" | Разрешена покупка |
| sell_enabled | "1"/"0" | Разрешена продажа |
| payment_link_buy | hex (зашифровано) | Реквизиты для покупки |
| payment_link_sell | hex (зашифровано) | Реквизиты для продажи |

---

## Enum-типы (PostgreSQL)

При объявлении `Enum()` в SQLAlchemy **всегда указывать `name=`** явно:

```python
# Правильно:
role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum, name="user_role"), ...)

# Неправильно (сгенерирует "roleenum"):
role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum), ...)
```

Имена: `user_role`, `order_type`, `order_status`, `rate_type`
