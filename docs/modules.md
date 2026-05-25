# Модули проекта

## Структура

```
app/
├── __init__.py
├── main.py
├── bot.py
├── config.py
├── database/
├── repositories/
├── services/
├── handlers/
├── middlewares/
├── keyboards/
├── fsm/
├── tasks/
└── utils/
```

**Навигация в FSM-потоках:** Все FSM-сценарии теперь поддерживают кнопку «❌ Отмена» — при входе в FSM основное меню заменяется клавиатурой с кнопкой отмены, при выходе (отмена или завершение) — восстанавливается. Обработчик `/start` также сбрасывает любое активное FSM-состояние.

**Календарь дат:** Вместо текстового ввода дат (ДД.ММ.ГГГГ) в статистике используется inline-календарь с навигацией по месяцам и выбором дня нажатием.

---

## app/config.py — Конфигурация (Pydantic Settings)

Единая точка конфигурации приложения. Читает переменные окружения из `.env` и валидирует их.

```python
class Settings(BaseSettings):
    BOT_TOKEN: str                          # Токен Telegram-бота
    DATABASE_URL: str                       # URL подключения к PostgreSQL
    REDIS_URL: str = "redis://localhost:6379/0"  # Redis для кеша
    ENCRYPTION_KEY: str                     # 64-char hex или base64 = 32 байта AES-256
    SUPER_ADMIN_TELEGRAM_ID: int            # Telegram ID SuperAdmin
    ORDERS_PER_PAGE: int = 5               # Заявок на страницу (пагинация)
    ARQ_REDIS_URL: str = "redis://localhost:6379/1"  # Redis для ARQ (DB 1)

    class Config:
        env_file = ".env"
```

**Особенности:**

- Ошибка валидации при старте — немедленный сбой с понятным сообщением
- Значения по умолчанию для Redis URL и пагинации
- Экземпляр `Settings` создаётся один раз (singleton) и используется во всём приложении

---

## app/database/ — База данных

### engine.py — AsyncEngine + AsyncSessionMaker

Создаёт асинхронный движок SQLAlchemy и фабрику сессий:

```python
async_engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
```

**Особенности:**

- `expire_on_commit=False` — объекты доступны после коммита без повторной загрузки
- Пул соединений управляется SQLAlchemy автоматически
- Для тестов: in-memory SQLite с `create_all()`

### base.py — DeclarativeBase

Базовый класс для всех ORM-моделей:

```python
class Base(DeclarativeBase):
    pass
```

### types.py — Кросс-диалектные типы

Пользовательские типы SQLAlchemy для совместимости между PostgreSQL (продакшен) и SQLite (тесты):

- **`JSONBCompat`** — `TypeDecorator`, который рендерится как `JSONB` на PostgreSQL и `JSON` на остальных диалектах. Используется в `AuditLog.details`. На PostgreSQL сохраняет все преимущества `jsonb` (индексация, бинарный формат), а на SQLite позволяет запускать тесты без ошибок компиляции.

### models/ — ORM модели

#### user.py — User

Пользователь бота с ролевой моделью.

| Атрибут | Тип | Описание |
|---------|-----|----------|
| `id` | `SERIAL PK` | Внутренний ID |
| `telegram_id` | `BIGINT UNIQUE` | Telegram ID пользователя |
| `username` | `String(255)` | Telegram username (может быть None) |
| `full_name` | `String(255)` | Полное имя (может быть None) |
| `role` | `Enum(RoleEnum, name="user_role")` | Роль: `super_admin`, `admin`, `operator`, `client` |
| `is_blocked` | `Boolean` | Зарезервировано, default=False |
| `created_at` | `TIMESTAMP` | Дата регистрации |

Связи: `orders` (→ Order), `rates_set` (→ Rate)

#### order.py — Order

Заявка на покупку или продажу USDT.

