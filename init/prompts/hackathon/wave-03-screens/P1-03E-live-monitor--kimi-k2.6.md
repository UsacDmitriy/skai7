# P1 · LiveMonitorScreen — Живой мониторинг (ВА + телематика)
> 💰 **Бюджет:** читать max 1–3 файла · не читать `./data`, `.venv`, `node_modules` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия. Не запускать параллельно.**
# Модель: moonshotai/kimi-k2.6 · ~$0.062 · Приоритет #1
> ❌ НЕ читать дополнительных файлов — вся спека встроена ниже
> ✅ Передать только: src/types.ts (~1.3K токенов) + этот промпт
> ⚠️ Одна сессия Cherry Studio → один файл

## Контекст продукта (кратко)

SKAI Unified Incident Window — система управления автопарком.
Целевые пользователи: диспетчеры, логисты, служба безопасности.
5 mock-кейсов (инциденты inc-001..inc-005, ТС А777ВВ 77 / В345КМ 97 / Е902СТ 150 / Н124УУ 199 / К451МА 77).
Стек: React 18 + TypeScript + Tailwind + Recharts + Leaflet.

## Файл: code/frontend/src/screens/LiveMonitorScreen.tsx

---

## ДИЗАЙН-СПЕКА (встроена полностью)

# Экран 2 — Живой мониторинг (карта + инциденты онлайн)

## Что рисуем
Главный оперативный экран диспетчерской. Карта с маркерами ТС в реальном времени,
топ-5 рискованных событий слева, детали выбранного инцидента справа.
Тёмная тема — экран работает 24/7 на большом мониторе.

## Layout 1440×900 — тёмная тема

