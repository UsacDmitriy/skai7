# 01D · vehicles.json
> 🤖 **Модель: `qwen/qwen3-coder:free`** | кодинг
> 💰 **Бюджет:** читать max 1–3 файла · не читать `./data`, `.venv`, `node_modules` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия Cherry Studio.** Не запускать параллельно.

> Волна 1

**Файл:** `data/mock/vehicles.json`  
**Только этот файл.**

Передавать: `data/mock/incidents.json` (нужны vehicleId).  
Создай массив из **5 объектов** по схеме `Vehicle` из `types.ts`.

| id | plate | driver | cameras | особенность |
|----|-------|--------|---------|-------------|
| V-001 | А777ВВ 77 | Иванов А.П. | CAM-01 ADAS ✓, CAM-02 DMS ✓, CAM-03 CH3 ✓ | все OK |
| V-002 | В345КМ 97 | Петров Д.С. | CAM-01 ✓, CAM-02 ✓, CAM-03 **offline** | для inc-002 |
| V-003 | Е902СТ 150 | Сидоров В.Н. | CAM-01 ✓, CAM-02 ✓, CAM-03 **offline** | для inc-003, calibrationRequired=true |
| V-004 | Н124УУ 199 | Козлов И.А. | CAM-01 ✓, CAM-02 ✓, CAM-03 ✓ | для inc-004 (HARSH_BRAKING) |
| V-005 | К451МА 77 | Новиков А.В. | CAM-01 ✓, CAM-02 ✓ | для inc-005 |

**Check:** `python3 -c "import json; d=json.load(open('data/mock/vehicles.json')); assert len(d)==5"`
