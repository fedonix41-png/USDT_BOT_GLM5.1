# API Endpoints Mapping

> **Цель:** Детальное сопоставление API endpoints между TelePay Mini App и текущим USDT_BOT проектом

---

## Легенда статусов

- ✅ **Совместим** — endpoint существует и полностью совместим
- ⚠️ **Требует адаптации** — endpoint существует, но требует изменений
- ❌ **Отсутствует** — endpoint нужно создать с нуля
- 🔄 **Частично** — часть функционала реализована

---

## 1. Аутентификация

### POST /api/v1/auth/telegram/verify

**TelePay:**
```typescript
Request: {
  initData: string;        // Telegram WebApp initData
  requestedRole?: string;  // Для dev режима
}

Response: {
  success: boolean;
  token: string;
  user: UserProfile;
}
```

**USDT_BOT:** ❌ Отсутствует

**Требуется создать:**
- Роутер: `app/api/routers/auth.py`
- Функция: `verify_telegram_webapp()`
- Валидация `initData` через Bot API
- Генерация JWT токена
- Возврат user profile

**Приоритет:** 🔴 Критический

---

### POST /api/v1/auth/login

**USDT_BOT:** ✅ Существует

```python
Request: {
  telegram_id: int;
  password: str;  # Опционально
}

Response: {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
}
```

**Действие:** Оставить как есть для альтернативной аутентификации

---

## 2. Профиль пользователя

### GET /api/v1/user/profile

**TelePay:**
```typescript
Response: UserProfile {
  id: number;
  username: string;
  role: "client" | "operator" | "admin" | "super_admin";
  balance: number;           // USDT баланс
  fiatBalance: number;       // RUB баланс
  status: "active" | "frozen";
  referredBy?: string;
  referralsCount: number;
  referralEarned: number;
}
```

**USDT_BOT:** ❌ Отсутствует

**Требуется создать:**
- Endpoint: `GET /api/v1/user/profile`
- Роутер: `app/api/routers/users.py` (расширить)
- Схема: `app/api/schemas/user.py` → `UserProfileResponse`

**Изменения в БД:**
```sql
ALTER TABLE users ADD COLUMN referred_by VARCHAR(255);
ALTER TABLE users ADD COLUMN referrals_count INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN referral_earned DECIMAL(10,2) DEFAULT 0;
ALTER TABLE users ADD COLUMN fiat_balance DECIMAL(10,2) DEFAULT 0;
```

**Приоритет:** 🔴 Высокий

---

## 3. Настройки системы

### GET /api/v1/exchange/settings

**TelePay:**
```typescript
Response: SystemSettings {
  buyRate: number;           // 94.50
  sellRate: number;          // 92.30
  buyEnabled: boolean;
  sellEnabled: boolean;
  botEnabled: boolean;
  requisitesCard: string;    // Реквизиты карты
  requisitesWallet: string;  // USDT кошелёк
  notificationChats: string[];
}
```

**USDT_BOT:** 🔄 Частично реализован

**Существующий endpoint:**
```python
GET /api/v1/rates
Response: {
  buy: float;
  sell: float;
}
```

**Требуется расширить:**
- Добавить в response: `buyEnabled`, `sellEnabled`, `botEnabled`
- Добавить `requisitesCard`, `requisitesWallet` (расшифрованные)
- Добавить `notificationChats`

**Альтернатива:** Создать новый endpoint `GET /api/v1/settings/full`

**Приоритет:** 🔴 Высокий

---

### POST /api/v1/exchange/settings

**TelePay:**
```typescript
Request: {
  buyRate?: number;
  sellRate?: number;
  buyEnabled?: boolean;
  sellEnabled?: boolean;
  botEnabled?: boolean;
  requisitesCard?: string;
  requisitesWallet?: string;
  notificationChats?: string[];
}

Response: {
  success: boolean;
  settings: SystemSettings;
}
```

**USDT_BOT:** ⚠️ Частично реализован

**Существующий endpoint:**
```python
PATCH /api/v1/settings
Request: {
  key: string;
  value: string;
}
```

