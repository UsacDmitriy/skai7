# COMPETITORS — конкурентный анализ единого окна телематики + видеоаналитики

> Исследование 2026-06-10 (веб-источники 2025–2026 + клиентские интервью из `source/`).
> Назначение: маппинг паттернов лидеров рынка на SKAI — что уже есть, что в волнах, что в бэклоге
> (`WAVE-5-BACKLOG.md`). Не контракт; решения фиксируются через `00-CONTRACT.md`/`FEATURES.md`.

## Глобальные лидеры (паттерны для заимствования)

| Вендор | Ключевой паттерн | Маппинг на SKAI | Датасет для полноты |
|---|---|---|---|
| **Lytx** | Human-in-the-loop **очередь верификации событий** (review queue): статусы validated/dismissed, коучинг-воркфлоу по статусам | **Частично**: `POST /incidents/{id}/verify` + `output/actions.csv` есть; полноценной очереди со статусами и KPI очереди нет → **W5-1**; `evidence_rate` (§10) — первый шаг | есть (55 алармов + журнал действий) |
| **Samsara** | Fleet OS (единая платформа), edge-AI алерты в кабине, **коучинг с трекингом эффективности** (повторные нарушения после коучинга) | **Нет** коучинг-цикла → **W5-2** (запрос Оздоева 1-в-1); метрика `recommendation_acceptance` (b25) — зачаток | нужен синтетический `training_assignments` |
| **Netradyne (Driver•i)** | Анализ **100% времени вождения** (не только событий), позитивный скоринг **DriverStar/GreenZone** | **Нет**: SKAI событийно-центричен; «зелёная зона» — KPI Оздоева → **W5-3** | track_points покрывают только окна событий — честное ограничение |
| **Motive** | Телематика + камера в **одном устройстве** (нет проблемы двух терминалов) | Не применимо (SKAI — оркестрация поверх существующих вендоров), но подтверждает боль Маслова: дубли терминалов → проверка `terminal_duplication` (§10.3, **Волна 4.4**) | есть |
| **Verizon Connect** | Интегрированные видеоклипы в карточке события, классификация тяжести | **Есть** (IncidentCard + video ±, severity) | есть |

## Российский рынок (доступные аналоги и среда)

| Игрок | Паттерн | Маппинг на SKAI |
|---|---|---|
| **Wialon (Gurtam)** | Видеомодуль: **карта рядом с видеоплеером**, MDVR-экосистема (Streamax, Howen), запрос файлов с борта | **Есть/частично**: IncidentCard синхронизирует видео↔телеметрию (#1); карта рядом с плеером — паттерн подтверждён |
| **СКАУТ** | Телематика-вендор Фомина (PepsiCo); ДТП-аналитика | Интеграционная цель (Волна 5+, живые коннекторы вместо датасетов) |
| **Montrans Online / Ufin** | **Мультивендорная агрегация** бортовых устройств, дашборды/отчёты | Подтверждает позиционирование SKAI: слой оркестрации, не замена вендоров |
| **ФНИС (АО «ГЛОНАСС», ГОСТЕХ)** | Гос-платформа мониторинга, бесплатно регионам; 2025 — 5 регионов, 2026 — 25+ | Среда/риск: коммерческое окно должно давать то, чего нет в гос-платформе — видеодоказательность, AI-слой, data trust |

## Кросс-референс: клиент ↔ конкурентный паттерн ↔ статус в SKAI

| Клиентский запрос (интервью) | Паттерн лидера | Статус в SKAI |
|---|---|---|
| Фомин: «39 ДТП в телематике, видео подтвердило 5» — нужна доказательная база | Lytx review queue | `evidence_rate` — **Волна 4.4** (§10); очередь — W5-1 |
| Фомин: «скорость видео ≠ CAN; истина — CAN» | (нет прямого аналога — дифференциатор SKAI) | Кросс-сверка скоростей — **Волна 4.4** (#21); CAN-датасет — W5-5 |
| Маслов: «3 ТС видны как 5 точек» (дубли терминалов) | Motive (один девайс), Wialon (группировка) | Дедуп на Мониторе есть (W2.2); проверка `terminal_duplication` — **Волна 4.4** |
| Маслов: рассинхрон online-статусов телематика↔видео | — | W5-5 (нет датасета статусов реального времени) |
| Оздоев: цифровой контур обучения (инцидент→курс→тест 18/20→эскалация при повторе) | Samsara coaching effectiveness, Lytx coaching workflow | W5-2 (нужен датасет) |
| Оздоев: «зелёная зона», позитивная мотивация, геймификация | Netradyne DriverStar/GreenZone | W5-3 / W5-4 |
| Оздоев: превентивный агент здоровья парка | Samsara fleet OS | **Есть** базово: FleetHealth (Волна 3) + forecast (4.1) |

## Выводы для позиционирования MVP

1. **Дифференциатор SKAI — data trust**: ни один RU-доступный игрок не показывает явную кросс-сверку
   источников (скорости, дубли, evidence rate). Волна 4.4 делает это видимым в UI.
2. **Самый короткий путь к паритету с лидерами** — очередь верификации (W5-1): инфраструктура
   (actions, evidence_rate, time_to_triage в b25) уже есть.
3. **Коучинг-цикл — самая монетизируемая фича** (явный запрос Оздоева, флагман Samsara/Lytx), но требует
   нового синтетического датасета — потому Волна 5, не 4.x.
4. SKAI — **слой оркестрации** над СКАУТ/видео-вендорами (как Montrans поверх устройств), не замена.

## Источники

- [Samsara — Fleet FAQ](https://www.samsara.com/guides/fleet-faq) · [Samsara 10-K FY2025](https://www.sec.gov/Archives/edgar/data/0001642896/000164289625000022/iot-20250201.htm) · [Fleet Equipment: Samsara safety outcomes](https://www.fleetequipmentmag.com/samsara-fleet-safety-outcomes/)
- [FleetOwner: Top dash cameras 2025](https://www.fleetowner.com/technology/article/55265084/top-dash-cameras-technology-for-trucking-fleets-in-2025) · [Oxmaint: Best fleet dash cams 2026](https://oxmaint.com/industries/fleet-management/best-fleet-dash-cam-systems-2026-ai-safety-camera) · [BestGuide: Samsara vs Verizon vs Motive 2026](https://bestguide.com/blog/samsara-vs-verizon-connect/)
- [Wialon: видеомодуль](https://wialon.com/en/blog/new-video-module) · [Wialon: video hardware](https://wialon.com/en/gps-hardware/video) · [Wialon × CMSv6](https://wialon.com/en/blog/wialon-cmsv6)
- [Ведомости: мониторинг дорожного движения 2025](https://www.vedomosti.ru/society/articles/2025/12/07/1161228-v-2025-g-trati-regionov-na-monitoring-dorozhnogo-dvizheniya-virosli) · [Минтранс: ИТС итоги 2025 / ФНИС](https://mintrans.gov.ru/press-center/news/12411) · [Минтранс: цифровая платформа мониторинга](https://mintrans.gov.ru/press-center/news/11142)
- [AXENTA: гид по мониторингу 2025](https://axenta.tech/blog/novosti/gid-2025-sistema-monitoringa-transporta-ot-a-do-ya/) · [Ufin: телематика в условиях санкций](https://ufin.online/blog/transportnaya-telematika-v-rossii-v-usloviyah-sankczij-sovremennye-resheniya-i-perspektivy/) · [Montrans](https://montrans.ru/uslugi/gps-monitoring-transporta)
- Интервью клиентов: `source/` (Фомин · PepsiCo, Маслов · Балтика, Оздоев · Газпромнефть-Терминал)
