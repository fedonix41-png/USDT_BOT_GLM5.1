# План интеграции TelePay Mini App

> **Дата создания:** 2024
> **Статус:** Планирование
> **Цель:** Интеграция полнофункционального Telegram Mini App из репозитория `usdt-telepay-mini-app` в текущий проект USDT_BOT

---

## Анализ текущего состояния

### Текущий проект (USDT_BOT_GLM5.1)

**Backend (Python):**
- ✅ Aiogram 3.x бот с FSM
- ✅ REST API на aiohttp (порт 8081)
- ✅ PostgreSQL 15 + SQLAlchemy 2.0 async
- ✅ Redis (кеш + ARQ очередь)
- ✅ JWT аутентификация
- ✅ Система ролей: client, operator, admin, super_admin
- ✅ Полная бизнес-логика обмена USDT
- ✅ Шифрование реквизитов (AES-256-CBC)
- ✅ Миграции Alembic

**Frontend (webapp/):**
- ⚠️ Базовый React + Vite скелет
- ⚠️ Только Calculator компонент (минимальный UI)
- ⚠️ Нет роутинга по ролям
- ⚠️ Нет админ-панели
- ⚠️ Нет системы поддержки

### TelePay Mini App (внешний репозиторий)

**Frontend (React + TypeScript):**
- ✅ Полноценный UI с роутингом по ролям
- ✅ UserDashboard (клиентский кабинет)
- ✅ AdminDashboard (CRM для операторов/админов)
- ✅ Система поддержки (тикеты)
- ✅ Zustand state management
- ✅ Tailwind CSS + Motion анимации
- ✅ Haptic feedback интеграция
- ✅ Dev Panel для тестирования

**Backend (Express + TypeScript):**
- ⚠️ In-memory база данных (mock)
- ⚠️ Все API endpoints в одном файле server.ts
- ⚠️ Нет персистентности данных
- ⚠️ Нет валидации Telegram подписи

---

## Стратегия интеграции

### Принцип: Frontend из TelePay + Backend из USDT_BOT

**Что берём:**
- ✅ Весь frontend из TelePay (React компоненты, UI/UX, дизайн)
- ✅ Архитектуру компонентов и роутинг
- ✅ Zustand store структуру

**Что НЕ берём:**
- ❌ Express backend (server.ts)
- ❌ In-memory базу данных
- ❌ Mock API endpoints

**Что адаптируем:**
- 🔄 API вызовы frontend → существующий aiohttp REST API
- 🔄 TypeScript типы → соответствие схемам Python API
- 🔄 Аутентификацию → JWT токены вместо mock
- 🔄 WebApp.sendData() → интеграция с Telegram Bot

---

## Roadmap интеграции

### Фаза 1: Подготовка и анализ

**Задачи:**

1. **Аудит API совместимости**
   - Сравнить endpoints TelePay server.ts с текущим aiohttp API
   - Выявить недостающие endpoints в Python API
   - Составить mapping таблицу

2. **Анализ типов данных**
   - Сопоставить TypeScript интерфейсы с Pydantic схемами
   - Выявить расхождения в структуре данных
   - Определить необходимые изменения

3. **Оценка зависимостей**
   - Проверить совместимость версий React/Vite
   - Определить новые npm пакеты (Tailwind, Motion, Zustand)
   - Оценить размер bundle после интеграции

**Результат:** Документ с детальным mapping и списком изменений

---

### Фаза 2: Расширение Backend API

**Задачи:**

1. **Добавить недостающие endpoints**
   
   Необходимые новые endpoints:
   ```
   GET  /api/v1/user/profile              # Профиль текущего пользователя
   GET  /api/v1/admin/stats               # Статистика для операторов
   GET  /api/v1/admin/users               # CRM список пользователей
   POST /api/v1/admin/bulk-moderation     # Массовая модерация заявок
   GET  /api/v1/support/tickets           # Список тикетов поддержки
   POST /api/v1/support/tickets           # Создать тикет
   POST /api/v1/support/tickets/:id/messages  # Добавить сообщение
   POST /api/v1/support/tickets/:id/close     # Закрыть тикет
   POST /api/v1/exchange/orders/complain      # Жалоба на битую ссылку
   POST /api/v1/exchange/orders/cancel        # Отмена заявки клиентом
   ```

