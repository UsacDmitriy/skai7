# Claude Design P6 — Экран заявок (TicketsScreen)
> Инструмент: claude.ai/design · System prompt: `00-design-system.md`
> Сохранить: `code/clade_design/Заявки/`

## Дизайн-спека
# Экран 7 — Список заявок и контроль

## Что рисуем
Общая картина по всем инцидентам: KPI + фильтры + таблица.
Диспетчер видит статусы заявок, просроченные — сразу видны красным, переходит к любому событию.

## Данные

**KPI (5 карточек):**
  ТС В ЗОНЕ РИСКА: 4 · КРИТИЧНЫХ: 2 · ВСЕГО ЗАЯВОК: 8 · ПРОСРОЧЕНО: 1 · УСТРАНЕНО: 3

**Таблица (7 строк):**

| ТС / Водитель | Событие | Источник | Видео | Статус | Дедлайн | — |
|---|---|---|---|---|---|---|
| А777ВВ 77 / Иванов А.П. | Засыпание за рулём | 📹 DMS | [▶] | 🔴 Новая | 16.05 | Открыть → |
| В345КМ 97 / Петров Д.С. | Датчик удара | 📡 Телематика | [▶] | 🟡 В работе | 15.05 | Открыть → |
| Е902СТ 150 / Сидоров В.Н. | Использование телефона | 📹 DMS | — | 🟡 В работе | 15.05 | Открыть → |
| Н124УУ 199 / Козлов И.А. | Резкое торможение | 📡 Телематика | [▶] | 🟢 Проверена | — | Открыть → |
| К451МА 77 / Новиков А.В. | Замена водителя | ⚡📹 Оба | [▶] | 🔴 Новая | 16.05 | Открыть → |
| Р788ОО 52 / Тихонов М.С. | Камера офлайн | ⚙ Диагностика | — | 🔴 **Просрочена** | 14.05 | Открыть → |
| Т901ПА 97 / Власов Е.Д. | FCW опасное сближение | 📹 ADAS | [▶] | 🟢 Закрыта | — | Открыть → |

## Layout 1440×900

**SIDEBAR (48px, bg #1E3A8A):**
  Иконки: 🗺 · ⚡ · 📋 (активна, bg #1E40AF) · ⚙

**TOP BAR (56px, white, border-bottom 1px #E2E8F0):**
  "Заявки · 8 событий" (18px bold)
  Справа: [Экспорт CSV] (ghost, border #E2E8F0)

**KPI BAR (border-bottom 1px #E2E8F0):**
  5 карточек flex в ряд, каждая border-right 1px #E2E8F0, px-24px py-16px:
    Число 32px bold #1E3A8A + лейбл 11px uppercase #64748B
    Карточка "ПРОСРОЧЕНО": число #DC2626

**FILTER BAR (p-16px, border-bottom 1px #E2E8F0, flex gap-12px):**
  input placeholder "Поиск по ТС или водителю..." (w-72, border #E2E8F0)
  select "Все статусы" (w-48)
  select "Все источники" (w-48) — варианты: «📹 ВА (DMS/ADAS)» / «⚡ Телематика» / «⚡📹 Оба»

**TABLE (flex-1, overflow-y auto):**
  Thead: bg #F8FAFC, 11px uppercase #64748B, border-bottom 2px #E2E8F0, sticky top
  Строки: border-left 4px severity-color, border-bottom 1px #F1F5F9
  Badges источника в колонке: [📹 ВА] фиолетовый · [⚡ Телематика] голубой · [⚡📹 Оба] зелёный · [⚙ Диагностика] серый
    Severity border: Новая=#DC2626 · В работе=#EA580C · Проверена=#1E3A8A · Закрыта=#16A34A · Просрочена=#DC2626
  Строка "Просрочена": bg #FEF2F2 (вся строка)
  Hover: bg #F8FAFC
  Видео [▶]: кнопка-иконка (border #E2E8F0, radius 4px, p-4px)
  Видео —: текст #CBD5E1 (нет видео)
  "Открыть →": text #1E3A8A, 13px, hover underline

Status badges (inline-flex, radius 12px, px-8px py-2px, 12px):
  Новая:     bg #FEE2E2, text #991B1B
  В работе:  bg #FEF3C7, text #B45309
  Проверена: bg #DBEAFE, text #1E3A8A
  Закрыта:   bg #DCFCE7, text #166534
  Просрочена:bg #FEE2E2, text #991B1B, font-bold

## Стиль
Inter · bg #F8FAFC · primary #1E3A8A · critical #DC2626
1440×900 · Output: React + Tailwind, один файл.


## Промпт
```
Создай standalone HTML "SKAI — Заявки".
bg #F8FAFC, светлая тема, таблица всех инцидентов-заявок.

HEADER white border-b h-14 px-6 flex justify-between items-center:
  "ЗАЯВКИ" 18px bold + "47 всего"
  input "Поиск по ТС или водителю..." border rounded-lg w-64
  select "Все статусы / Новые / В работе / Закрытые"

KPI BAR white border-b px-6 py-3 flex gap-8:
  ТС В РИСКЕ: 7 (28px bold #1E3A8A)
  КРИТИЧНЫХ: 4 (28px bold #DC2626)
  В РАБОТЕ: 12 (28px bold #EA580C)
  ПРОСРОЧЕНО: 3 (28px bold #EA580C)
  ЗАКРЫТО: 24 (28px bold #16A34A)

ТАБЛИЦА (white, 100% width, border-collapse):
  Thead bg #F8FAFC text-xs uppercase text-slate-500 border-b:
    # | ТС / Водитель | Событие | Источник | Видео | Статус | Действие

  Tbody — 7 строк:
  Строка 1: border-l-4 #DC2626 (critical)
    № #001 | В345КМ 97 · Петров Д.С. | 💥 Подозрение на ДТП | COMBINED badge | ▶ Смотреть | [🔴 Критично] | [Открыть →]
  Строка 2: border-l-4 #DC2626
    № #002 | А777ВВ 77 · Иванов А.П. | 😴 Засыпание за рулём | DMS | ▶ Смотреть | [🔴 Критично] | [Открыть →]
  Строка 3: border-l-4 #EA580C
    № #003 | Е902СТ 150 · Сидоров В.Н. | 📱 Использование телефона | DMS | 📷 Нет видео | [🟡 Высокое] | [Открыть →]
  Строки 4-7: HARSH_BRAKING, FCW, DRIVER_SUBSTITUTION, CAMERA_OFFLINE
  
  Hover: bg-slate-50

Tailwind CDN, standalone HTML.
```