**Требуется:**
- Создать `POST /api/v1/settings/bulk` для массового обновления
- Или адаптировать frontend для множественных PATCH запросов

**Приоритет:** 🟡 Средний

---

## 4. Заявки обмена

### GET /api/v1/exchange/orders

**TelePay:**
```typescript
Response: ExchangeOrder[] {
  id: string;              // "EX-1002"
  username: string;
  userId: number;
  type: "buy" | "sell";
  amountUsdt: number;
  amountRub: number;
  rate: number;
  clientDetails: string;   // Адрес кошелька или карта
  requisitesSelected: string;
  status: "pending" | "completed" | "rejected";
  timestamp: string;
  rejectionReason?: string;
  complained?: boolean;
}
```

**USDT_BOT:** ⚠️ Требует адаптации

**Существующий endpoint:**
```python
GET /api/v1/orders
Response: OrderListResponse {
  orders: Order[];
  total: int;
  page: int;
  per_page: int;
}
```

**Различия:**
- USDT_BOT использует пагинацию
- Отсутствуют поля: `clientDetails`, `requisitesSelected`, `complained`
- Формат ID: integer vs string "EX-1002"

**Требуется:**
- Добавить поля в модель `Order`
- Добавить query параметр `?no_pagination=true` для получения всех заявок
- Или создать отдельный endpoint `GET /api/v1/orders/all`

**Приоритет:** 🔴 Высокий

---

### POST /api/v1/exchange/orders

**TelePay:**
```typescript
Request: {
  type: "buy" | "sell";
  amountUsdt: number;
  amountRub: number;
  clientDetails: string;
}

Response: {
  success: boolean;
  order: ExchangeOrder;
  user: UserProfile;  // Обновлённый баланс
}
```

**USDT_BOT:** ⚠️ Требует адаптации

**Существующий endpoint:**
```python
POST /api/v1/orders
Request: {
  order_type: "buy" | "sell";
  amount: float;
  # Другие поля через FSM в боте
}
```

**Требуется:**
- Добавить поле `client_details` в request
- Возвращать обновлённый user profile
- Автоматически выбирать `requisites_selected` из настроек

**Приоритет:** 🔴 Высокий

---

### POST /api/v1/exchange/orders/complain

**TelePay:**
```typescript
Request: {
  orderId: string;
}

Response: {
  success: boolean;
  order: ExchangeOrder;
}
```

**USDT_BOT:** ❌ Отсутствует

**Требуется создать:**
- Endpoint: `POST /api/v1/orders/{order_id}/complain`
- Установить флаг `complained = True`
- Отправить уведомление операторам через ARQ

**Приоритет:** 🟡 Средний

---

### POST /api/v1/exchange/orders/cancel

**TelePay:**
```typescript
Request: {
  orderId: string;
}

Response: {
  success: boolean;
  order: ExchangeOrder;
  user: UserProfile;  // Возврат баланса при sell
}
```

**USDT_BOT:** ❌ Отсутствует

**Требуется создать:**
- Endpoint: `POST /api/v1/orders/{order_id}/cancel`
- Проверка: только pending заявки
- Проверка: только владелец заявки
- Возврат USDT при type=sell
- Обновление статуса на rejected

**Приоритет:** 🟡 Средний

---

## 5. Администрирование

### GET /api/v1/admin/stats

**TelePay:**
```typescript
Response: {
  totalUsers: number;
  pendingCount: number;
  totalVolumeRub: number;
  totalVolumeUsdt: number;
  systemHealthy: boolean;
}
```

**USDT_BOT:** 🔄 Частично реализован

**Существующий endpoint:**
```python
GET /api/v1/statistics
Response: {
  total_orders: int;
  completed_orders: int;
  pending_orders: int;
  total_volume: float;
  # Статистика за период
}
```

**Требуется:**
- Добавить `total_users`
- Разделить `total_volume` на RUB и USDT
- Добавить `system_healthy` (проверка БД, Redis)

**Приоритет:** 🟡 Средний

---

### GET /api/v1/admin/users

**TelePay:**
```typescript
Query: {
  search?: string;  // Поиск по username или ID
}

Response: UserProfile[]
```