| Атрибут | Тип | Описание |
|---------|-----|----------|
| `id` | `SERIAL PK` | ID заявки |
| `user_id` | `INT FK → users.id` | Клиент |
| `order_type` | `Enum(OrderTypeEnum, name="order_type")` | `buy` или `sell` |
| `amount_usdt` | `Numeric(18,8)` | Сумма в USDT |
| `rate` | `Numeric(18,2)` | Курс на момент создания |
| `total_fiat` | `Numeric(18,2)` | Сумма в фиате |
| `status` | `Enum(OrderStatusEnum, name="order_status")` | `created`, `cancelled`, `completed` |
| `payment_link_snapshot` | `TEXT` | Зашифрованные реквизиты на момент создания |
| `link_broken` | `Boolean` | Флаг жалобы на ссылку |
| `message_id` | `INT` | ID сообщения с заявкой в чате клиента |
| `chat_id` | `BIGINT` | Chat ID клиента |
| `created_at` | `TIMESTAMP` | Дата создания |
| `updated_at` | `TIMESTAMP` | Дата обновления |

Индексы: `(user_id)`, `(status, created_at)`, `(order_type, created_at)`

#### rate.py — Rate

История изменений курсов. Каждое изменение — новая запись.

| Атрибут | Тип | Описание |
|---------|-----|----------|
| `id` | `SERIAL PK` | ID записи |
| `rate_type` | `Enum(RateTypeEnum, name="rate_type")` | `buy` или `sell` |
| `value` | `Numeric(18,2)` | Значение курса (RUB/USDT) |
| `set_by` | `INT FK → users.id` | Админ, установивший курс |
| `created_at` | `TIMESTAMP` | Дата установки |

#### global_settings.py — GlobalSettings

Хранилище ключ-значение для глобальных настроек.

| Атрибут | Тип | Описание |
|---------|-----|----------|
| `key` | `String(255) PK` | Ключ настройки |
| `value` | `TEXT` | Значение (может быть зашифровано) |

Ключи: `bot_enabled`, `buy_enabled`, `sell_enabled`, `payment_link_buy`, `payment_link_sell`

#### notification_chat.py — NotificationChat

Чаты/каналы для получения уведомлений.

| Атрибут | Тип | Описание |
|---------|-----|----------|
| `id` | `SERIAL PK` | ID записи |
| `chat_id` | `BIGINT UNIQUE` | Telegram Chat ID |
| `added_by` | `INT FK → users.id` | Админ, добавивший чат |
| `created_at` | `TIMESTAMP` | Дата добавления |

#### audit_log.py — AuditLog

Аудит-лог действий администраторов.

| Атрибут | Тип | Описание |
|---------|-----|----------|
| `id` | `SERIAL PK` | ID записи |
| `user_id` | `INT FK → users.id` | Кто совершил действие |
| `action` | `String(255)` | Тип действия (например, `change_rate_buy`) |
| `details` | `JSONBCompat` | Детали изменения (JSONB на PostgreSQL, JSON на SQLite) |
| `created_at` | `TIMESTAMP` | Дата действия |

---

## app/repositories/ — Репозитории

### base.py — Базовый репозиторий (Generic CRUD)

Предоставляет стандартные операции для всех моделей:

- `get_by_id(session, id)` — получить по первичному ключу
- `get_all(session, offset, limit)` — список с пагинацией
- `create(session, **kwargs)` — создать запись
- `update(session, id, **kwargs)` — обновить запись
- `delete(session, id)` — удалить запись

### user_repo.py — UserRepository

Специфичные методы:

- `get_by_telegram_id(session, telegram_id)` — поиск по Telegram ID
- `exists_by_telegram_id(session, telegram_id)` — проверка существования

### order_repo.py — OrderRepository

Специфичные методы:

- `get_active_orders(session, offset, limit)` — заявки со статусом `created` за последние 24 часа
- `count_active_orders(session)` — количество активных заявок
- `get_broken_link_orders(session, order_type)` — заявки с битой ссылкой указанного типа
- `get_statistics(session, start, end)` — агрегация (COUNT, SUM) по дипазону дат

### rate_repo.py — RateRepository

Специфичные методы:

- `get_current_rate(session, rate_type)` — последняя запись с данным `rate_type`, `ORDER BY created_at DESC, id DESC`
- `get_rate_history(session, rate_type, limit)` — история изменений курса, `ORDER BY created_at DESC, id DESC`

### settings_repo.py — SettingsRepository

Специфичные методы:

- `get(session, key)` — получить значение по ключу
- `set(session, key, value)` — установить значение

### notification_repo.py — NotificationRepository

Специфичные методы:

- `get_all_chat_ids(session)` — список всех Chat ID для рассылки

### audit_repo.py — AuditRepository

Специфичные методы:

- `log(session, user_id, action, details)` — записать действие в аудит-лог

---

