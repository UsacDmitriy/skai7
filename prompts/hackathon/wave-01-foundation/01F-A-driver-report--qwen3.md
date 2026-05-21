# 01F-A · driver-report.json — Мок Идея #2 В-1
> 🤖 **Модель: `qwen/qwen3-coder:free`** | кодинг
> 💰 **Бюджет:** читать max 1–3 файла · не читать `./data`, `.venv`, `node_modules` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия Cherry Studio.** Не запускать параллельно.

> Волна 1
> Нужен для: AnalyticsScreen режим В-1 (один водитель)

Прочитай AGENTS.md. Создай `data/mock/driver-report.json`.

Это данные для демо Flow 3: «Нарушения Иванова за три дня».

```json
{
  "mode": "single_driver",
  "driverName": "Иванов Алексей Петрович",
  "driverInitials": "ИА",
  "vehicleId": "А777ВВ 77",
  "vehicleModel": "Scania R450",
  "safetyScore": 68,
  "tenureLabel": "4 г 2 мес",
  "periodLabel": "14–16.05.2026",
  "periodDays": 3,
  "mileageKm": 487,
  "tripsCount": 4,
  "driveTimeMin": 582,
  "department": "Логистика · Север-1",
  "region": "Москва",
  "totalCount": 7,
  "grossViolations": 1,
  "vaCount": 4,
  "telCount": 3,
  "violations": [
    {
      "id": "v1", "date": "14.05", "time": "08:14",
      "type": "Превышение скорости +18 км/ч",
      "source": "tel", "severity": "high",
      "speedKmh": 78, "limitKmh": 60, "hasVideo": false,
      "lat": 55.751, "lng": 37.618, "incidentId": "inc-001"
    },
    {
      "id": "v2", "date": "14.05", "time": "10:32",
      "type": "Курение за рулём",
      "source": "va", "severity": "gross",
      "speedKmh": 76, "limitKmh": 60, "hasVideo": true,
      "lat": 55.762, "lng": 37.634, "incidentId": "inc-001",
      "camera": "CAM-02 · DMS · Салон",
      "continuousDriveMin": 138
    },
    {
      "id": "v3", "date": "14.05", "time": "14:51",
      "type": "Резкое торможение",
      "source": "tel", "severity": "high",
      "speedKmh": 88, "limitKmh": 60, "hasVideo": false,
      "lat": 55.748, "lng": 37.601, "incidentId": "inc-001"
    },
    {
      "id": "v4", "date": "15.05", "time": "00:36",
      "type": "Засыпание за рулём",
      "source": "va", "severity": "high",
      "speedKmh": 72, "limitKmh": 60, "hasVideo": true,
      "lat": 55.739, "lng": 37.589, "incidentId": "inc-001",
      "camera": "CAM-02 · DMS · Салон"
    },
    {
      "id": "v5", "date": "15.05", "time": "09:05",
      "type": "Ремень безопасности",
      "source": "va", "severity": "high",
      "speedKmh": 0, "hasVideo": true,
      "lat": 55.755, "lng": 37.622, "incidentId": "inc-001"
    },
    {
      "id": "v6", "date": "15.05", "time": "21:15",
      "type": "Превышение скорости +9 км/ч",
      "source": "tel", "severity": "medium",
      "speedKmh": 69, "limitKmh": 60, "hasVideo": false,
      "lat": 55.741, "lng": 37.598, "incidentId": "inc-001"
    },
    {
      "id": "v7", "date": "16.05", "time": "13:40",
      "type": "Отвлечение внимания",
      "source": "va", "severity": "high",
      "speedKmh": 65, "hasVideo": true,
      "lat": 55.758, "lng": 37.641, "incidentId": "inc-001",
      "camera": "CAM-02 · DMS · Салон"
    }
  ],
  "speedByDay": [
    {"day": "14.05", "avgKmh": 74, "maxKmh": 88},
    {"day": "15.05", "avgKmh": 68, "maxKmh": 72},
    {"day": "16.05", "avgKmh": 65, "maxKmh": 71}
  ]
}
```



**Check:**
```bash
python3 -c "import json; d=json.load(open('data/mock/driver-report.json')); print(d['driverName'], len(d['violations']), 'нарушений')"
# → Иванов Алексей Петрович 7 нарушений
```
