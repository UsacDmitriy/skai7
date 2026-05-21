# Волна 00a-C — Design Tokens
> 🤖 **Модель: `qwen/qwen3-coder:free`** | извлечение цветов → constants.ts
> 💰 **Контекст:** прикрепить verify-standalone.jpg как image (~$0)
> ❌ НЕ передавать HTML-файлы (1.9MB = $0.35 за чтение)
> ⚠️ Можно запускать одновременно с 00a-B (разные сессии Cherry Studio)

## Что передать в сессию

**Прикрепить как image** (не текстом!):
`code/clade_design/Интерактивнй отчет/verify-standalone.jpg`

Это скриншот финального результата (14KB). Qwen3 Coder Vision видит цвета напрямую.

---

## Промпт

```
На изображении — экран SKAI (система управления автопарком).
Это готовый дизайн: тёмная тема, цветовая индикация событий.

Задача: создать src/constants.ts на основе визуального дизайна.

Извлеки из изображения:
- Основные цвета фона, поверхностей, бордеров
- Цвет текста (основной и приглушённый)
- Цвета состояний: критический (красный), предупреждение (оранжевый), норма (зелёный), офлайн (серый)
- Цвета для графиков (линии, оси)
- Font-family если определяется визуально

Напиши src/constants.ts:

export const COLORS = {
  bg: '#...',           // основной фон
  surface: '#...',      // фон карточек/панелей
  border: '#...',       // бордеры
  text: {
    primary: '#...',
    muted: '#...',
  },
  critical: '#...',     // DMS_DROWSY, CRASH_SENSOR — красный
  warning: '#...',      // HARSH_BRAKING — оранжевый
  ok: '#...',           // норма — зелёный
  offline: '#...',      // камера offline — серый
  chart: ['#...', '#...', '#...', '#...'],
} as const

export const ALARM_TYPE_LABELS: Record<string, string> = {
  DMS_DROWSY: 'Засыпание за рулём',
  CRASH_SENSOR: 'Датчик удара',
  DMS_PHONE: 'Использование телефона',
  HARSH_BRAKING: 'Резкое торможение',
  DRIVER_SUBSTITUTION: 'Замена водителя',
}

export const STATUS_LABELS: Record<string, string> = {
  new: 'Новое',
  in_progress: 'В работе',
  closed: 'Закрыто',
  pending: 'Ожидает',
}

export const STATUS_COLORS: Record<string, string> = { ... }

export const SPEED_LIMIT_KMH = 60
export const DROWSY_THRESHOLD_MIN = 120

Только код. Без объяснений.
```
