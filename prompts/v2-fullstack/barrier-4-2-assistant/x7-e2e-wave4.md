# x7 · e2e ассистент (Волна 4.2) — `main` не трогаем

> **Барьер под-волны 4.2 (ассистент).** **Владеет:** только запуск/проверки (e2e ассистента + регресс).
> Авторство тестов — трек T. **Модель:** 🔴 Opus — интеграция/приёмка.
> Запускать ПОСЛЕ Волны 4.2 (b21–b23, f15–f19, tu-copilot, t-wave4-frontend) и зелёного x6.
> **`main` продвигает финальный барьер Волны 4.3 — `x8`**, не этот.

## Перед стартом — склейка Волны 4.2 (main держим стабильным)

В окне `skai_7` на ветке `integration`. **`main` = стабильный P1/P2 — не трогаем.**

```bash
cd /Users/dimausac/projects/skai_7
git checkout integration

# GUARD: merge берёт только коммиты — стоп, если в worktree есть незакоммиченные изменения.
for w in backend web tests; do
  d=".worktrees/$w"; [ -d "$d" ] || continue
  test -z "$(git -C "$d" status --porcelain)" || { echo "❌ $w: незакоммичено — закоммить в worktree и повтори барьер"; exit 1; }
done

git merge feat/backend feat/web feat/tests   # 4.2: b21–b23, f15–f19, tu-copilot, t-wave4-frontend
```

## Проверка предыдущего шага (x6 · умное событие/прогнозы зелёный)

Не начинай e2e, пока x6 (smoke 4.1) не подтверждён: `incident_scene`/`incident_weather` собраны,
`/forecast`/`/zones`/`/fatigue` отвечают, `b24`-governance мета присутствует.

## Цель

End-to-end по **ассистенту и UI-интеграции** AI-слоя на кэше/фолбэке (офлайн): данные → backend → UI.
Слой измеримости/безопасности/explainability (#18–#20) проверяет следующий барьер **x8** (Волна 4.3).

## Шаги

1. `make db` → `incident_scene`/`incident_weather`=54, `v_risk_zones` непуст.
2. `make api`: `/incidents/{id}/scene`, `/reports/forecast/{plate}`, `/zones`, `/fatigue`,
   `POST /api/copilot/chat` (RU и EN, без ключа → фолбэк) → все 200, схемы §8.4.
   `b22`-нарратив присутствует в `/reports/*` и `/forecast` (поле `narrative`, §7.5/§8.4).
3. `pytest api/tests/unit -q` (включая `tu-scene/weather/forecast/zones/fatigue/copilot`) — зелёный;
   регресс P0/P1/P2 не сломан; `b18`-прогноз отдаёт детерминированный fallback (без ARIMA, §8.0).
4. `make web` + `npm run typecheck`: карточка показывает сцену+расхождение; отчёт — спарклайн+рекомендации+
   нарратив; копилот отвечает (RU/EN); монитор — heatmap+зоны (incident/reb); виджет саботажа — умный вердикт.
   `npm run test` зелёный.

## Универсальный гейт + негативы ассистента (обязательно)

Прогнать **полный** [`../barrier-CHECKLIST.md`](../barrier-CHECKLIST.md): `bash scripts/check.sh` целиком
(весь регресс P0/P1/P2/Волна 3/4.1 — не только `tu-copilot`), пост-условие git (`main` НЕ тронут — финал в x8).

Негативы/детерминизм копилота и нарратива (доп.):
```bash
post(){ curl -s -X POST localhost:8000/api/copilot/chat -H 'content-type: application/json' -d "$1"; }
unset GROQ_API_KEY
post '{"text":"кто в группе риска сегодня?"}' | jq -e '.role=="assistant" and .lang=="ru"'   # RU, fallback-маршрутизация
post '{"text":"who is high risk today?"}'    | jq -e '.lang=="en"'                            # EN детект
post '{"text":"asdkjhqwe"}'                  | jq -e '.text|length>0'                          # бессмыслица → вежливый ответ, не 5xx
curl -s -X POST localhost:8000/api/copilot/chat -d '{}' -H 'content-type: application/json' -o /dev/null -w '%{http_code}'  # 422
diff <(post '{"text":"сравни Иванова и Петрова"}') <(post '{"text":"сравни Иванова и Петрова"}')  # детерминизм fallback
curl -s localhost:8000/api/reports/driver/<plate> | jq -e 'has("narrative")'                  # b22: поле narrative (§7.5)
post '{"text":"сравни Иванова и Петрова"}' | jq -e '[.tool_calls[].name]|index("driver_report")!=null'  # E1: маршрутизация по таблице b21
diff <(curl -s localhost:8000/api/reports/driver/<plate> | jq .narrative) \
     <(curl -s localhost:8000/api/reports/driver/<plate> | jq .narrative)                     # D1: narrative детерминирован (b22)
curl -s localhost:8000/api/reports/driver/<plate> | jq -e '.narrative|type=="string" and length>0'      # D1: narrative не NULL
curl -s localhost:8000/api/reports/forecast/<plate> \
  | jq -e '.anomaly==false and (.anomaly_reason//""|test("недостаточно"))'                    # G1/§8.0: b18 = фолбэк на 2-дневных данных
# governance §8.6 — реальная конвенция флага: SKAI_AI_<NAME> (0/false/off → выкл), НЕ AI_*_ENABLED.
# Флаги читаются на старте процесса → задаём env при запуске сервера для проверки:
#   SKAI_AI_COPILOT=0 make api  →  POST /copilot/chat = 200 {"enabled":false} (не 5xx)
curl -s localhost:8000/api/incidents/<id>/scene | jq -e '.state.source|test("live|cache|fallback")'  # мета AiFeatureState
```
- Паритет: карточка(сцена)/отчёт(прогноз+нарратив)/монитор(heatmap)/копилот/виджет — на живом API **и**
  `VITE_USE_FIXTURES=true`; состояния loading/empty/error копилота; консоль чистая; a11y чата (роль/клавиатура).

## Критерии приёмки

- Идеи #11–#16 проходят сквозь стек на офлайн-кэше; нет сети/ключей — не падает (фолбэк); копилот RU/EN, негатив 422.
- **Полный** `scripts/check.sh` зелёный (регресс прошлых волн не сломан); `narrative` присутствует (b22).
- Обратная совместимость: P0/P1/P2 + Волна 3 регресс зелёный (risk_score/sabotage/отчёты/fleet-health не сломаны).
- Типы §8.4 совпадают; фронт без ошибок typecheck.
- `b24`-governance работает (флаг off → «disabled» 200; мета `AiFeatureState`).
- Прогноз = детерминированный фолбэк §8.0 (`anomaly=false`, причина «недостаточно истории»);
  `narrative` не NULL и стабилен между запросами; маршрутизация фолбэка соответствует таблице b21.

## Финализация — НЕ трогаем `main`

`main` остаётся на стабильном P1/P2. Зелёный x7 = ассистент готов на `integration` → переходим к **Волне 4.3**
(ops & trust). `main` продвинет её барьер **x8** после полного регресса + live-smoke.

Красный e2e → дефект треку, чиним на `integration`; к Волне 4.3 не переходим.

## Коммит (обязательно)

Барьер фиксирует smoke-правки (если были) в `integration`:

```bash
git add -A && git commit -m "x7: e2e ассистент (Волна 4.2), main не трогаем"
```