## app/services/ — Сервисы (бизнес-логика)

### encryption.py — EncryptionService

AES-256-CBC шифрование/дешифрование реквизитов.

```python
class EncryptionService:
    def __init__(self, key_hex: str): ...  # 64-char hex или base64 → 32 байта
    def encrypt(self, plaintext: str) -> str: ...  # → hex (IV + ciphertext)
    def decrypt(self, cipher_hex: str) -> str: ...  # ← hex → plaintext
```

- Ключ принимается в формате: 64 hex-символа, стандартный base64 или URL-safe base64 (с `-` и `_`). Декодированный ключ должен быть ровно 32 байта (AES-256).
- IV — случайные 16 байт, записываются перед ciphertext
- Результат — hex-строка для хранения в TEXT-поле БД
- Используется библиотека `cryptography` (`Cipher`, `algorithms`, `modes`, `padding`)

### user_service.py — UserService

Управление пользователями и ролями.

| Метод | Описание |
|-------|----------|
| `get_or_create(session, telegram_id, username, full_name)` | Создать пользователя или вернуть существующего. Если `telegram_id == SUPER_ADMIN_TELEGRAM_ID` → роль `super_admin`, иначе `client` |
| `get_by_telegram_id(session, telegram_id)` | Найти пользователя по Telegram ID |
| `set_role(session, user_id, role, set_by_user_id)` | Установить роль + запись в `audit_logs` |
| `is_super_admin(session, telegram_id)` | Проверка, является ли пользователь SuperAdmin |

### order_service.py — OrderService

Управление заявками.

| Метод | Описание |
|-------|----------|
| `create_order(session, user_id, order_type, amount_usdt, rate, payment_link, message_id, chat_id)` | Создать заявку. Рассчитывает `total_fiat = amount_usdt * rate`, сохраняет зашифрованный `payment_link_snapshot` |
| `cancel_order(session, order_id, user_id)` | Отменить заявку. Проверяет: `status == created`, `user_id` совпадает (или роль=admin+) |
| `complete_order(session, order_id, operator_user_id)` | Завершить заявку. Меняет статус на `completed`, логирует |
| `mark_link_broken(session, order_id)` | Установить флаг `link_broken = True` |
| `get_active_orders(session, offset, limit)` | Активные заявки с пагинацией |
| `count_active_orders(session)` | Количество активных заявок |
| `get_broken_link_orders(session)` | Заявки с битой ссылкой |
| `get_statistics(session, start, end)` | Агрегация: COUNT, SUM по `order_type` за период |

### rate_service.py — RateService

Управление курсами.

| Метод | Описание |
|-------|----------|
| `get_current_rate(session, rate_type)` | Текущий курс. Последняя запись в `rates` с данным `rate_type`, `ORDER BY created_at DESC`. Возвращает `None`, если записей нет |
| `set_rate(session, rate_type, value, set_by_user_id)` | Установить курс + запись в `audit_logs` |
| `get_rate_history(session, rate_type, limit=10)` | История изменений курса |

### settings_service.py — SettingsService

Управление глобальными настройками и флагами.

| Метод | Описание |
|-------|----------|
| `get(session, key)` | Получить значение по ключу |
| `set(session, key, value, user_id)` | Установить значение |
| `is_bot_enabled(session)` | Проверка `bot_enabled`. Default: `True` (если ключ отсутствует) |
| `is_buy_enabled(session)` | Проверка `buy_enabled`. Default: `True` |
| `is_sell_enabled(session)` | Проверка `sell_enabled`. Default: `True` |
| `get_payment_link(session, order_type)` | Расшифровать и вернуть `payment_link_buy` или `payment_link_sell` |
| `set_payment_link(session, order_type, link, user_id)` | Зашифровать и сохранить ссылку |

### notification_service.py — NotificationService

Отправка уведомлений в чаты через ARQ.

| Метод | Описание |
|-------|----------|
| `send_to_all_chats(bot, session, text)` | Отправить текст во все чаты из `notification_chats`. Каждая отправка — ARQ-задача с retry |
| `notify_new_order(bot, session, order)` | Уведомление о новой заявке |
| `notify_broken_link(bot, session, order, user)` | Уведомление о жалобе на ссылку |
| `notify_order_completed(bot, session, order)` | Уведомление о завершении заявки |
| `notify_role_assigned(bot, session, user, role)` | Уведомление о назначении роли |

