# План выполнения

> Действующий план разработки — каталог `prompts/v2-fullstack/`.
> Источник истины — `prompts/v2-fullstack/00-CONTRACT.md`. Каждый агент кодит против контракта,
> а не против рантайма соседа — поэтому треки идут параллельно.
> (Старая wave-00..05 React-only последовательность и её arch-документы удалены.)

---

## Phase 0 — project-scoped ClinePass MCP (owner-only gate)

До подготовки и любой implementation wave владелец Claude/Codex обязан:

1. Проверить canonical bridge package
   `tools/clinepass-mcp/{server.py,test_server.py,models.env,.env.example,README.md}`;
   exact model slugs и route mappings хранятся только в `models.env`, credentials и
   transport overrides — только в ignored `.env`.
2. Проверить tracked Claude registration в `.mcp.json`; для Codex — слить только
   `[mcp_servers.clinepass]` из `.codex/config.toml.example` в локальный config, не
   перезаписывая пользовательские настройки и не добавляя secrets.
3. Запустить unit tests, `server.py --selftest`, Python compilation, JSON/TOML parsing,
   прямые MCP stdio `initialize` и `tools/list`.
4. Вызвать `clinepass_config`, `clinepass_list_models` с явным registry fallback при
   недоступном endpoint, `clinepass_audit_reset` и `clinepass_audit_report`.
5. Зафиксировать privacy boundary: ClinePass не получает credentials, private/production
   data, private media, unrestricted raw corpora, privileged configuration или
   unrestricted repository context. Нельзя молча переключаться на другого provider.
6. Проверить model family allowlist: разрешены только семейства Kimi, DeepSeek, Qwen и
   GLM. Любой другой alias или slug отклоняется при загрузке registry, неизвестный или
   запрещённый alias/route падает с ошибкой без скрытого fallback, а новая объявленная
   модель (включая Qwen3.8) попадает в `models.env` только после успешной live-проверки
   доступности ClinePass.

Phase 0, client registration, permissions, shared contracts, integration, deterministic
acceptance, commits и final response не делегируются ClinePass. Implementation не
начинается, пока локальные Phase 0 checks не зелёные; live endpoint outage документируется
вместе с committed-registry fallback. Политика относится только к development-репозиторию
`skai_7`, не к SKAI requirements/system-analysis repositories.

---

## Подготовка

- `git clone` + `git pull`, установка зависимостей (Python 3.12 + Node 18+)
- Прочитать `agents.md` (что строим и правила) и `prompts/v2-fullstack/00-CONTRACT.md` (как)
- Данные уже в `datasets/ready/**` (54 аларма, 94 MP4, треки, топливо, навигация)

---

## Барьер 0 — Подготовка и контракт (гейт)

| Шаг | Что | Файлы |
|-----|-----|-------|
| 0a | Cleanup мёртвых ссылок + перенос legacy init-setup в `prompts/legacy/` | docs |
| 0b | Заморозка `00-CONTRACT.md` (включая §7 full-scope) | `prompts/v2-fullstack/00-CONTRACT.md` |
| 0c | Решение по источнику `driver_reference` (сид / внешний источник) | §7.1 |

✅ **Чекпоинт 0:** контракт заморожен, навигация чистая.

---

## Волна 1 — Ядро P0 (три трека параллельно)

```
TRACK B: b1→b3 (посл.) ; b2 ‖ b4 ; → b5 → b6
TRACK D: d1 → d2 → d3
TRACK F: f1 → (f2 ‖ f3) → f4
```

Зависимость только по контракту. Критический путь: `b1 → b3 → b5 → b6`.

✅ **Чекпоинт 1:** `make db` собирает DuckDB (54 аларма, 14 типов, `v_incidents`); бэк отдаёт `/api/incidents`.

---

## Волна 2 — Интеграция P0

```
x1 (выпил Streamlit backend/) → x2 (wiring: routers + proxy + Makefile) → x3 (e2e smoke)
```

✅ **Чекпоинт 2:** рабочее демо идеи #1 — `/incidents/:id` на живом API, оба кейса (есть/нет видео), действия пишутся.

---

## Волна 3 — Расширение P1/P2 + Voice/NLU (макс. параллелизм)

После заморозки контракта стартует до ~13 промптов параллельно:

```
TRACK B+: b7-driver-ref → b10-reports-views ; b8-stt ‖ b9-nlu ; b11-sabotage ‖ b12-reb ‖ b13-tickets/alerts/trips
TRACK D+: d4-map ‖ d5-voice/timeline
TRACK F+: f5-лента ‖ f6-карта ‖ f7-отчёт+voice ‖ f8-tickets ‖ f9-alert ‖ f10-досье ‖ f11-РЭБ ‖ f12-саботаж ‖ f13-роли
```

Самая длинная цепочка: `b7 → b10 → f7` (отчёт В-1/В-2 + голос).

✅ **Чекпоинт 3:** идеи #2, #4–#10 рабочие на живом API.

---

## Волна 4 — Финальный e2e

Повторный `x3`: все экраны, голос (faster-whisper) → NLU (Groq) → отчёт, видео по клику, дедупликация ТС на карте, заявки.

✅ **Чекпоинт 4:** сквозные сценарии Flow 1/2/3 проходят end-to-end.

---

## Демо (сценарии)

- **Flow 1:** ДТП без DMS (датчик удара, 54→0) → карточка с видео+телеметрией → [Создать заявку]
- **Flow 2:** нет видео (телефон, камера offline) → placeholder → [Запросить архив]
- **Flow 3:** голос «Нарушения Иванова за 3 дня» → подтверждение → отчёт → клик по нарушению → видео справа
