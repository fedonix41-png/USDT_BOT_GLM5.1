# USDT Exchange Telegram Mini App

Telegram Mini App для обмена USDT ↔ RUB через P2P платформу.

## Технологии

- **React 19** + **TypeScript**
- **Vite** - сборщик
- **Tailwind CSS 4** - стилизация
- **Zustand** - управление состоянием
- **Motion** - анимации
- **Lucide React** - иконки
- **Telegram WebApp SDK** - интеграция с Telegram

## Установка

```bash
npm install
```

## Разработка

```bash
npm run dev
```

Приложение будет доступно на `http://localhost:5173`

## Сборка

```bash
npm run build
```

Собранные файлы будут в директории `dist/`

## Переменные окружения

Создайте файл `.env`:

```env
VITE_API_URL=http://localhost:8081
```

## Структура

```
src/
├── components/
│   ├── user/           # Компоненты для клиентов
│   ├── admin/          # Компоненты для операторов/админов
│   └── shared/         # Общие компоненты
├── store/
│   └── useAuthStore.ts # Zustand store
├── types.ts            # TypeScript типы
├── App.tsx             # Главный компонент
├── main.tsx            # Точка входа
└── index.css           # Tailwind CSS
```

## API Endpoints

- `POST /api/v1/auth/telegram/verify` - Аутентификация через Telegram WebApp
- `GET /api/v1/user/profile` - Получение профиля пользователя
- `GET /api/v1/settings` - Получение настроек системы
- `GET /api/v1/orders` - Получение списка заявок
- `GET /api/v1/rates` - Получение текущих курсов

## Интеграция с Telegram

Приложение использует Telegram WebApp SDK для:
- Аутентификации пользователей
- Haptic feedback
- Адаптации под тему Telegram
- Управления viewport

## Роли пользователей

- **client** - обычный пользователь (обмен USDT)
- **operator** - оператор (модерация заявок)
- **admin** - администратор (управление курсами, настройками)
- **super_admin** - суперадминистратор (полный доступ)
