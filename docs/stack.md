# Технологический стек

> **SSOT:** Этот документ — единственный источник истины для технологий и их версий.
> Структура файлов — см. `modules.md`. Архитектура — см. `architecture.md`.

---

## Основные технологии

| Технология | Версия | Роль в проекте |
|-----------|--------|----------------|
| Python | 3.11+ | Основной язык. Async/await, type hints, богатая экосистема. |
| Aiogram | 3.15.x | Telegram Bot фреймворк. Long Polling, FSM, middleware, роутинг, inline-клавиатуры. |
| SQLAlchemy | 2.0.x | ORM и запросы. Асинхронный режим (`sqlalchemy[asyncio]`), typed mapping (`Mapped[]`). |
| asyncpg | 0.30.x | Асинхронный драйвер PostgreSQL. Работает со SQLAlchemy async engine. |
| PostgreSQL | 15-alpine | Реляционная СУБД. JSONB, индексы, транзакции. Образ alpine — минимальный размер. |
| Redis | 7-alpine | Кеш (DB 0) и очередь задач ARQ (DB 1). TTL 30 сек для флагов. |
| ARQ | 0.26.x | Асинхронная очередь задач на Redis. Retry, max_tries, job timeout. |
| aiohttp | 3.x | REST API фреймворк. HTTP-сервер для внешнего доступа. |
| PyJWT | 2.x | JWT аутентификация для REST API. Access + refresh токены. |
| Pydantic Settings | 2.7.x | Конфигурация из `.env`. Валидация типов, значения по умолчанию. |
| Cryptography | 44.0.x | AES-256-CBC шифрование реквизитов. IV генерируется случайно, prepend к ciphertext. |
| Alembic | 1.14.x | Миграции БД. Управление схемой PostgreSQL. |
| Docker | — | Контейнеризация. Изоляция компонентов. |
| Docker Compose | 3.9 | Оркестрация. Зависимости, healthcheck, volumes. |
| uv | latest | Менеджер пакетов Python (замена pip/poetry). Быстрая установка зависимостей. |
| React | 18.x | Frontend библиотека для Web3 Telegram Mini App. |
| Vite | 5.x | Сборщик frontend проекта. Быстрый HMR и билд. |
| @twa-dev/sdk | 7.x | Telegram Web App SDK для интеграции с клиентом Telegram. |

---

## Зависимости разработки

| Технология | Версия | Роль |
|-----------|--------|------|
| pytest | 8.3.x | Фреймворк тестирования |
| pytest-asyncio | 0.24.x | Async-тесты. Режим `auto` |
| pytest-cov | 6.0.x | Покрытие кода (`--cov=app --cov-report=term-missing`) |
| aiosqlite | 0.20.x | In-memory SQLite для тестов вместо PostgreSQL |
| ruff | 0.8.x | Линтер + форматтер. Правила: E, F, I, N, W, UP. Target: Python 3.11, line-length 120 |

---

## Выбор технологий: обоснование

### Long Polling вместо Webhook

Webhook требует публичного HTTPS-эндпоинта и веб-сервера (FastAPI). Long Polling проще на одном VPS, не требует открытия портов. Окно ~30 сек возможной потери обновлений при перезапуске — допустимо для MVP.

### AES-256-CBC для реквизитов

Шифрование на уровне приложения позволяет хранить в БД зашифрованный текст. Ключ — в `.env`, не в коде. При компрометации БД реквизиты защищены.

### ARQ вместо Celery

ARQ легче, работает на Redis (уже используется для кеша), полностью асинхронный. Celery избыточен для 2 задач и требует RabbitMQ.

### SQLAlchemy 2.0 с typed mapping

`Mapped[]` и `mapped_column()` — типобезопасность моделей и автодополнение в IDE. Асинхронный режим не блокирует event loop.

### Pydantic Settings

Единая точка конфигурации: валидация при старте. Ошибка в `.env` — немедленный сбой с понятным сообщением.

---

## См. также

- **Архитектура:** `architecture.md`
- **Структура файлов:** `modules.md`
- **Установка и запуск:** `quickstart.md`
