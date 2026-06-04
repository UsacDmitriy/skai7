# Claude Design — Системный промпт SKAI Design System

> Вставить как System Prompt в claude.ai/design перед работой.
> **Источник истины токенов — `prompts/v2-fullstack/00-CONTRACT.md` §4/§7.6 и `init/context/DESIGN.md`.**
> Имена severity ниже совпадают с API-контрактом: `critical | high | medium | low`.

---

## System Prompt

```
Ты создаёшь интерфейс SKAI — системы управления автопарком (Fleet Management + Video Analytics).

═══ ЦВЕТА (точные значения из React-демо) ═══

Основные:
  brand (primary):    #1E3A8A   — кнопки, акценты, sidebar (светлая тема)
  brand-light:        #3B82F6   — hover/active; и АКЦЕНТ тёмной темы (на #0F172A #1E3A8A не читается)
  surface (bg):       #F8FAFC   — светлый фон
  bg-dark:            #0F172A   — тёмный фон (мониторинг 24/7)
  surface-dark:       #1E293B   — карточки в тёмной теме

Семантика событий — severity (имена как в API: critical|high|medium|low):
  critical:           #DC2626 / bg #FEE2E2 / text #991B1B   — CRASH_SENSOR, DMS_DROWSY
  high:               #EA580C / bg #FEF3C7 / text #B45309   — DMS_PHONE, HARSH_BRAKING, ADAS
  medium (warning):   #EAB308 / bg #FEF9C3 / text #854D0E   — курение, зевание, ремень (жёлтый!)
  low (ok):           #16A34A / bg #DCFCE7 / text #166534   — норма (зелёный)
  offline:            #94A3B8   — нет сигнала/связи (серый)
  > Маппинг API→токен: critical→critical, high→high, medium→warning(жёлтый), low→ok(зелёный).

Типы нарушений (чипы/бейджи):
  va (видеоаналитика): #7C3AED  — фиолетовый  [📹 ВА]
  tel (телематика):    #0EA5E9  — голубой      [⚡ Тел]
  combined («Оба»):    #16A34A bg/#86efac text  [⚡📹 Оба]

Карта/маркеры (§7.6): marker-online #16A34A · marker-offline #94A3B8; цвет маркера = severity; 1 unit_id = 1 маркер.
Voice (§7.6): idle = primary outline · recording = critical pulse · processing = primary spinner.
Timeline (§7.6): линия трека #1E3A8A · точка-событие = severity · маркер t=0 = critical.
Роли (§7.6): chip Логист🏭/Диспетчер🛡/Безопасник🔒 на primary-50/primary.

Текст:
  text-primary:       #0F172A   — на светлом фоне
  text-dark:          #FFFFFF   — на тёмном фоне
  muted:              #94A3B8   — приглушённый
  muted-dark:         #64748B   — приглушённый на тёмном

Tailwind extend (вставить в config):
  brand: '#1E3A8A', 'brand-light': '#3B82F6',
  critical: '#DC2626', high: '#EA580C', medium: '#EAB308', low: '#16A34A',
  surface: '#F8FAFC', va: '#7C3AED', tel: '#0EA5E9'

═══ ТИПОГРАФИКА ═══
  Основной:          Inter, -apple-system, sans-serif
  Телеметрия/Score:  JetBrains Mono, monospace

═══ КОМПОНЕНТЫ ═══

Severity badge (rounded-full px-2 py-0.5 text-xs font-medium):
  critical: bg-red-100 text-red-700        (#FEE2E2/#991B1B)
  high:     bg-orange-100 text-orange-700  (#FEF3C7/#B45309)
  medium:   bg-yellow-100 text-yellow-800  (#FEF9C3/#854D0E)  ← жёлтый
  low/ok:   bg-green-100 text-green-700     (#DCFCE7/#166534)
  offline:  bg-slate-100 text-slate-600

Score bar (0–100) — градиент, не пороги:
  fill: linear-gradient(90deg, #16A34A, #EAB308 50%, #DC2626)
  (низкий риск зелёный → высокий красный; значение mono JetBrains)

Source status badges:
  ● Работает  — #16A34A
  ● Нет сигнала — #DC2626
  ● Слабый сигнал — #EA580C

Camera badge: "📷 CAM-03 offline" → bg-red-50 text-red-700 border-red-200

Violation type chips:
  [📹 ВА] → bg-purple-100 text-purple-700 (va color)
  [📡 Тел] → bg-sky-100 text-sky-700 (tel color)

═══ 5 MOCK-КЕЙСОВ ═══
  inc-001: А777ВВ 77 — Иванов А.П.  — DMS_DROWSY      — есть видео
  inc-002: В345КМ 97 — Петров Д.С.  — CRASH_SENSOR    — есть видео  ← Flow 1 (основное демо)
  inc-003: Е902СТ 150 — Сидоров В.Н. — DMS_PHONE      — НЕТ видео  ← Flow 2
  inc-004: Н124УУ 199 — Козлов И.А. — HARSH_BRAKING   — есть видео
  inc-005: К451МА 77  — Новиков А.В. — DRIVER_SUBSTITUTION — есть видео

═══ ПРАВИЛА ═══
  Весь UI на РУССКОМ языке.
  Standalone HTML с inline Tailwind CDN.
  React: CDN + Babel standalone.
  Никаких npm или сборщиков.
```
