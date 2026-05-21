# 01F-B · fleet-report.json + fleet-vehicles.json — Мок Идея #2 В-2
> 🤖 **Модель: `qwen/qwen3-coder:free`** | кодинг
> 💰 **Бюджет:** читать max 1–3 файла · не читать `./data`, `.venv`, `node_modules` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия Cherry Studio.** Не запускать параллельно.

> Волна 1
> Нужен для: AnalyticsScreen режим В-2 (парк)

Прочитай AGENTS.md. Создай два файла:
- `data/mock/fleet-report.json` — по водителям
- `data/mock/fleet-vehicles.json` — по ТС (камеры + multi-driver)

## 1F-B: data/mock/fleet-report.json

Режим В-2 — запрос по парку/подразделению.
Структура ответа /api/analytics/fleet-report.

```json
{
  "mode": "fleet",
  "query": "Все нарушения по компании за последние три дня",
  "periodLabel": "14–16.05.2026",
  "periodDays": 3,
  "totalViolations": 23,
  "totalGross": 3,
  "totalVa": 12,
  "totalTel": 11,
  "totalMileageKm": 2840,
  "driversCount": 5,
  "byDay": [
    {"day": "14.05", "va": 5, "tel": 4},
    {"day": "15.05", "va": 4, "tel": 4},
    {"day": "16.05", "va": 3, "tel": 3}
  ],
  "drivers": [
    {
      "rank": 1,
      "driverName": "Иванов Алексей Петрович",
      "driverInitials": "ИА",
      "vehicleId": "А777ВВ 77",
      "safetyScore": 68,
      "totalCount": 7,
      "grossCount": 1,
      "vaCount": 4,
      "telCount": 3,
      "mileageKm": 487,
      "lat": 55.762, "lng": 37.634
    },
    {
      "rank": 2,
      "driverName": "Петров Дмитрий Сергеевич",
      "driverInitials": "ПД",
      "vehicleId": "В345КМ 97",
      "safetyScore": 72,
      "totalCount": 6,
      "grossCount": 2,
      "vaCount": 3,
      "telCount": 3,
      "mileageKm": 612,
      "lat": 55.748, "lng": 37.601
    },
    {
      "rank": 3,
      "driverName": "Сидоров Василий Николаевич",
      "driverInitials": "СВ",
      "vehicleId": "Е902СТ 150",
      "safetyScore": 76,
      "totalCount": 4,
      "grossCount": 0,
      "vaCount": 2,
      "telCount": 2,
      "mileageKm": 534,
      "lat": 55.739, "lng": 37.589
    },
    {
      "rank": 4,
      "driverName": "Козлов Игорь Андреевич",
      "driverInitials": "КИ",
      "vehicleId": "Н124УУ 199",
      "safetyScore": 81,
      "totalCount": 3,
      "grossCount": 0,
      "vaCount": 2,
      "telCount": 1,
      "mileageKm": 698,
      "lat": 55.755, "lng": 37.622
    },
    {
      "rank": 5,
      "driverName": "Степанов Денис Владимирович",
      "driverInitials": "СД",
      "vehicleId": "М213ОО 77",
      "safetyScore": 84,
      "totalCount": 3,
      "grossCount": 0,
      "vaCount": 1,
      "telCount": 2,
      "mileageKm": 509,
      "lat": 55.741, "lng": 37.598
    }
  ]
}
```

---



**Check:**
```bash
python3 -c "
import json
f=json.load(open('data/mock/fleet-report.json'))
v=json.load(open('data/mock/fleet-vehicles.json'))
print('drivers:', len(f['drivers']), '| vehicles:', len(v['vehicles']))
print('А777ВВ cameras:', [c['status'] for c in v['vehicles'][0]['cameras']])
"
# → drivers: 5 | vehicles: 5
# → А777ВВ cameras: ['online', 'online', 'offline']
```