2. **Создать модели для тикетов поддержки**
   - Таблица `support_tickets`
   - Таблица `support_messages`
   - Миграция Alembic

3. **Расширить существующие endpoints**
   - Добавить поле `complained` в Order
   - Добавить поля `referredBy`, `referralsCount`, `referralEarned` в User
   - Добавить `fiatBalance` в User (опционально)

4. **Создать Pydantic схемы**
   - `app/api/schemas/support.py`
   - Расширить `app/api/schemas/statistics.py`
   - Обновить `app/api/schemas/user.py`

5. **Создать роутеры**
   - `app/api/routers/support.py`
   - Расширить `app/api/routers/statistics.py`

6. **Создать репозитории и сервисы**
   - `app/repositories/support_repo.py`
   - `app/services/support_service.py`

**Результат:** Полностью совместимый REST API

---

### Фаза 3: Миграция Frontend

**Задачи:**

1. **Перенос структуры проекта**
   ```
   webapp/
   ├── src/
   │   ├── components/
   │   │   ├── admin/
   │   │   │   └── AdminDashboard.tsx
   │   │   ├── user/
   │   │   │   └── UserDashboard.tsx
   │   │   └── shared/
   │   │       ├── LoadingSkeleton.tsx
   │   │       └── QrCodeGenerator.tsx
   │   ├── store/
   │   │   └── useAuthStore.ts
   │   ├── types.ts
   │   ├── App.tsx
   │   ├── main.tsx
   │   └── index.css
   ├── package.json
   ├── tsconfig.json
   ├── tailwind.config.js
   └── vite.config.ts
   ```

2. **Установка зависимостей**
   ```bash
   cd webapp
   npm install zustand motion lucide-react
   npm install -D tailwindcss autoprefixer @tailwindcss/vite
   npm install -D typescript @types/node
   ```

3. **Настройка TypeScript**
   - Создать `tsconfig.json`
   - Конвертировать `.jsx` → `.tsx`
   - Добавить типы для Telegram WebApp

4. **Настройка Tailwind CSS**
   - Создать `tailwind.config.js`
   - Интегрировать с Vite
   - Перенести стили из TelePay

5. **Адаптация API клиента**
   - Изменить базовый URL с `/api/v1` на `${VITE_API_URL}/api/v1`
   - Добавить JWT токен в заголовки
   - Обработать ошибки 401 (redirect на login)

**Результат:** Работающий frontend с новым UI

---

### Фаза 4: Интеграция аутентификации

**Задачи:**

1. **Telegram WebApp аутентификация**
   - Создать endpoint `POST /api/v1/auth/telegram/verify`
   - Валидация `initData` через Bot API
   - Генерация JWT токена
   - Возврат user profile

2. **Обновить useAuthStore**
   - Хранить JWT токен в localStorage
   - Автоматическое добавление токена в запросы
   - Refresh token логика
   - Logout с очисткой состояния

3. **Middleware для WebApp**
   - Проверка Telegram подписи
   - Извлечение user_id из initData
   - Создание/обновление пользователя в БД

4. **Интеграция с ботом**
   - Добавить inline кнопку "Открыть Mini App" в главное меню
   - Настроить WebApp URL в BotFather
   - Обработка WebApp.sendData() в боте

**Результат:** Полная интеграция с Telegram

---

### Фаза 5: Адаптация компонентов

**Задачи:**

1. **UserDashboard**
   - Подключить к реальному API
   - Адаптировать создание заявок
   - Интегрировать Calculator
   - Добавить историю операций
   - Реализовать жалобу на битую ссылку

2. **AdminDashboard**
   - Подключить статистику
   - Реализовать модерацию заявок
   - Добавить CRM пользователей
   - Интегрировать настройки системы
   - Реализовать управление курсами

