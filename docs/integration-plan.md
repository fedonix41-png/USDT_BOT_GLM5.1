# План интеграции TelePay Mini App → WebApp

> **Дата создания**: 2026-05-30  
> **Статус**: Утверждён к реализации  
> **Цель**: Точное перенесение UI-дизайна и функциональности TelePay Mini App в основной webapp с последующей настройкой взаимодействия с реальным backend.

---

## 1. Анализ текущего состояния

### 1.1. Основной webapp (STUB)

| Файл | Строк | Содержание |
|------|-------|-----------|
| `App.tsx` | 100 | Базовая авторизация + маршрутизация по ролям |
| `UserDashboard.tsx` | 51 | Баланс, курсы, заглушка «в разработке» |
| `AdminDashboard.tsx` | 20 | Роль, заглушка «в разработке» |
| `useAuthStore.ts` | 96 | Zustand-стор, **сломанные API-пути** (`/api/v1/exchange/*`) |
| `types.ts` | 80 | Интерфейсы, несовместимые с backend-схемами |
| `index.css` | 54 | Корректный Tailwind v4 + custom classes (идентичны telepay) |

### 1.2. TelePay Mini App (ПОЛНЫЙ)

| Файл | Строк | Содержание |
|------|-------|-----------|
| `App.tsx` | 404 | Auth + Dev Panel + Toast + Bot-Disabled экран |
| `UserDashboard.tsx` | 1928 | Обмен, история, профиль/KYC, рефералы, поддержка |
| `AdminDashboard.tsx` | 1491 | Модерация, CRM, поддержка, настройки, статистика |
| `useAuthStore.ts` | 99 | Zustand-стор, **сломанные API-пути** (`/api/v1/exchange/*`) |
| `types.ts` | 80 | Идентичен основному webapp |
| `index.css` | 55 | Идентичен основному webapp |

### 1.3. CSS и дизайн-система

Идентичны между проектами. Классы `.glass`, `.usdt-green`, `.usdt-bg`, `.tab-active`, шрифты, скроллбары — полностью совпадают. Дополнительных CSS-правил при миграции не требуется.

---

## 2. GAP-анализ: несоответствия между TelePay UI и реальным Backend

### 2.1. Типовые несоответствия (Frontend ↔ Backend)

| Поле | TelePay Frontend | Реальный Backend | Действие |
|------|------------------|------------------|----------|
| `Order.id` | `string` ("EX-1002") | `int` | Адаптировать в API-слое |
| `Order.status` | `"pending"` / `"completed"` / `"rejected"` | `"created"` / `"completed"` / `"cancelled"` | Маппинг: `created→pending`, `cancelled→rejected` |
| `Order.amountRub` | `amountRub: number` | `total_fiat: Decimal` | Маппинг полей |
| `Order.clientDetails` | `clientDetails: string` | `payment_link_snapshot: str` (encrypted) | Маппинг полей |
| `Order.requisitesSelected` | `requisitesSelected: string` | Нет в модели | Добавить в ответ API (из глобальных реквизитов) |
| `Order.complained` | `complained: boolean` | `link_broken: boolean` | Маппинг: `link_broken→complained` |
| `Order.username` | `username: string` | Нет в OrderResponse | Добавить через join user |
| `Order.rejectionReason` | `rejectionReason?: string` | Нет в модели | Добавить колонку в БД |
| `User.status` | `"active"` / `"frozen"` | `is_blocked: bool` | Маппинг: `!is_blocked→active`, `is_blocked→frozen` |
| `User.fiatBalance` | `fiatBalance` | `fiat_balance` | Маппинг camelCase→snake_case |
| Settings.buyRate / sellRate | Поля в SystemSettings | Отдельный эндпоинт `/api/v1/rates` | Объединить в составной эндпоинт |
| Settings.requisitesCard | Поля в SystemSettings | Нет в БД | Добавить хранение реквизитов |
| Settings.requisitesWallet | Поля в SystemSettings | Нет в БД | Добавить хранение реквизитов |
| Settings.notificationChats | `notificationChats: string[]` | Таблица `notification_chats` | Возвращать в составе settings |

