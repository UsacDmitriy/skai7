# 01C · incidents.json
> 🤖 **Модель: `qwen/qwen3-coder:free`** | кодинг
> 💰 **Бюджет:** читать max 1–3 файла · не читать `./data`, `.venv`, `node_modules` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия Cherry Studio.** Не запускать параллельно.

> Волна 1

**Файл:** `data/mock/incidents.json`
**Файл уже существует** — он богатый (701 строка). НЕ пересоздавай с нуля.

Прочитай `data/mock/incidents.json` и убедись что:

1. Есть ровно **5 демо-кейсов** в массиве `incidents`:

| id | alarm_type | vehicle_plate | driver | video_available | Назначение |
|----|-----------|---------------|--------|-----------------|------------|
| inc-001 | DMS_DROWSY | А777ВВ 77 | Иванов А.П. | true | Засыпание за рулём, ночь |
| inc-002 | CRASH_SENSOR | В345КМ 97 | Петров Д.С. | true | **Flow 1** — ДТП без DMS |
| inc-003 | DMS_PHONE | Е902СТ 150 | Сидоров В.Н. | **false** | **Flow 2** — кейс без видео |
| inc-004 | HARSH_BRAKING | Н124УУ 199 | Козлов И.А. | true | Резкое торможение, 108 км/ч при лимите 60 |
| inc-005 | DRIVER_SUBSTITUTION | К451МА 77 | Новиков А.В. | true | Замена водителя, ночь |

2. У каждого инцидента есть поле `risk_level` ('critical' / 'high' / 'medium' / 'low').
   Если отсутствует — добавь на основе score:
   score ≥ 80 → 'critical', 60–79 → 'high', 40–59 → 'medium', < 40 → 'low'

3. У inc-003 `video_available: false` (это критично для кейса Б / Flow 2).

4. У каждого инцидента есть `evidence_summary` — текст 3–5 предложений для блока анализа.

5. Удали из `_comment` упоминания "тема 8" — это не наша тема.

Если чего-то нет — добавь. Если всё есть — просто подтверди без изменений.

**Check:** `python3 -c "import json; d=json.load(open('data/mock/incidents.json')); print(len(d['incidents']), 'incidents')"`
