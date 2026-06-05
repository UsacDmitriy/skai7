# f9 · Dispatch Alert — алерт критического алярма (идея #5)

> Трек **Frontend**. Против `00-CONTRACT.md` §7.4 (`GET /api/alerts/{id}`), §7.5 (`DispatchAlert`),
> **Модель:** 🔴 Opus — высокие ставки: интеграция / синк / алгоритм / анти-регресс / killer-feature / барьер.
> §7.8 (AC «Dispatch alert»). **Владеет:** `web/src/pages/DispatchAlert.tsx` (рендерится как модал
> поверх текущего экрана). Использует UI-примитивы d2 (`@/components`: `Button`, `SeverityBadge`,
> `VideoPlayer`, `TelemetryChart`) и API-клиент f2.

## Цель

При критическом алярме (`auto_request_video=true` из `alarm_type_catalog`) диспетчер должен получить
немедленный алерт **поверх** рабочего экрана: видео момента ±15 с + телеметрия момента + быстрые
действия — не теряя контекст того, чем он занят. Это «push»-сценарий идеи #5: система сама запросила
видео, человек подтверждает или отклоняет.

## DispatchAlert.tsx

Маршрут `/alert/:id` (открывается как overlay-модал поверх фона, фон **не блокируется** — затемнение
полупрозрачное, под ним виден предыдущий экран; Esc / клик по фону = «Всё в порядке»). Данные —
`client.getAlert(id)` → `DispatchAlert { incident: IncidentDetail, video_window_sec=15, requested_at }`.

Содержимое модала:
- **Шапка**: `SeverityBadge(critical)`, `alarm_label_ru`, плашка «🔴 Автозапрос видео · {requested_at}»,
  ТС (`vehicle_plate`) / водитель (`driver`) / время (`ts`).
- **Видео ±15 с**: два `VideoPlayer` (`videoUrl(id,1)` ADAS + `videoUrl(id,5)` DMS); окно
  `video_window_sec` показать как подпись «±15 с от момента». Если `video_available=false` —
  placeholder + «Запросить архив».
- **Телеметрия момента**: компактный `TelemetryChart` по `incident.telemetry[]` с маркером t=0
  (скорость в момент алярма крупно рядом, `speed_kmh`).
- **3 кнопки действий** (через `client.postAction`):
  - `[Позвонить водителю]` → `postAction({incident_id, action:"call_driver"})`, состояния idle/connecting/active.
  - `[Создать заявку]` → `postAction({action:"create_task"})`, после успеха — тост + закрыть.
  - `[Всё в порядке]` → `postAction({action:"mark_reviewed"})`, закрыть модал (вернуться на фон).
- Состояния loading / error / 404.

> UX: модал не должен «красть» весь экран навсегда — закрытие всегда возвращает к фоновому маршруту.
> Несколько алертов подряд — очередь (показываем по одному, следующий после закрытия). Без `Date.now()`
> в логике — время берём из `requested_at`/`ts`.

## Зависимости и параллелизм

- **Опирается на:** d2 (`VideoPlayer`/`TelemetryChart`/`Button`/`SeverityBadge`), f2-клиент.
- **f2/x2:** f2-клиент дополняется методом `getAlert(id) → DispatchAlert` (тип `DispatchAlert` в `types.ts`
  пополю по §7.5). Маршрут `/alert/:id` добавляется в `App.tsx` (зона f1/x2) как overlay-route.
- **Бэк:** `GET /api/alerts/{id}` (b13). До готовности — фикстуры f3 (`VITE_USE_FIXTURES=true`).
- **Можно параллелить** с f10–f13: общих файлов нет (отдельная страница-модал). Пересечения только в
  `App.tsx` (роуты) и `client.ts`/`types.ts` — согласовать с f1/f2.

## Check

- `/alert/:id` открывается как overlay; фоновый экран виден и не размонтируется.
- Esc и клик по фону = действие «Всё в порядке» (mark_reviewed) и закрытие.
- При `video_available=true` — два плеера с подписью «±15 с»; при `false` — placeholder + «Запросить архив».
- `TelemetryChart` рисует момент с маркером t=0.
- Все 3 кнопки шлют корректный `POST /api/actions` (`call_driver` / `create_task` / `mark_reviewed`).
- Работает и на живом API (`make db` + бэк), и на фикстурах (`VITE_USE_FIXTURES=true`).
- `npm run typecheck` проходит; `DispatchAlert` совпадает с §7.5 пополю.
- **Неизвестный `id`** (`GET /api/alerts/{id}` → 404) → состояние «Алерт не найден» внутри модала
  (заголовок + «Закрыть»), а не белый экран/краш; на фикстурах несуществующий id ведёт себя так же.
- **loading** → скелетон шапки/видео-зон; **error** (сбой сети ≠ 404) → плашка + «Повторить».
- **Нет видео-окна** (`video_available=false`) → плашка-placeholder + «Запросить архив» вместо плееров
  (без битых `<video>`); подпись «±15 с» скрыта.
- **a11y модала**: `role="dialog"` + `aria-modal`, `aria-labelledby` на заголовок, фокус-трап,
  автофокус на первой кнопке, Esc = «Всё в порядке»; возврат фокуса на триггер после закрытия.
- **a11y кнопок**: 3 действия — доступные `<button>` с текстом (не только иконка), `aria-busy` в
  состояниях `connecting`/отправки; «Позвонить водителю» отражает idle/connecting/active текстом.
- **Локаль времени**: `requested_at`/`ts` форматируются через util локали/таймзоны (без `Date.now()`).

## Состояния и edge-cases

- **loading** → скелетон; **error** (≠404) → «Повторить»; **404 / неизвестный id** → «Алерт не найден»
  (§7.8/Edge #5), закрытие возвращает на фон.
- **Нет видео** (`video_available=false`) → placeholder + «Запросить архив», подпись «±15 с» не рисуется.
- Esc/клик по фону = `mark_reviewed` и закрытие; фон не размонтируется; очередь алертов — по одному.
- Живой API и фикстуры (`VITE_USE_FIXTURES=true`); `npm run typecheck` зелёный.