3. **Support система**
   - Создать компоненты тикетов
   - Реализовать чат с оператором
   - Добавить уведомления о новых сообщениях
   - Интегрировать с Telegram уведомлениями

4. **Удалить Dev Panel**
   - Убрать панель разработчика из production
   - Оставить только для development режима
   - Добавить переменную окружения `VITE_DEV_MODE`

**Результат:** Полностью функциональный UI

---

### Фаза 6: Тестирование и оптимизация

**Задачи:**

1. **Функциональное тестирование**
   - Тестирование всех ролей (client, operator, admin, super_admin)
   - Проверка создания/отмены заявок
   - Тестирование модерации
   - Проверка системы поддержки
   - Тестирование настроек

2. **Интеграционное тестирование**
   - Взаимодействие Bot ↔ Mini App
   - Синхронизация данных
   - Уведомления через ARQ
   - Haptic feedback

3. **Тестирование безопасности**
   - Валидация Telegram подписи
   - JWT токены
   - CORS настройки
   - Rate limiting

4. **Оптимизация производительности**
   - Bundle size анализ
   - Lazy loading компонентов
   - Оптимизация изображений
   - Кеширование API запросов

5. **Адаптивность**
   - Тестирование на разных устройствах
   - iOS Safari
   - Android Chrome
   - Desktop Telegram

**Результат:** Стабильное production-ready приложение

---

### Фаза 7: Deployment и мониторинг

**Задачи:**

1. **Обновить Docker конфигурацию**
   - Обновить `Dockerfile.webapp` для TypeScript
   - Добавить multi-stage build
   - Оптимизировать nginx конфигурацию

2. **Настроить переменные окружения**
   ```env
   WEBAPP_URL=https://your-domain.com
   VITE_API_URL=https://api.your-domain.com
   ```

3. **Настроить Cloudflare Tunnel**
   - Обновить маршруты для Mini App
   - Настроить SSL
   - Добавить кеширование статики

4. **Мониторинг**
   - Логирование ошибок frontend
   - Метрики использования
   - Отслеживание производительности

**Результат:** Развёрнутое приложение в production

---

## Детальный mapping API endpoints

### Существующие endpoints (совместимые)

| TelePay Endpoint | USDT_BOT Endpoint | Статус |
|------------------|-------------------|--------|
| `GET /api/v1/exchange/settings` | `GET /api/v1/rates` | ⚠️ Частично (нужно расширить) |
| `GET /api/v1/exchange/orders` | `GET /api/v1/orders` | ✅ Совместим |
| `POST /api/v1/exchange/orders` | `POST /api/v1/orders` | ⚠️ Нужна адаптация |
| `POST /api/v1/exchange/settings` | `PATCH /api/v1/settings` | ⚠️ Разная структура |

### Новые endpoints (требуют реализации)

| Endpoint | Метод | Назначение | Приоритет |
|----------|-------|------------|-----------|
| `/api/v1/user/profile` | GET | Профиль пользователя | 🔴 Высокий |
| `/api/v1/admin/stats` | GET | Статистика системы | 🔴 Высокий |
| `/api/v1/admin/users` | GET | Список пользователей | 🟡 Средний |
| `/api/v1/admin/users/update` | POST | Обновление пользователя | 🟡 Средний |
| `/api/v1/admin/bulk-moderation` | POST | Массовая модерация | 🟢 Низкий |
| `/api/v1/support/tickets` | GET | Список тикетов | 🔴 Высокий |
| `/api/v1/support/tickets` | POST | Создать тикет | 🔴 Высокий |
| `/api/v1/support/tickets/:id/messages` | POST | Добавить сообщение | 🔴 Высокий |
| `/api/v1/support/tickets/:id/close` | POST | Закрыть тикет | 🟡 Средний |
| `/api/v1/exchange/orders/complain` | POST | Жалоба на ссылку | 🟡 Средний |
| `/api/v1/exchange/orders/cancel` | POST | Отмена заявки | 🟡 Средний |
| `/api/v1/auth/telegram/verify` | POST | Telegram аутентификация | 🔴 Высокий |

---

## Изменения в базе данных

### Новые таблицы

