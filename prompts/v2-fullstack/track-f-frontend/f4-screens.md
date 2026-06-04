# f4 · Экраны (Карточка инцидента сквозь API; Монитор/Отчёт — scaffold)

> Трек **Frontend**. Против `00-CONTRACT.md` §3. **Владеет:**
> `web/src/pages/IncidentCard.tsx`, `web/src/pages/Monitor.tsx`, `web/src/pages/Report.tsx`.
> Использует UI-примитивы d2 (`@/components`) и API-клиент f2. Референсы вёрстки — HTML-мокапы:
> `ui/Карточка инцидента/`, `ui/Промпт_2_Живой мониторинг /`, `ui/Интерактивнй отчет/` (+ `wave-03-screens/**`).

## Цель

Собрать экраны из примитивов d2 на данных f2-клиента. **P0 — «Карточка инцидента» полностью** (сквозной flow); Монитор и Отчёт — вёрстка-scaffold на списке/фикстурах без полного wiring.

## IncidentCard.tsx (P0, end-to-end)

Маршрут `/incidents/:id`. Через `client.getIncident(id)` (+ `getTelemetry`):
- **Топбар инцидента**: тип (`alarm_label_ru`), `SeverityBadge`, `ScoreBar(risk_score)`, источник (`source`, в т.ч. «Оба»/COMBINED), ТС/водитель (+`driver_region`, `driver_safety_score`)/время/адрес.
- **Блок причины**: `evidence_summary` + **«версия события · уверенность `confidence`%»** (`event_version`).
- **Два видео** (`VideoPlayer`): `cam_front_url` (ADAS) и `cam_dms_url` (DMS); доп. каналы из `cam_extra[]` («Другие камеры»). Если `video_available=false` — пустое состояние + «Запросить архив»; показать окно offline (`Camera.offline_from/to`) и `sensor_active_after_sec` («DMS-сенсор работал +N сек»).
- **График телеметрии** (`TelemetryChart`) по `telemetry[]`, статичный маркер события x=0 (акселерометр `ax` — производная скорости, не плоский ноль).
- **Синхронизация видео↔телеметрия (idea #1, §6):** экран хранит `currentSec` (из `VideoPlayer.onTimeUpdate`) и
  передаёт его как `playheadOffset` в `TelemetryChart` — движущаяся вертикаль идёт за воспроизведением. Оба плеера
  (ADAS+DMS) синхронны: `seekTo`/play общие; клик по графику → `seekTo` на обоих. Это ключевой демо-эффект.
- **Статусы камер** (`cameras[]`) — online/offline/**warning** («Нестабильна»).
- **Панель действий** (`Button`): «Проверено» (`mark_reviewed`) / «Создать заявку» (`create_task`) / «Запросить архив» (`request_archive`) / «Позвонить водителю» (`call_driver`) / **«Валидация»** (`validate`) / **«Стоп ТС»** (`stop_vehicle`) → `client.postAction(...)`.
- Состояния loading/error/404.

Покрыть оба кейса из идеи #1: «есть видео» (датчик удара 54→0) и «нет видео» (телефон, камера offline).

## Monitor.tsx (scaffold)

Маршрут `/monitor`. Лента инцидентов из `client.listIncidents()` — список `Card(variant=incident)` с
severity-border, сортировка по `ts`/`risk_score`, фильтры по severity/source. Клик → `/incidents/:id`.
Карта/таймлайн — заглушка-плейсхолдер с `# TODO`. Референс — `ui/Промпт_2_Живой мониторинг /`.

## Report.tsx (scaffold)

Маршрут `/report`. Поле NL-запроса + кнопка → `client.queryReport(text)`; рендер `DriverReport`/`FleetReport`
(KPI-плашки + `DataTable` нарушений). Клик по строке → видео справа (killer-feature idea #2) — выезжающая
панель с `VideoPlayer`. Голосовой ввод — кнопка-заглушка `# TODO Whisper`. Референс — `ui/Интерактивнй отчет/`.

## Check

- `/incidents/:id` рендерит карточку на живом API (после `make db`+бэк) и на фикстурах (`VITE_USE_FIXTURES=true`).
- Кейс «нет видео» показывает пустое состояние и «Запросить архив».
- Действия пишутся (`POST /api/actions`), статус инцидента обновляется.
- `/monitor` и `/report` открываются без ошибок (scaffold).