### audit_service.py — AuditService

Логирование действий администраторов.

| Метод | Описание |
|-------|----------|
| `log(session, user_id, action, details=None)` | Записать действие в `audit_logs` |

---

## app/handlers/ — Обработчики

### start.py — /start и регистрация

- Команда `/start` — проверка/создание пользователя, определение роли
- Если пользователя нет → создать с `role=client` (или `super_admin` при совпадении с `SUPER_ADMIN_TELEGRAM_ID`)
- Отправка приветственного сообщения и меню по роли

### client/ — Клиентские обработчики

#### buy.py — Покупка USDT

FSM `OrderBuyStates` (`waiting_amount`, `confirm_order`):
1. Проверка `buy_enabled` (через BotStatus middleware)
2. Ввод суммы USDT (валидация: 0.01–100000)
3. Получение текущего курса покупки
4. Получение и расшифровка реквизитов
5. Создание заявки в БД
6. Отправка сообщения с заявкой + inline-кнопки
7. Уведомление в чаты через ARQ

#### sell.py — Продажа USDT

FSM `OrderSellStates` (`waiting_amount`, `confirm_order`):
- Аналогично покупке, но проверяется `sell_enabled`, курс `rate_type='sell'`, реквизиты `payment_link_sell`

#### rates.py — Просмотр курсов

- Получение текущих курсов (buy, sell)
- Отображение: «Покупка: X RUB/USDT, Продажа: Y RUB/USDT»
- Если курс не установлен — «Не установлен»

#### support.py — Поддержка

FSM `SupportStates` (`waiting_message`):
1. Клиент нажимает «📞 Поддержка»
2. Вводит текст обращения
3. Сообщение пересылается в чаты уведомлений
4. Клиенту: «Ваше сообщение передано в поддержку.»

#### cancel_order.py — Отмена заявки

- Inline callback `order_cancel:{order_id}`
- Проверка: заказ существует, статус `created`, `user_id` совпадает
- Изменение статуса на `cancelled`
- Редактирование сообщения: «❌ Заявка #{id} отменена.»

### operator/ — Обработчики оператора

#### active_orders.py — Активные заявки

- Вывод списка Orders со `status='created'` за последние 24 часа
- Пагинация: по 5 заявок на страницу
- Inline-кнопки под каждой заявкой: [✅ Завершить] [❌ Отменить]

#### complete_order.py — Завершение заявки

- Inline callback `order_complete:{order_id}`
- Изменение статуса на `completed`
- Уведомление клиента: «✅ Ваша заявка #{id} подтверждена!»
- Уведомление в чаты через ARQ

#### statistics.py — Статистика за период

FSM `StatisticsStates` (`waiting_start_date`, `waiting_end_date`):
1. Показ inline-календаря для выбора начальной даты + кнопка «❌ Отмена»
2. Выбор начальной даты → показ нового календаря для конечной даты
3. Выбор конечной даты (валидация: end >= start)
4. Агрегация из `OrderService.get_statistics()`
5. Вывод: покупок, продаж, всего заявок
6. Восстановление основного меню по роли пользователя

### admin/ — Обработчики администратора

#### change_rate.py — Смена курса

FSM `ChangeRateStates` (`waiting_new_rate`):
1. Показ текущего курса
2. Ввод нового курса (валидация: число > 0)
3. Сохранение в `Rate` + `audit_log`
4. Ответ: «Курс покупки/продажи изменён на X RUB/USDT»

#### change_links.py — Смена реквизитов

FSM `ChangeLinksStates` (`choosing_type`, `waiting_new_link`):
1. Выбор типа: покупка/продажа (inline-кнопки)
2. Ввод новых реквизитов
3. Шифрование и сохранение в `global_settings`
4. Если есть заявки с `link_broken=True` → ARQ-задача `update_broken_links`
5. Ответ: «Реквизиты для покупки/продажи обновлены.»

#### toggle_flags.py — Управление флагами

- **Стоп/старт закупа** — инвертирует `buy_enabled`. Если 0: «Покупка USDT остановлена», если 1: «Покупка USDT возобновлена»
- **Стоп/старт продажи** — инвертирует `sell_enabled`
- **Отключить/включить бота** — инвертирует `bot_enabled`. Клиенты видят «Бот временно недоступен»

#### notification_chats.py — Управление чатами уведомлений