**1. support_tickets**
```sql
CREATE TABLE support_tickets (
    id SERIAL PRIMARY KEY,
    ticket_id VARCHAR(20) UNIQUE NOT NULL,  -- TK-100234
    user_id INTEGER REFERENCES users(id),
    subject VARCHAR(255) NOT NULL,
    order_id INTEGER REFERENCES orders(id) NULL,
    status VARCHAR(20) NOT NULL,  -- open, closed
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**2. support_messages**
```sql
CREATE TABLE support_messages (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER REFERENCES support_tickets(id),
    sender_id INTEGER REFERENCES users(id),
    text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Изменения существующих таблиц

**users:**
```sql
ALTER TABLE users ADD COLUMN referred_by VARCHAR(255);
ALTER TABLE users ADD COLUMN referrals_count INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN referral_earned DECIMAL(10,2) DEFAULT 0;
ALTER TABLE users ADD COLUMN fiat_balance DECIMAL(10,2) DEFAULT 0;
```

**orders:**
```sql
ALTER TABLE orders ADD COLUMN complained BOOLEAN DEFAULT FALSE;
ALTER TABLE orders ADD COLUMN client_details TEXT;
ALTER TABLE orders ADD COLUMN requisites_selected TEXT;
```

---

## Изменения в конфигурации

### .env (новые переменные)

```env
# Webapp
WEBAPP_URL=https://your-mini-app.com
VITE_API_URL=https://api.your-domain.com

# Telegram Mini App
TELEGRAM_BOT_WEBAPP_URL=https://your-mini-app.com
```

### package.json (webapp)

```json
{
  "dependencies": {
    "react": "^19.0.1",
    "react-dom": "^19.0.1",
    "zustand": "^5.0.14",
    "motion": "^12.23.24",
    "lucide-react": "^0.546.0",
    "@twa-dev/sdk": "^8.0.2"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^6.0.1",
    "typescript": "~5.8.2",
    "tailwindcss": "^4.1.14",
    "@tailwindcss/vite": "^4.1.14",
    "vite": "^6.2.3"
  }
}
```

---

## Риски и митигация

### Риск 1: Несовместимость API структур
**Вероятность:** Средняя  
**Влияние:** Высокое  
**Митигация:** Создать адаптеры на frontend для преобразования данных

### Риск 2: Проблемы с Telegram WebApp API
**Вероятность:** Средняя  
**Влияние:** Критическое  
**Митигация:** Тщательное тестирование на разных платформах, fallback на web версию

### Риск 3: Увеличение bundle size
**Вероятность:** Высокая  
**Влияние:** Среднее  
**Митигация:** Code splitting, lazy loading, tree shaking

### Риск 4: Конфликты стилей
**Вероятность:** Низкая  
**Влияние:** Низкое  
**Митигация:** Использование Tailwind CSS изолирует стили

### Риск 5: Проблемы с TypeScript миграцией
**Вероятность:** Средняя  
**Влияние:** Среднее  
**Митигация:** Постепенная миграция, использование `any` для сложных типов

---

## Критерии успеха

### Функциональные
- ✅ Все роли работают корректно
- ✅ Создание/отмена заявок
- ✅ Модерация операторами
- ✅ Система поддержки
- ✅ Настройки системы
- ✅ Статистика

### Технические
- ✅ Bundle size < 500KB (gzipped)
- ✅ First Contentful Paint < 1.5s
- ✅ Time to Interactive < 3s
- ✅ Lighthouse Score > 90

### Безопасность
- ✅ Валидация Telegram подписи
- ✅ JWT токены с refresh
- ✅ CORS настроен корректно
- ✅ Rate limiting работает

---

## Следующие шаги

1. ✅ Создан план интеграции
2. ⏳ Утверждение плана
3. ⏳ Начало Фазы 1: Аудит API
4. ⏳ Создание детального mapping документа
5. ⏳ Начало разработки

---

## См. также

- **Архитектура:** `architecture.md`
- **Структура проекта:** `modules.md`
- **База данных:** `database.md`
- **Технологии:** `stack.md`
