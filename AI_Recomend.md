1. Убрать дубли между architecture.md и modules.md
В modules.md убрать раздел "Middleware: порядок выполнения" (он уже в architecture.md). Вместо него — ссылка:
## Middlewares
Порядок и логика — см. `architecture.md#middlewares`.
Список файлов: `app/middlewares/{throttling,db_session,user_middleware,bot_status,role_guard}.py`

2. Убрать Enum trap из modules.md
В modules.md в разделе "Enum-типы (PostgreSQL)" — оставить только:
## Enum-типы
Имена enum в PostgreSQL: `user_role`, `order_type`, `order_status`, `rate_type`.
Правила использования — см. `database.md#enum-типы`.

3. Убрать FSM states из modules.md
Таблица FSM states в modules.md дублирует scenarios.md. Оставить только:
## FSM-модули
`app/fsm/{order,statistics,rate,links,role,support}_states.py`
Детальные сценарии — см. `scenarios.md`.

----

### Принцип 1: Разделить temporal layers
State-документы (описывают текущее состояние, обновляются при изменениях):

    architecture.md — общая архитектура, компоненты, слои, паттерны
    modules.md — структура файлов, слои, конфигурации
    database.md — схема БД, таблицы, индексы, миграции
    scenarios.md — FSM-сценарии (ТОЛЬКО пошаговая логика, без ролей)
    roles.md — матрица прав (ТОЛЬКО права, без FSM-деталей)
    stack.md — технологии (редко меняется)

Plan-документ (что делать):

    roadmap.md — ТОЛЬКО активные задачи ❌. После реализации задача удаляется из roadmap и остаётся только в state-документах + git.

History (что было):

    Git log
    PR / commits
    НЕ status.md (удалить или не обновлять)

### Принцип 2: Single Source of Truth для каждой сущности
Чёткое правило "где описывать что":
Сущность
	
Единственный источник
Архитектурный компонент (bot, worker, DB)
	
architecture.md
Middleware порядок и логика
	
architecture.md (НЕ modules.md)
Структура файлов
	
modules.md (НЕ architecture.md)
Конфиги (Settings, global_settings keys)
	
modules.md
Таблица БД, колонка, индекс
	
database.md
Enum trap (name=)
	
database.md (НЕ modules.md)
FSM пошаговый сценарий
	
scenarios.md
Матрица прав по ролям
	
roles.md
Технологии и версии
	
stack.md
Что делать дальше
	
roadmap.md (только ❌)
Кросс-ссылки вместо повторений: если в modules.md нужно упомянуть Enum trap — поставь ссылку см. database.md, а не копируй пример кода.