# f12 · Виджет детекции саботажа камеры (идея #9)

> Трек **Frontend**. Против `00-CONTRACT.md` §7.4 (`GET /api/sabotage`), §7.5 (`SabotageEvent`),
> §7.8 (AC «Саботаж»). **Владеет:** `web/src/components/SabotageWidget.tsx` + встраивание секции в
> `Report.tsx` (f7) и `Monitor.tsx` (f6). Использует UI-примитивы d2 (`@/components`: `Card`, `Button`,
> `SeverityBadge`, `VideoPlayer`) и API-клиент f2.

## Цель

Связка видео + телематики детектирует саботаж: DMS-камера даёт тёмный/однотонный кадр (закрыта), а
телематика показывает движение (`speed_kmh > 0`). Идея #9: вынести такие события отдельным виджетом —
тёмный DMS-кадр рядом со скоростью движения как доказательство, плюс быстрые действия. Это переиспользуемый
**компонент** (виджет), а не отдельный маршрут — встраивается в Report и Monitor.

## SabotageWidget.tsx

Данные — `client.getSabotage()` → `SabotageEvent[]`, где
`SabotageEvent { id, vehicle_plate, ts, dms_dark: bool, speed_kmh: float, driver_name, video_url }`.

Виджет:
- **Заголовок** секции: «Камера заблокирована · подозрение на саботаж» + счётчик событий за период.
- **Список** `SabotageEvent[]` — карточки (`Card`), каждая:
  - **Тёмный DMS-кадр**: `VideoPlayer`/превью по `video_url` с оверлей-меткой «DMS перекрыта» (когда
    `dms_dark=true`).
  - **Корреляция-доказательство**: рядом крупно `speed_kmh` км/ч с подписью «машина едет» —
    тёмный кадр + скорость>0 = ключевой инсайт.
  - **Кто/когда**: `driver_name`, `vehicle_plate`, `ts`.
  - **Кнопки** (через `client.postAction`): `[Создать заявку]` → `postAction({incident_id:id,
    action:"create_task"})`, `[Уведомить HR]` → `postAction({action:"create_task", comment:"notify_hr"})`
    (отдельного action-типа в §3.4 нет — помечаем через comment; TODO-маркер на согласование с b13).
- **Пустое состояние**: «Саботаж не обнаружен».
- Состояния loading / error.

### Встраивание

- В `Report.tsx` (f7) — отдельная секция/вкладка «Саботаж» (KPI + список).
- В `Monitor.tsx` (f6) — компактная панель-сводка (счётчик + последние события, клик разворачивает).
- Виджет не владеет этими страницами — только экспортирует `<SabotageWidget />`; f6/f7 импортируют.

## Зависимости и параллелизм

- **Опирается на:** d2 (`Card`/`Button`/`SeverityBadge`/`VideoPlayer`), f2-клиент.
- **f2/x2:** f2-клиент дополняется методом `getSabotage() → SabotageEvent[]` (тип `SabotageEvent` в
  `types.ts` пополю по §7.5). Маршрут не нужен — виджет встраиваемый.
- **Бэк:** `GET /api/sabotage` (b11, `v_sabotage`). До готовности — фикстуры f3 (`VITE_USE_FIXTURES=true`).
- **Можно параллелить** с f9/f10/f11/f13: владеет только `SabotageWidget.tsx`. Встраивание в `Report.tsx`/
  `Monitor.tsx` координируется с f7/f6 (одна точка вставки import — согласовать, чтобы не перетереть).

## Check

- `SabotageWidget` рендерит список с тёмным DMS-кадром + значением `speed_kmh` для каждого события.
- Метка «DMS перекрыта» показывается при `dms_dark=true`.
- Кнопки «Создать заявку» / «Уведомить HR» шлют `POST /api/actions`.
- Пустое состояние при отсутствии событий.
- Виджет встроен и виден в `/report` и `/monitor`.
- Работает на живом API и на фикстурах (`VITE_USE_FIXTURES=true`).
- `npm run typecheck` проходит; `SabotageEvent` совпадает с §7.5 пополю.
