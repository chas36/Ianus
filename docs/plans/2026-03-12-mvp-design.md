# Ianus MVP — Дизайн платформы расписания

**Дата:** 2026-03-12
**Школа:** ГБОУ Школа №1584 (Москва)

## Цель

Веб-платформа для просмотра и экспорта школьного расписания. Импорт из aSc Timetables XML. Один пользователь (завуч), локальный запуск.

## Стек

- **Backend:** FastAPI (Python) + SQLAlchemy + Alembic
- **Frontend:** React (TypeScript) + Vite
- **Database:** PostgreSQL
- **Инфра:** docker-compose (PostgreSQL + backend + frontend)

## MVP Scope

**Включено:**
- Импорт XML из aSc Timetables (парсинг, upsert в БД)
- Просмотр расписания в виде сетки (дни x уроки)
- Три режима: по классу / по учителю / по кабинету
- Боковая панель со списком сущностей для быстрого переключения
- Экспорт отдельного расписания в Excel и PDF

**Исключено из MVP:**
- Авторизация и роли
- Редактирование расписания (drag & drop)
- Многопользовательская синхронизация и аудит изменений
- Импорт из .roz (парсер готов, подключим позже)
- Telegram-бот
- Алгоритм составления расписания

## Модель данных

### Справочники (из XML)

- **subjects** — id, asc_id, name, short_name
- **teachers** — id, asc_id, name, short_name
- **classes** — id, asc_id, name, short_name
- **rooms** — id, asc_id, name, short_name

### Расписание

- **lessons** — id, asc_id, subject_id, teacher_id, class_id, group_name, periods_per_week
- **cards** — id, lesson_id, room_id, day (1-5), period (1-10)

### Мета

- **imports** — id, filename, imported_at, source_format

Связь: один lesson -> несколько cards (например, "алгебра 3ч/нед" = 3 записи card с разными day+period).

`asc_id` — оригинальный GUID из XML для повторного импорта без дублирования.

## API

### Импорт

- `POST /api/import/asc-xml` — загрузка XML файла, парсинг, upsert в БД

### Просмотр

- `GET /api/classes` — список классов
- `GET /api/teachers` — список учителей
- `GET /api/rooms` — список кабинетов
- `GET /api/timetable/class/{id}` — расписание класса (сетка 5x10)
- `GET /api/timetable/teacher/{id}` — расписание учителя
- `GET /api/timetable/room/{id}` — расписание кабинета

### Экспорт

- `GET /api/export/class/{id}?format=xlsx|pdf`
- `GET /api/export/teacher/{id}?format=xlsx|pdf`
- `GET /api/export/room/{id}?format=xlsx|pdf`

Timetable-эндпоинты возвращают массив 5 дней x 10 уроков. В каждой ячейке: предмет, учитель, кабинет, группа (или пусто).

## Фронтенд

### Верхняя панель
- Переключатель режимов: Классы | Учителя | Кабинеты
- Кнопки: Импорт XML | Экспорт Excel | Экспорт PDF

### Боковая панель (слева)
- Режим "класс": классы по параллелям (5-е, 6-е, 7-е...)
- Режим "учитель": алфавитный список
- Режим "кабинет": список кабинетов

### Основная область — сетка
- Колонки: Понедельник — Пятница
- Строки: уроки 1-10 с временем (8:30-18:05)
- Ячейка в режиме "класс": предмет + учитель + кабинет
- Ячейка в режиме "учитель": предмет + класс + кабинет
- Ячейка в режиме "кабинет": класс + предмет
- Цветовая кодировка по предметам/классам

## Структура проекта

```
Ianus/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── routers/
│   │   │   ├── import_router.py
│   │   │   ├── timetable.py
│   │   │   └── export.py
│   │   ├── services/
│   │   │   ├── asc_xml_parser.py
│   │   │   └── export_service.py
│   │   └── alembic/
│   ├── requirements.txt
│   └── alembic.ini
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── TimetableGrid.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── TopBar.tsx
│   │   │   └── ImportDialog.tsx
│   │   ├── api/
│   │   └── types/
│   ├── package.json
│   └── vite.config.ts
├── export_file/
│   └── roz_parser.py
└── docker-compose.yml
```

## Будущие фазы

- **Фаза 2:** Авторизация, роли (завуч/учитель), многопользовательская работа, аудит изменений
- **Фаза 3:** Редактирование расписания (drag & drop), валидация конфликтов
- **Фаза 4:** Импорт из .roz и других форматов, Telegram-бот
- **Фаза 5:** Алгоритм составления расписания (интеграция FET)