### 2.2. Отсутствующие Backend-эндпоинты

| TelePay эндпоинт | Назначение | Необходимость | Решение |
|------------------|-----------|---------------|---------|
| `POST /api/v1/exchange/orders` | Создание заявки клиентом | **Критично** | Создать `POST /api/v1/orders` (client+) |
| `GET /api/v1/exchange/orders` (client) | Список своих заявок | **Критично** | Создать `GET /api/v1/user/orders` |
| `POST /api/v1/exchange/orders/cancel` | Отмена своей заявки | **Критично** | Расширить `PATCH /api/v1/orders/{id}/status` для клиента |
| `POST /api/v1/exchange/orders/complain` | Жалоба на заявку | Важно | Создать `POST /api/v1/orders/{id}/complain` |
| `GET /api/v1/exchange/settings` | Курсы + флаги + реквизиты | **Критично** | Создать `GET /api/v1/exchange/settings` |
| `POST /api/v1/exchange/settings` | Сохранение настроек | Важно | Создать `PATCH /api/v1/exchange/settings` |
| `POST /api/v1/admin/users/update` | Редактирование пользователя | Важно | Создать `PATCH /api/v1/users/{id}` |
| `POST /api/v1/admin/bulk-moderation` | Массовая модерация | Желательно | Создать `POST /api/v1/orders/bulk-status` |
| `GET /api/v1/support/tickets` | Тикеты поддержки | Важно | Создать модуль support |
| `POST /api/v1/support/tickets` | Создание тикета | Важно | Создать модуль support |
| `POST /api/v1/support/tickets/:id/messages` | Сообщения в тикете | Важно | Создать модуль support |
| `POST /api/v1/support/tickets/:id/close` | Закрытие тикета | Важно | Создать модуль support |
| `POST /api/v1/dev/switch-role` | Переключение ролей | Dev-only | Не нужен (используем реальный JWT) |

### 2.3. Отсутствующие структуры БД

| Сущность | Необходимость | Действие |
|----------|---------------|----------|
| `requisites_card` в global_settings | **Критично** | Добавить ключ `requisites_card` в global_settings |
| `requisites_wallet` в global_settings | **Критично** | Добавить ключ `requisites_wallet` в global_settings |
| `rejection_reason` в orders | Важно | Добавить колонку `rejection_reason` |
| Таблица `support_tickets` | Важно | Новая миграция |
| Таблица `support_messages` | Важно | Новая миграция |

---

## 3. Взвешенный план реализации

### Принцип приоритизации

- **P0 (Критично)**: Без этого UI не функционирует — обмен, просмотр заявок, авторизация
- **P1 (Важно)**: Ключевые функции для полноценной работы — поддержка, жалобы, редактирование CRM
- **P2 (Желательно)**: Улучшения UX — массовая модерация, dev-панель, пульсации

### Зависимости между волнами

```
Волна 0 (Типы + API-адаптер)
  ↓
Волна 1 (Backend API — P0 эндпоинты)
  ↓
Волна 2 (Миграция UI — UserDashboard + AdminDashboard)
  ↓
Волна 1b (Backend API — P1 эндпоинты: support)
  ↓
Волна 2b (Активация P1 UI — support tab)
  ↓
Волна 3 (Тестирование + документация)
```

---

## 4. Волна 0: Гармонизация типов и API-адаптер

**Цель**: Создать фундамент, на котором UI-компоненты будут работать с реальным backend.

### 4.1. Обновить `types.ts` — привести в соответствие с backend-схемами

