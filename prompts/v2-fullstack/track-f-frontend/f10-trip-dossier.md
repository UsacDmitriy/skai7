# f10 · Видеодосье рейса (идея #7)

> Трек **Frontend**. Против `00-CONTRACT.md` §7.4 (`GET /api/trips/{id}`), §7.5 (`TripDossier`),
> §7.8 (AC «Видеодосье»). **Владеет:** `web/src/pages/TripDossier.tsx`. Использует примитивы карты d4
> (`@/components/map`: `MapView`, `MarkerLayer`), таймлайн d5 (`@/components/ui/Timeline`), UI-примитивы
> d2 (`Button`, `SeverityBadge`, `VideoPlayer`, `TelemetryChart`) и API-клиент f2.

## Цель

Собрать «досье рейса» как единое полотно: маршрут ТС на карте + хронология событий рейса (таймлайн) +
скорость за рейс. Клик по событию таймлайна / точке трека → видео именно этого момента. Это идея #7:
расследование рейса без переключения между разными инструментами.

## TripDossier.tsx

Маршрут `/trip/:id`. Данные — `client.getTrip(id)` →
`TripDossier { vehicle_plate, track: TelemetryPoint[], timeline: {ts_offset, alarm_code, label, has_video}[] }`.

Раскладка (двухколоночная: карта/таймлайн слева, видео+график справа):
- **Шапка**: `vehicle_plate`, водитель (если есть из enrichment), длительность/диапазон рейса.
- **Карта рейса** (`MapView` d4): трек строим из координат точек (`track[].lat/lon` — если в схеме нет
  координат на точку, используем последовательность; уточнить с b13). Линия трека `#1E3A8A` (токен d5),
  точки событий = `MarkerLayer` с цветом по severity, t=0 — critical-маркер. Клик по точке трека →
  выбрать ближайшее событие.
- **Timeline событий** (`Timeline` d5): элементы из `timeline[]`: `ts_offset`, `label` (`alarm_label_ru`),
  цвет точки по severity, иконка 📹 если `has_video=true`. Клик по событию → выбрать момент.
- **Видео момента** (`VideoPlayer`): для выбранного события (`videoUrl(id, channel)`); если `has_video=false`
  — placeholder. ADAS (ch1) по умолчанию, переключатель на DMS (ch5).
- **График скорости за рейс** (`TelemetryChart`) по `track[]`: ось — `ts_offset`, маркер выбранного
  события. Клик по графику синхронизирует выбор с картой и таймлайном.
- Единый «выбранный момент» (`selectedOffset`) синхронизирует карту ↔ таймлайн ↔ видео ↔ график.
- Состояния loading / error / 404.

## Зависимости и параллелизм

- **Опирается на:** d4 (`MapView`/`MarkerLayer`), d5 (`Timeline` + токены track-line/event-dot/t=0),
  d2 (`VideoPlayer`/`TelemetryChart`/`Button`), f2-клиент.
- **f2/x2:** f2-клиент дополняется методом `getTrip(id) → TripDossier` (тип `TripDossier` в `types.ts`
  пополю по §7.5). Маршрут `/trip/:id` добавляется в `App.tsx` (зона f1/x2).
- **Бэк:** `GET /api/trips/{id}` (b13). До готовности — фикстуры f3 (`VITE_USE_FIXTURES=true`).
- **Можно параллелить** с f9/f11/f12/f13: отдельная страница, пересечения только в `App.tsx` и
  `client.ts`/`types.ts`. Делит карту-примитив d4 с f6/f11 (общий компонент, не файл) — согласовать API d4.

## Check

- `/trip/:id` рендерит карту с треком, таймлайн событий, видео и график скорости.
- Клик по точке трека, по событию таймлайна и по графику выбирает один и тот же момент (синхронизация).
- Для события с `has_video=true` показывается видео момента; с `false` — placeholder.
- Переключение ADAS/DMS меняет `channel` в `videoUrl`.
- Работает на живом API и на фикстурах (`VITE_USE_FIXTURES=true`).
- `npm run typecheck` проходит; `TripDossier` совпадает с §7.5 пополю.