Подменю: [📋 Список чатов] [➕ Добавить чат] [➖ Удалить чат]
- Добавление: переслать сообщение из чата или ввести Chat ID. Бот проверяет, что он админ в чате
- Удаление: inline-список чатов, удаление по клику

#### assign_roles.py — Назначение ролей

FSM `AssignRoleStates` (`waiting_target_user`):
1. Ввод Telegram ID или пересылка контакта
2. Поиск пользователя в БД (должен запустить бота первым)
3. Установка роли (`operator` или `admin`)
4. Уведомление пользователя и чатов

### common/ — Общие обработчики

#### broken_link.py — Жалоба на неработающую ссылку

- Inline callback `order_broken_link:{order_id}`
- Установка `link_broken = True`
- Alert-ответ: «Мы уже меняем ссылку. Новая ссылка будет отправлена сюда же.»
- Уведомление в чаты через ARQ

#### cancel.py — Глобальный обработчик отмены FSM

- Ловит текст «❌ Отмена» во **всех** FSM-состояниях
- Сбрасывает FSM-состояние (`state.clear()`)
- Восстанавливает основное меню по роли пользователя (client/operator/admin)
- Если пользователь не в FSM — отвечает «Нет активного действия для отмены.»
- Если `user is None` — использует роль `client` по умолчанию для восстановления меню
- Зарегистрирован **перед** остальными роутерами в `bot.py`, чтобы иметь приоритет

#### calendar.py — Обработчик inline-календаря для выбора дат

- Обрабатывает callback-данные календаря:
  - `cal:ignore` — пустой клик (заголовки, плейсхолдеры)
  - `cal:nav:prev/next:{year}:{month}` — навигация по месяцам
  - `cal:pick:{year}:{month}:{day}` — выбор дня
- Работает в связке с `StatisticsStates` (стартовая и конечная дата)
- При выборе стартовой даты — сохраняет в FSM data, переводит в `waiting_end_date`
- При выборе конечной даты — валидирует (end ≥ start), загружает статистику, восстанавливает меню

---

## app/middlewares/ — Промежуточные слои

### db_session.py — DBSessionMiddleware

Инъекция `AsyncSession` в handler data:
- Открывает сессию перед обработкой: `data["session"] = async_session_maker()`
- Коммитит после успешной обработки
- Откатывает при исключении
- Закрывает сессию в `finally`

### bot_status.py — BotStatusMiddleware

Проверка статуса бота:
- Читает `bot_enabled` из Redis-кеша (TTL 30 сек), при отсутствии — из БД
- Если `bot_enabled == "0"` и `user.role == client` → перехватывает сообщение, отвечает «Бот временно недоступен»
- Операторы и админы работают всегда

### role_guard.py — RoleGuardMiddleware

Проверка прав роли:
- Используется как фильтр на роутерах: `router.message.filter(RoleFilter(min_role=RoleEnum.admin))`
- Иерархия: `super_admin > admin > operator > client`
- Если роль недостаточна → сообщение «У вас нет прав для этого действия»

---

## app/keyboards/ — Клавиатуры

### client_kb.py — ReplyKeyboardMarkup для клиента

```
[💰 Купить USDT] [💸 Продать USDT]
[📊 Курсы]        [📞 Поддержка]
```

Динамическое отображение: если `buy_enabled=False` → кнопка `[🛑 Закуп остановлен]`

### operator_kb.py — ReplyKeyboardMarkup для оператора

```
[📋 Активные заявки] [📊 Курсы]
[📈 Статистика]
```

### admin_kb.py — ReplyKeyboardMarkup для админа/SuperAdmin

```
[📋 Активные заявки] [📈 Статистика] [📊 Курсы]
[🔄 Сменить курс (покупка)] [🔄 Сменить курс (продажа)]
[🔗 Сменить реквизиты]
[⏸ Стоп закуп] [⏸ Стоп продажа]
[🛑 Отключить бота]
[➕ Чаты уведомлений]
[👤 Сделать Оператором]
[👑 Сделать Админом]  ← только SuperAdmin
```

Кнопки-переключатели меняют текст: «Стоп закуп» ↔ «Старт закуп»

### cancel_kb.py — Клавиатура отмены и восстановление меню