**USDT_BOT:** ⚠️ Требует адаптации

**Существующий endpoint:**
```python
GET /api/v1/users
Response: UserListResponse {
  users: User[];
  total: int;
  page: int;
  per_page: int;
}
```

**Требуется:**
- Добавить query параметр `search`
- Добавить `?no_pagination=true`

**Приоритет:** 🟡 Средний

---

### POST /api/v1/admin/users/update

**TelePay:**
```typescript
Request: {
  userId: number;
  balance?: number;
  fiatBalance?: number;
  status?: "active" | "frozen";
  role?: UserRole;
}

Response: {
  success: boolean;
  user: UserProfile;
}
```

**USDT_BOT:** ⚠️ Требует адаптации

**Существующий endpoint:**
```python
PATCH /api/v1/users/{user_id}
Request: {
  role?: RoleEnum;
  is_blocked?: bool;
}
```

**Требуется:**
- Добавить поля `balance`, `fiat_balance`
- Переименовать `is_blocked` → `status` (active/frozen)
- Добавить проверку прав (admin не может назначать admin/super_admin)

**Приоритет:** 🟡 Средний

---

### POST /api/v1/admin/moderation

**TelePay:**
```typescript
Request: {
  transactionId: string;
  status: "completed" | "rejected";
  rejectionReason?: string;
}

Response: {
  success: boolean;
  order: ExchangeOrder;
  users: UserProfile[];  // Обновлённые балансы
}
```

**USDT_BOT:** ⚠️ Требует адаптации

**Существующий endpoint:**
```python
PATCH /api/v1/orders/{order_id}
Request: {
  status: OrderStatus;
  rejection_reason?: str;
}
```

**Требуется:**
- Возвращать обновлённый user profile
- Автоматически обновлять баланс при завершении

**Приоритет:** 🔴 Высокий

---

### POST /api/v1/admin/bulk-moderation

**TelePay:**
```typescript
Request: {
  transactionIds: string[];
  status: "completed" | "rejected";
  rejectionReason?: string;
}

Response: {
  success: boolean;
  processedCount: number;
  processedIds: string[];
}
```

**USDT_BOT:** ❌ Отсутствует

**Требуется создать:**
- Endpoint: `POST /api/v1/orders/bulk-update`
- Обработка массива order_id
- Транзакционная обработка (все или ничего)
- Обновление балансов пользователей

**Приоритет:** 🟢 Низкий (можно отложить)

---

## 6. Поддержка

### GET /api/v1/support/tickets

**TelePay:**
```typescript
Response: SupportTicket[] {
  id: string;              // "TK-100234"
  userId: number;
  username: string;
  subject: string;
  orderId?: string;
  status: "open" | "closed";
  messages: SupportMessage[];
  createdAt: string;
  updatedAt: string;
}

SupportMessage {
  id: string;
  senderId: number;
  senderName: string;
  senderRole: UserRole;
  text: string;
  timestamp: string;
}
```

**USDT_BOT:** ❌ Отсутствует

**Требуется создать:**

1. **Модели БД:**
```python
# app/database/models/support_ticket.py
class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id: Mapped[int]
    ticket_id: Mapped[str]  # TK-100234
    user_id: Mapped[int]
    subject: Mapped[str]
    order_id: Mapped[int | None]
    status: Mapped[str]  # open, closed
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

# app/database/models/support_message.py
class SupportMessage(Base):
    __tablename__ = "support_messages"
    id: Mapped[int]
    ticket_id: Mapped[int]
    sender_id: Mapped[int]
    text: Mapped[str]
    created_at: Mapped[datetime]
```

2. **Миграция:**
```bash
uv run alembic revision -m "add_support_system"
```

3. **Роутер:**
```python
# app/api/routers/support.py
@router.get("/tickets")
async def get_tickets(...)

@router.post("/tickets")
async def create_ticket(...)

@router.post("/tickets/{ticket_id}/messages")
async def add_message(...)

@router.post("/tickets/{ticket_id}/close")
async def close_ticket(...)
```