```typescript
// UserProfile: маппинг snake_case → camelCase при получении из API
export interface UserProfile {
  id: number;
  telegramId: number;        // + новое поле (backend: telegram_id)
  username: string | null;   // null-able (backend: str | None)
  fullName: string | null;    // + новое поле (backend: full_name)
  role: UserRole;
  isBlocked: boolean;         // вместо status: "active" | "frozen"
  balance: number;
  fiatBalance: number;
  referralsCount: number;
  referralEarned: number;
  createdAt: string;          // + новое поле
}

// ExchangeOrder: маппинг snake_case + статусы
export interface ExchangeOrder {
  id: number;                        // int, не string
  userId: number;
  username: string;                  // из user-join
  orderType: "buy" | "sell";         // вместо type
  amountUsdt: number;
  rate: number;
  totalFiat: number;                 // вместо amountRub
  status: "created" | "completed" | "cancelled";  // реальные статусы
  paymentLinkSnapshot: string;       // вместо clientDetails
  requisitesSelected: string;        // добавляется API из global_settings
  linkBroken: boolean;               // вместо complained
  rejectionReason: string | null;    // + новое поле
  createdAt: string;
  updatedAt: string;
}

// SystemSettings: объединяет rates + flags + requisites
export interface SystemSettings {
  buyRate: number | null;
  sellRate: number | null;
  buyEnabled: boolean;
  sellEnabled: boolean;
  botEnabled: boolean;
  requisitesCard: string;
  requisitesWallet: string;
  notificationChats: string[];
}
```

### 4.2. Создать API-клиент `src/api/client.ts`

Централизованный HTTP-клиент с:
- Автоматическая подстановка `Authorization: Bearer <token>` из Zustand-стора
- Базовый URL из env (`VITE_API_URL` или относительный `/api`)
- Методы для каждого эндпоинта
- Маппинг snake_case ↔ camelCase
- Маппинг статусов заказов (`created→pending` для UI, `pending→created` для API)
- Единая обработка ошибок (401 → logout, 403 → forbidden, etc.)

### 4.3. Обновить `useAuthStore.ts`

- Заменить `/api/v1/exchange/*` на реальные пути
- Добавить Authorization headers ко всем fetch-вызовам
- `refreshUserData()` → 3 параллельных запроса: profile + exchange/settings + user/orders
- Добавить действия: `setTickets`, `updateUserFiatBalance`

### 4.4. Файлы, затрагиваемые в волне 0

| Файл | Действие |
|------|----------|
| `webapp/src/types.ts` | Переписать |
| `webapp/src/api/client.ts` | Создать (новый) |
| `webapp/src/api/mappers.ts` | Создать (новый, маппинг snake↔camel) |
| `webapp/src/store/useAuthStore.ts` | Переписать |
| `webapp/src/App.tsx` | Адаптировать auth flow |

---

## 5. Волна 1: Расширение Backend API (P0 — Критичные эндпоинты)

**Цель**: Добавить backend-эндпоинты, без которых UI обмена не работает.

### 5.1. Составной эндпоинт настроек: `GET /api/v1/exchange/settings` [P0]

Возвращаетrates + flags + requisites одним ответом. Это устраняет 3 отдельных fetch-вызова.

```
GET /api/v1/exchange/settings
Auth: Bearer (любая роль, включая client)
Response: {
  buy_rate: Decimal | null,
  sell_rate: Decimal | null,
  buy_enabled: bool,
  sell_enabled: bool,
  bot_enabled: bool,
  requisites_card: str,
  requisites_wallet: str,
  notification_chats: str[]
}
```

**Реализация**:
- Новый роутер `app/api/routers/exchange.py`
- Читает `global_settings` (flags) + `rates` (latest) + `requisites_*` (keys) + `notification_chats`
- Минимальная роль: любая (client+)

### 5.2. Эндпоинт клиентских заявок: `GET /api/v1/user/orders` [P0]

Список собственных заявок клиента.

```
GET /api/v1/user/orders
Auth: Bearer (client+)
Response: OrderListResponse (с user-join для username)
```

**Реализация**:
- Новый роут в `app/api/routers/users.py` или `exchange.py`
- Фильтрация по `current_user.id`
- Include user-relationship для username

### 5.3. Создание заявки: `POST /api/v1/orders` [P0]