| Функция | Описание |
|---------|----------|
| `cancel_keyboard()` | ReplyKeyboardMarkup с единственной кнопкой `[❌ Отмена]`. Показывается при входе в FSM вместо основного меню. |
| `get_main_keyboard(role, ...)` | Возвращает основное меню по роли пользователя. Используется для восстановления после отмены или завершения FSM. |

Константа `CANCEL_BUTTON_TEXT = "❌ Отмена"` — единый текст кнопки отмены для всех FSM-потоков.

### calendar_kb.py — Inline-календарь для выбора дат

| Функция | Описание |
|---------|----------|
| `calendar_kb(year, month, prefix)` | Строит InlineKeyboardMarkup с сеткой дней месяца. Навигация ◀️/▶️, дни — кнопки. Поддерживает `prefix` для различения календарей. |

Callback-данные:
- `{prefix}:nav:prev:{year}:{month}` / `{prefix}:nav:next:{year}:{month}` — навигация
- `{prefix}:pick:{year}:{month}:{day}` — выбор дня
- `{prefix}:ignore` — пустая кнопка (заголовки, выравнивание)

Русские названия месяцев и дней недели (Пн–Вс, понедельник первый).

### inline_kb.py — InlineKeyboardMarkup

| Клавиатура | Callback-префикс | Использование |
|-----------|-------------------|---------------|
| Заявка клиента | `order_cancel:{id}`, `order_broken_link:{id}` | Под сообщением с заявкой |
| Заявка оператора | `order_complete:{id}`, `order_cancel:{id}` | В списке активных заявок |
| Пагинация | `page:{type}:{offset}` | Список заявок, список чатов |
| Выбор типа ссылки | `link_type:{buy\|sell}` | Смена реквизитов |
| Удаление чата | `chat_del:{id}` | Список чатов для удаления |
| Подменю чатов уведомлений | `notif_list`, `notif_add`, `notif_delete`, `notif_back` | Управление чатами + кнопка «🔙 Назад» |

---

## app/fsm/ — FSM-состояния

### order_states.py — OrderBuyStates, OrderSellStates

```
OrderBuyStates:
  waiting_amount  → ожидание ввода суммы покупки
  confirm_order   → подтверждение заявки на покупку

OrderSellStates:
  waiting_amount  → ожидание ввода суммы продажи
  confirm_order   → подтверждение заявки на продажу
```

### statistics_states.py — StatisticsStates

```
StatisticsStates:
  waiting_start_date → ожидание выбора начальной даты (inline-календарь)
  waiting_end_date   → ожидание выбора конечной даты (inline-календарь)
```

Ввод дат осуществляется через inline-календарь (`calendar_kb.py` + `handlers/common/calendar.py`), а не через текстовый ввод.

### rate_states.py — ChangeRateStates

```
ChangeRateStates:
  waiting_new_rate → ожидание нового курса (положительное число)
```

### links_states.py — ChangeLinksStates

```
ChangeLinksStates:
  choosing_type    → выбор типа ссылки (покупка/продажа)
  waiting_new_link → ввод новых реквизитов
```

### role_states.py — AssignRoleStates

```
AssignRoleStates:
  waiting_target_user → ожидание Telegram ID или пересланного контакта
```

### support_states.py — SupportStates

```
SupportStates:
  waiting_message → ожидание сообщения клиента для поддержки
```

---

## app/tasks/ — Фоновые задачи (ARQ)

### worker.py — ARQ Worker конфигурация

```python
from arq.connections import RedisSettings

class WorkerSettings:
    functions = [send_notification, update_broken_links]
    redis_settings = RedisSettings.from_dsn(settings.ARQ_REDIS_URL)
    max_tries = 3
```

**Важно:** `RedisSettings` импортируется из `arq.connections`, а не из `arq` напрямую (изменено в ARQ 0.26.x).

Запуск: `uv run arq app.tasks.worker.WorkerSettings`

### jobs.py — Фоновые задачи

| Функция | Триггер | Описание |
|---------|---------|----------|
| `send_notification(chat_id, text)` | Создание заявки, жалоба на ссылку, назначение роли, завершение заявки | Отправка сообщения в указанный чат. Retry × 3 при ошибке Telegram API |
| `update_broken_links(order_type, new_link)` | Админ меняет реквизиты | Найти все Orders с `link_broken=True`, `status=created`, `order_type` совпадает. Для каждого: отредактировать сообщение клиента (по `chat_id` + `message_id`), заменить реквизиты, установить `link_broken=False` |