4. **Репозиторий:**
```python
# app/repositories/support_repo.py
class SupportRepository(BaseRepository[SupportTicket]):
    async def get_user_tickets(user_id: int)
    async def get_all_tickets()
    async def add_message(ticket_id: int, message: SupportMessage)
```

5. **Сервис:**
```python
# app/services/support_service.py
class SupportService:
    async def create_ticket(...)
    async def add_message(...)
    async def close_ticket(...)
    async def notify_operators(...)  # ARQ задача
```

**Приоритет:** 🔴 Высокий

---

### POST /api/v1/support/tickets

**TelePay:**
```typescript
Request: {
  subject: string;
  text: string;
  orderId?: string;
}

Response: {
  success: boolean;
  ticket: SupportTicket;
}
```

**Действие:** Создать как часть системы поддержки

---

### POST /api/v1/support/tickets/:id/messages

**TelePay:**
```typescript
Request: {
  text: string;
}

Response: {
  success: boolean;
  message: SupportMessage;
  ticket: SupportTicket;
}
```

**Действие:** Создать как часть системы поддержки

---

### POST /api/v1/support/tickets/:id/close

**TelePay:**
```typescript
Response: {
  success: boolean;
  ticket: SupportTicket;
}
```

**Действие:** Создать как часть системы поддержки

---

## Сводная таблица приоритетов

| Endpoint | Статус | Приоритет | Оценка |
|----------|--------|-----------|--------|
| `POST /api/v1/auth/telegram/verify` | ❌ | 🔴 Критический | 4 часа |
| `GET /api/v1/user/profile` | ❌ | 🔴 Высокий | 2 часа |
| `GET /api/v1/exchange/settings` | 🔄 | 🔴 Высокий | 3 часа |
| `GET /api/v1/exchange/orders` | ⚠️ | 🔴 Высокий | 2 часа |
| `POST /api/v1/exchange/orders` | ⚠️ | 🔴 Высокий | 3 часа |
| `POST /api/v1/admin/moderation` | ⚠️ | 🔴 Высокий | 2 часа |
| `GET /api/v1/support/tickets` | ❌ | 🔴 Высокий | 8 часов |
| `POST /api/v1/support/tickets` | ❌ | 🔴 Высокий | - |
| `POST /api/v1/support/tickets/:id/messages` | ❌ | 🔴 Высокий | - |
| `POST /api/v1/exchange/orders/complain` | ❌ | 🟡 Средний | 1 час |
| `POST /api/v1/exchange/orders/cancel` | ❌ | 🟡 Средний | 2 часа |
| `GET /api/v1/admin/stats` | 🔄 | 🟡 Средний | 2 часа |
| `GET /api/v1/admin/users` | ⚠️ | 🟡 Средний | 1 час |
| `POST /api/v1/admin/users/update` | ⚠️ | 🟡 Средний | 2 часа |
| `POST /api/v1/support/tickets/:id/close` | ❌ | 🟡 Средний | - |
| `POST /api/v1/admin/bulk-moderation` | ❌ | 🟢 Низкий | 3 часа |

**Общая оценка:** ~35-40 часов разработки backend

---

## Рекомендации по реализации

### Порядок разработки

1. **Критические endpoints (день 1-2):**
   - `POST /api/v1/auth/telegram/verify`
   - `GET /api/v1/user/profile`
   - Расширение `GET /api/v1/exchange/settings`

2. **Основной функционал (день 3-4):**
   - Адаптация orders endpoints
   - Система поддержки (модели + миграция)
   - Support tickets endpoints

3. **Дополнительный функционал (день 5):**
   - Admin endpoints
   - Complain/Cancel функции
   - Bulk moderation

### Тестирование

Для каждого endpoint создать:
- Unit тесты (pytest)
- Integration тесты с БД
- API тесты (httpx)

### Документация

Обновить после реализации:
- `docs/modules.md` — новые роутеры
- `docs/database.md` — новые таблицы
- `docs/architecture.md` — новые компоненты

---

## См. также

- **План интеграции:** `INTEGRATION_PLAN.md`
- **Архитектура:** `architecture.md`
- **База данных:** `database.md`