Создание exchange-заявки клиентом через API (вместо WebApp.sendData).

```
POST /api/v1/orders
Auth: Bearer (client+)
Body: {
  order_type: "buy" | "sell",
  amount_usdt: Decimal,
  client_details: str   // USDT-адрес (buy) или реквизиты карты (sell)
}
Response: OrderResponse
```

**Реализация**:
- Расширить `app/api/routers/orders.py`
- Проверка флагов `buy_enabled` / `sell_enabled`
- Проверка мин. суммы (10 USDT)
- При sell — проверка `user.balance >= amount_usdt` и списание
- При buy — без списания (USDT начисляются после одобрения)
- Авто-расчёт `rate` (из текущего курса) и `total_fiat`
- Авто-подстановка `requisitesSelected` из global_settings

### 5.4. Отмена заявки клиентом: `PATCH /api/v1/orders/{id}/status` [P0]

Расширить существующий эндпоинт для возможности отмены клиентом **своей** заявки.

```
PATCH /api/v1/orders/{id}/status
Auth: Bearer (client может отменить только свой order со статусом created)
Body: { status: "cancelled" }
```

**Реализация**:
- Модифицировать `app/api/routers/orders.py:update_order_status`
- Если `current_user.role == client`: проверить `order.user_id == current_user.id` и `order.status == created`
- При отмене sell-заявки → возврат USDT на баланс

### 5.5. Хранение реквизитов: `requisites_card` + `requisites_wallet` [P0]

**Реализация**:
- Добавить 2 записи в `global_settings` через миграцию:
  - `key='requisites_card'`, `value='0000 0000 0000 0000'`
  - `key='requisites_wallet'`, `value='TXxxxxxxxxxxxxxxxxxxxxxxxxxx'`
- Новая миграция `006_add_requisites.py`

### 5.6. Колонка `rejection_reason` в `orders` [P1]

**Реализация**:
- Добавить колонку `rejection_reason = Column(Text, nullable=True)` в Order
- Новая миграция `007_add_rejection_reason.py`
- Обновить `OrderResponse` schema

### 5.7. Файлы, затрагиваемые в волне 1

| Файл | Действие |
|------|----------|
| `app/api/routers/exchange.py` | Создать (новый) |
| `app/api/routers/orders.py` | Расширить (POST + client cancel) |
| `app/api/routers/users.py` | Добавить GET /api/v1/user/orders |
| `app/api/schemas/exchange.py` | Создать (новый) |
| `app/api/schemas/order.py` | Обновить (rejection_reason) |
| `app/api/app.py` | Зарегистрировать exchange-роутер |
| `app/database/models/order.py` | Добавить rejection_reason |
| `migrations/versions/006_add_requisites.py` | Создать |
| `migrations/versions/007_add_rejection_reason.py` | Создать |
| `app/services/order_service.py` | Расширить (create + client cancel) |
| `app/services/settings_service.py` | Добавить get_requisites() |

---

## 6. Волна 1b: Расширение Backend API (P1 — Система поддержки)

**Цель**: Добавить систему тикетов поддержки.

### 6.1. Таблица `support_tickets`