**TOP BAR (48px, bg #0F172A, border-bottom 1px #1E3A8A):**
  Слева: красная точка (8px, пульсирует) + "РИСКОВАННЫЕ ПОЕЗДКИ ОНЛАЙН" (13px bold white uppercase)
  Справа (инлайн, gap 24px):
    ПЕРЕКЛЮЧАТЕЛЬ РОЛИ (тёмный, pill):
      [🏭 Логист] [🛡 Диспетчер ●] [🔒 Безопасность]
      bg: неактивные #1E293B border #334155 | активная bg #3B82F6 text white
      ← Маслов (Балтика): «Логисты используют карту для координации доставки»
    🕐 "00:42:54" (таймер смены, 14px mono white)
    "Активные: 47" + dot-счётчики: 🔴 3 · 🟡 7 · 🟠 12
    "Решено сегодня: 24" (12px #94A3B8)
    "Средн. реакция: 3.2 мин" (12px #94A3B8)

**LEFT PANEL (300px, bg #0F172A, border-right 1px #1E293B):**
  Заголовок: "ТОП-5 РИСКОВАННЫХ ПОЕЗДОК" (10px uppercase #64748B, px-16 py-12)

  5 карточек (gap 8px, px-12px):

  Карточка 1 — ВЫБРАНА (bg #1E293B/50, border-left 4px #3B82F6, border-radius 6px, p-12px):
    "А777ВВ 77" (12px bold white pill #374151) + badge [📹 ВА] (#4C1D95/80 bg, #C4B5FD text, 9px) + "1:08 назад" (11px #64748B, right)
    "Иванов А.П." (12px #94A3B8)
    "🔴 Засыпание за рулём (микросон)" (13px white)
    Чипы: ⚡ "72 км/ч" · 🌙 "Ночь" (bg #1F2937, text #94A3B8, 11px)
    "Score 97" (right, 14px bold white)

  Карточка 2 (border-left 4px #DC2626):
    "В345КМ 97" + badge [⚡📹 Оба] (#052e16/80 bg, #86efac text, 9px) + "3:12 назад"
    "Петров Д.С." | "🔴 Подозрение на ДТП — датчик удара" | "Score 84"

  Карточка 3 (border-left 4px #EA580C):
    "Е902СТ 150" + badge [⚡ Телематика] (#082f49/80 bg, #7dd3fc text, 9px) + "2:26 назад"
    "Сидоров В.Н." | "🟡 Использование телефона" + chip [📷 Нет видео] (#7f1d1d/60, #fca5a5) | "Score 76"

  Карточка 4 (border-left 4px #EA580C):
    "Н124УУ 199" + "1:00 назад"
    "Козлов И.А." | "🟡 Превышение скорости +28 км/ч" | "Score 68" + чип "⚡ 108 км/ч" (красный)

  Карточка 5 (border-left 4px #EAB308):
    "Р788ОО 52" + "1:50 назад"
    "Новиков А.В." | "🟠 Резкое торможение / экстренное ускорение" | "Score 54"

**CENTER (flex-1, карта):**
  Тёмная OSM карта, центр Москва (55.75, 37.62, zoom 12)
  Маркеры (circle 16px, border 2px white, shadow):
    🔴 А777ВВ 77 — выбран, маркер крупнее (20px), кольцо пульсирует
    🔴 В345КМ 97
    🟡 Е902СТ 150 (желтовато-оранжевый)
    🟡 Н124УУ 199
    🟠 Р788ОО 52
  Попап на А777ВВ 77 (белый, radius 8px, shadow-xl, p-12px):
    "А777ВВ 77" (13px bold #0F172A) + badge [📹 ВА] (#EDE9FE, #7C3AED, 10px)
    "Иванов Алексей Петрович" (12px #64748B)
    "Обнаружено засыпание за рулём (микросон)" (12px #0F172A)
    "⚡ 72 км/ч  📍 55.7512, 37.6184" (11px #64748B)
    "1 ТС · 1 объект на карте" (9px #94A3B8) ← важно: не дублируем терминалы
    Крестик ✕ закрыть (right-top)
  Легенда уровня риска (top-right карты, white card):
    ● Критический  ● Высокий  ● Средний
  Легенда источников (под риском, 10px):
    [📹 ВА]  [⚡ Телематика]  [⚡📹 Оба]  [📷 Нет видео]

**RIGHT PANEL (420px, bg #0F172A, border-left 1px #1E293B, overflow-y auto):**

  Секция ВИДЕО (border-bottom 1px #1E293B, p-12px):
    Заголовок строкой: "ДЕТАЛИ ИНЦИДЕНТА" (10px uppercase #64748B) | badge "● REC" красный | "02.04.2026 · 00:36:43" (11px #94A3B8, right)
    Главный видеоплеер (aspect 16:9, bg #000):
      Лейбл top-left: "Cam 1 · фронт" (11px white, bg #0F172A/60)
      Описание снизу overlay: "Обнаружено засыпание за рулём (микросон).
      Голова водителя опустилась ниже уровня руля..." (12px white/70)
    Прогресс-бар под видео: тонкий 4px #1E293B, заполнен 35% #3B82F6
    Таймкоды: "00:50" left | "01:45" right (11px #64748B)
    Ряд миниатюр (3 штуки, gap 6px, mt-6px):
      Cam 2 · салон | Cam 3 · правая | Cam 4 · задняя
      Каждая: aspect 16:9, bg #111827, radius 4px, лейбл снизу 10px

  Табы: [Телеметрия] активна (border-bottom 2px #3B82F6, white) | [Информация] (muted)

  Секция СКОРОСТЬ (p-12px, border-bottom 1px #1E293B):
    Лейбл: "СКОРОСТЬ (КМ/Ч)" (10px uppercase #64748B)
    График 80px высота (bg #0F172A, grid #1E293B, axis #374151):
      X: 21:31:25 → 21:42:45
      Синяя линия скорости: значения ~75-80, пик 90, спад к 65
      Красная пунктирная горизонталь = лимит 80 км/ч

  Секция АКСЕЛЕРОМЕТР (p-12px, border-bottom 1px #1E293B):
    Лейбл: "АКСЕЛЕРОМЕТР (М/С²)" (10px uppercase #64748B)
    График 60px высота:
      Жёлтая линия: колеблется -1...+2, малая амплитуда

  Бейджи-контекст (p-12px, gap 8px, border-bottom 1px #1E293B):
    🟠 "Непрерывное вождение: 2ч 58мин" + иконка ⚠️ (bg #1E293B, text #F59E0B)
    🔵 "Ночная поездка (04:00–07:00)" (bg #1E293B, text #3B82F6)

  Секция ПРОСМОТР АРХИВА (p-12px, border-bottom 1px #1E293B):
    Лейбл: "ПРОСМОТР АРХИВА" (10px uppercase #3B82F6)
    Две превью-карточки рядом (aspect 16:9, bg #111827):
      "CAM-01 · ПЕРЕД" | "CAM-02 ·" (лейблы снизу 10px #94A3B8)
      Таймкоды: "00:36:43" оба
    Слайдер timeline под ними (bg #1E293B, thumb #3B82F6)
    Временные метки: "-15с" | "00:36:43" (center, #94A3B8) | "+15с"
    Кнопки плеера (center, gap 16px): ⏮ ▶ ⏭ (text #94A3B8)

  Кнопки действий (p-12px):
    [📞 Вызов водителя] — bg #16A34A, text white, full-width, h-40px, radius 6px
    Ряд двух: [🔵 Валидация ▾] border #3B82F6 text #3B82F6  |  [🔴 Стоп] border #DC2626 text #DC2626

**BOTTOM BAR (32px, bg #0F172A, border-top 1px #1E293B):**
  Flex row, gap 24px, px-16px, text 11px:
  "● Здоровье системы:" + прогресс-бар 80px (#F59E0B на #1E293B) + "74.6%"
  "📶 На связи: 47/63" (#94A3B8)
  "⚠ Не на связи: 9" (#DC2626) + "(А018КВ7, В123ОЭ7, Е234СТ50 ...)"
  "📷 Неиспр. камер: 7" (#DC2626) + "(А012ХХ77, В678УН97 ...)"

## Стиль
Тёмная тема: bg #0F172A · surface #1E293B · primary #3B82F6 · text white/#E2E8F0
Inter · 1440×900 · Output: React + Tailwind, один файл.

---

## Поведение ролей (Маслов, Балтика)

| Роль | Что видит | Что скрыто |
|------|-----------|-----------|
| 🏭 Логист | Позиция ТС, скорость, статус доставки | DMS/ADAS алармы, Score, детали ВА |
| 🛡 Диспетчер | Все события, видео, телеметрия, заявки | — (полный вид) |
| 🔒 Безопасность | Всё + выделены Score<70 и грубые нарушения | — |

Источник: Маслов (Балтика): «Сделать фильтром — показывать только телематику или только видео.
Логисты используют карту для координации доставки.»


---


### Кнопка перехода в Аналитику (добавить в TOP BAR справа)

```tsx
// В TOP BAR, в ряду справа — добавить кнопку перед таймером:
import { useNavigate } from 'react-router-dom'
const navigate = useNavigate()

// В JSX TOP BAR:
<button
  onClick={() => navigate('/analytics')}
  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg
             bg-[#1E3A8A] text-white text-sm font-medium
             hover:bg-[#1e40af] transition-colors"
>
  📊 Аналитика
</button>
```

Кнопка расположена в TOP BAR справа, рядом с переключателем роли.
При клике → navigate('/analytics') → AnalyticsScreen.

## КОД

### Данные

```ts
import { useState, useEffect } from 'react'
import incidentsData from '../../data/mock/incidents.json'
import liveData from '../../data/mock/live-monitor.json'
import type { Incident } from '../types'

type Role = 'logist' | 'dispatcher' | 'safety'

const incidents = incidentsData.incidents as Incident[]
const [selectedId, setSelectedId] = useState<string>('inc-001')
const [role, setRole] = useState<Role>('dispatcher')
const [elapsed, setElapsed] = useState(2574)

// Фильтрация по роли (Маслов, Балтика)
const visibleIncidents = role === 'logist'
  ? incidents.filter(i => !['DMS_DROWSY', 'DMS_PHONE'].includes(i.alarm_type))
  : incidents

const selected = incidents.find(i => i.id === selectedId) ?? incidents[0]

useEffect(() => {
  const t = setInterval(() => setElapsed(e => e + 1), 1000)
  return () => clearInterval(t)
}, [])

const fmt = (s: number) =>
  `${String(Math.floor(s/3600)).padStart(2,'0')}:${String(Math.floor((s%3600)/60)).padStart(2,'0')}:${String(s%60).padStart(2,'0')}`
```

### Layout — точно по дизайн-спеке выше

Реализуй все 5 зон:
1. TOP BAR — переключатель роли + таймер + счётчики
2. LEFT PANEL (300px) — 5 карточек риска с цветными бордерами
3. CENTER — Leaflet карта, тёмный стиль, маркеры по severity
4. RIGHT PANEL (420px) — видео миниатюры + телеметрия + действия
5. BOTTOM BAR — здоровье системы + статистика

### Acceptance criteria

- Таймер смены тикает каждую секунду
- Роль Логист скрывает DMS_DROWSY и DMS_PHONE события
- Клик карточки → детали в правой панели
- Клик маркера на карте → та же карточка выбирается
- [Открыть карточку] → navigate(`/incident/${selected.id}`)
- Тёмная тема: bg #0F172A, primary #3B82F6
- npm run build без ошибок TypeScript