```sql
CREATE TABLE support_tickets (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  subject VARCHAR(255) NOT NULL,
  order_id INTEGER REFERENCES orders(id),
  status VARCHAR(20) DEFAULT 'open',  -- open / closed
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### 6.2. Таблица `support_messages`

```sql
CREATE TABLE support_messages (
  id SERIAL PRIMARY KEY,
  ticket_id INTEGER NOT NULL REFERENCES support_tickets(id),
  sender_id INTEGER NOT NULL REFERENCES users(id),
  text TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### 6.3. API-эндпоинты

| Метод | Путь | Роль | Описание |
|-------|------|------|----------|
| `GET` | `/api/v1/support/tickets` | client (свои), operator+ (все) | Список тикетов |
| `POST` | `/api/v1/support/tickets` | client+ | Создать тикет |
| `GET` | `/api/v1/support/tickets/{id}` | client (свой), operator+ | Получить тикет |
| `POST` | `/api/v1/support/tickets/{id}/messages` | client (свой), operator+ | Добавить сообщение |
| `POST` | `/api/v1/support/tickets/{id}/close` | client (свой), operator+ | Закрыть тикет |

### 6.4. Файлы, затрагиваемые в волне 1b

| Файл | Действие |
|------|----------|
| `app/database/models/support_ticket.py` | Создать |
| `app/api/schemas/support.py` | Создать |
| `app/api/routers/support.py` | Создать |
| `app/repositories/support_repo.py` | Создать |
| `app/services/support_service.py` | Создать |
| `app/api/app.py` | Зарегистрировать support-роутер |
| `migrations/versions/008_add_support_tables.py` | Создать |

---

## 7. Волна 2: Миграция UI-компонентов

**Цель**: Точное перенесение UI TelePay в webapp с адаптацией под реальный API.

### 7.1. Стратегия миграции

UI-компоненты TelePay переносятся **целиком**, с последующей адаптацией:

1. **Копирование**: Полный перенос JSX/TSX разметки и стилей (1:1)
2. **Адаптация API**: Замена прямых `fetch()` вызовов на `api/client.ts`
3. **Адаптация типов**: Замена прямого обращения к полям на маппинг
4. **Удаление mock-логики**: Убрать localStorage-based KYC/уровни/пресеты (заглушки)
5. **Dev-панель**: Убрать (для production) или скрыть за `import.meta.env.DEV`

### 7.2. `App.tsx` — обновление

**Что перенести из TelePay**:
- Toast-система уведомлений (AnimatePresence + motion)
- Экран «Бот временно недоступен» для клиентов
- Улучшенный экран ошибки авторизации с кнопкой «Повторить»
- Обёртка viewport (стеклянный мобильный фрейм на десктопе)
- Радиальные фоновые декорации

**Что НЕ переносить**:
- Dev Panel (sidebar) — скрыть за `import.meta.env.DEV`
- Role switching — заменить на реальный JWT-auth
- Faucet deposit — dev-only

### 7.3. `UserDashboard.tsx` — полная замена

**5 вкладок** (из TelePay):
1. **Exchange** — покупка/продажа USDT с формой, конвертером, реквизитами
2. **History** — список собственных заявок со статусами
3. **Profile (Cabinet)** — профиль, пресеты, sparkline курса
4. **Referrals** — реферальная ссылка и статистика
5. **Support** — тикеты поддержки

**Адаптации**:
- `fetch("/api/v1/exchange/orders")` → `apiClient.getUserOrders()`
- `fetch("/api/v1/exchange/settings")` → `apiClient.getExchangeSettings()`
- `POST /api/v1/exchange/orders` → `apiClient.createOrder()`
- `POST /api/v1/exchange/orders/cancel` → `apiClient.cancelOrder()`
- Убрать localStorage-заглушки KYC (оставить UI, но подключить к API когда будет backend)
- Sparkline курса → `GET /api/v1/rates/history`

### 7.4. `AdminDashboard.tsx` — полная замена

**5 вкладок** (из TelePay):
1. **Moderation** — очередь заявок, approve/reject, bulk actions
2. **Users (CRM)** — поиск, редактирование балансов/ролей/статусов
3. **Support** — все тикеты, ответы, закрытие
4. **Settings** — курсы, флаги, реквизиты, чаты уведомлений
5. **Stats** — статистика объёмов

**Адаптации**:
- `GET /api/v1/admin/stats` → `apiClient.getStatistics()`
- `GET /api/v1/admin/users` → `apiClient.getUsers()`
- `POST /api/v1/admin/users/update` → `apiClient.updateUser()`
- `POST /api/v1/admin/moderation` → `apiClient.updateOrderStatus()`
- `POST /api/v1/admin/bulk-moderation` → `apiClient.bulkModerate()`
- Settings tab → `apiClient.getExchangeSettings()` + `apiClient.updateExchangeSettings()`

### 7.5. Файлы, затрагиваемые в волне 2

| Файл | Действие |
|------|----------|
| `webapp/src/App.tsx` | Переписать (с toast + bot-disabled + viewport) |
| `webapp/src/components/user/UserDashboard.tsx` | Переписать (полный TelePay UI) |
| `webapp/src/components/admin/AdminDashboard.tsx` | Переписать (полный TelePay UI) |
| `webapp/src/components/shared/LoadingSkeleton.tsx` | Синхронизировать (идентичны) |
| `webapp/src/components/shared/QrCodeGenerator.tsx` | Синхронизировать (идентичны) |
| `webapp/src/index.css` | Не менять (идентичны) |

---

## 8. Волна 2b: Активация P1 UI (Support)

**Цель**: Подключить вкладки поддержки после завершения backend-модуля support.

- Активировать Support tab в `UserDashboard.tsx`
- Активировать Support tab в `AdminDashboard.tsx`
- Подключить к `apiClient.getTickets()`, `createTicket()`, `sendMessage()`, `closeTicket()`

---

## 9. Волна 3: Интеграционная проверка и документация

### 9.1. Проверочные сценарии

| Сценарий | Роль | Ожидаемый результат |
|----------|------|---------------------|
| Авторизация через Telegram | client | JWT-токен, загрузка профиля + настроек |
| Покупка USDT | client | Создание заявки, отображение в истории |
| Продажа USDT | client | Списание USDT, создание заявки |
| Отмена заявки | client | Возврат USDT (sell), статус cancelled |
| Модерация | operator | Approve (зачисление USDT для buy) / Reject |
| Настройки | admin | Изменение курса, флагов, реквизитов |
| CRM | admin | Поиск, блокировка, редактирование баланса |
| Статистика | operator | Корректные цифры объёмов |
| Бот отключён | client | Экран «технические работы» |

### 9.2. Обновление документации

| Документ | Обновление |
|----------|-----------|
| `docs/architecture.md` | Добавить exchange + support роутеры |
| `docs/database.md` | Добавить support_tickets, support_messages, rejection_reason |
| `docs/modules.md` | Добавить новые файлы |
| `docs/roles.md` | Уточнить права client на API-эндпоинты |
| `docs/stack.md` | Обновить версии frontend-зависимостей |
| `docs/issues.md` | Удалить устранённые проблемы, добавить новые |

---

## 10. Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Несовместимость snake_case/camelCase между API и UI | Высокая | Среднее | Централизованный маппинг в `api/mappers.ts` |
| Расхождение статусов заказов (created/pending) | Высокая | Низкое | Явный маппинг в API-клиенте |
| Отсутствие rejection_reason в текущей БД | Средняя | Низкое | Миграция 007; UI показывает null-safe |
| Регресс в существующих Bot FSM-сценариях | Низкая | Высокое | Не менять существующие handlers, только добавлять API |
| Dev-панель утекает в production | Низкая | Среднее | Условный рендеринг по `import.meta.env.DEV` |
| EncryptionService для payment_link_snapshot | Средняя | Среднее | API возвращает расшифрованные данные только для authorized user |

---

## 11. Порядок выполнения (итоговая таблица)

| # | Волна | Задачи | Файлы | Приоритет |
|---|-------|--------|-------|-----------|
| 0 | Foundation | types.ts + api/client.ts + api/mappers.ts + useAuthStore.ts | 4 файла | P0 |
| 1a | Backend P0 | exchange settings + client orders + create order + cancel | ~8 файлов | P0 |
| 1b | Backend P0 | requisites migration + rejection_reason migration | 2 миграции | P0 |
| 2a | UI Migration | App.tsx + UserDashboard.tsx + AdminDashboard.tsx | 3 файла | P0 |
| 1c | Backend P1 | support tickets module | ~6 файлов | P1 |
| 2b | UI P1 | Activate support tabs | В рамках 2a | P1 |
| 3 | Verification | Integration testing + docs update | docs/ | P1 |
