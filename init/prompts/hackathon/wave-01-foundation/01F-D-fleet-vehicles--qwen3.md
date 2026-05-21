# Волна 01F-D — fleet-vehicles.json (В-2 по ТС)
> 🤖 **Модель: `qwen/qwen3-coder:free`** | генерация mock JSON
> 💰 **Контекст:** только этот промпт (~1K токенов) | $0
> ⚠️ Запускать после 01A (types.ts). Результат → `data/mock/fleet-vehicles.json`

## Зачем

`fleet-vehicles.json` сейчас пустой (0 bytes), но `AnalyticsScreen.tsx` его импортирует.
Без этого файла `npm run build` упадёт с ошибкой TypeScript.

## Промпт

```
Создай data/mock/fleet-vehicles.json — mock-данные для режима В-2 "По ТС"
в AnalyticsScreen SKAI Unified Incident Window.

Ключевая логика: 1 ТС = актив компании. За период у ТС могут быть разные водители.

Структура верхнего уровня:
{
  "meta": { "period": "14–16.05.2026", "total_km": 2840 },
  "vehicles": [ ...5 объектов... ]
}

Каждый объект vehicles[]:
{
  "vehicleId": "А777ВВ 77",
  "model": "Scania R450",
  "risk_score": 68,
  "total_km": 487,
  "trips_count": 5,
  "violations_count": 7,
  "violations_va": 4,
  "violations_tel": 3,
  "gross_count": 1,
  "cameras": [
    { "id": "CAM-01", "type": "ADAS", "status": "online", "label": "Передняя" },
    { "id": "CAM-02", "type": "DMS",  "status": "online", "label": "Салон" },
    { "id": "CAM-03", "type": "CH3",  "status": "offline","label": "Задняя" }
  ],
  "drivers": [
    { "name": "Иванов А.П.", "role": "primary", "trips": 4, "dates": "14–16.05" },
    { "name": "Козлов И.А.", "role": "additional", "trips": 1, "dates": "14.05" }
  ],
  "last_violations": [
    { "time": "14.05 · 10:32", "type": "Курение за рулём", "severity": "gross" },
    { "time": "15.05 · 00:36", "type": "Засыпание за рулём", "severity": "high" },
    { "time": "16.05 · 13:40", "type": "Отвлечение внимания", "severity": "high" }
  ]
}

5 ТС (в порядке убывания нарушений):
1. А777ВВ 77 · Scania R450 · risk 68 · 7 наруш. (4ВА+3тел) · 1 груб.
   Камеры: CAM-01 online, CAM-02 online, CAM-03 offline
   Водители: Иванов А.П. (primary, 4 рейса) + Козлов И.А. (additional, 1 рейс)

2. В345КМ 97 · MAN TGX · risk 72 · 6 наруш. (3ВА+3тел) · 2 груб.
   Камеры: все 3 online
   Водители: Петров Д.С. (primary, 5 рейсов)

3. Е902СТ 150 · Volvo FH · risk 76 · 4 наруш. (2ВА+2тел) · 0 груб.
   Камеры: CAM-01 online, CAM-02 online, CAM-03 offline
   Водители: Сидоров В.Н. (primary, 3 рейса)

4. Н124УУ 199 · DAF XF · risk 81 · 3 наруш. (0ВА+3тел) · 0 груб.
   Камеры: все 3 online
   Водители: Козлов И.А. (primary, 4 рейса)

5. М213ОО 77 · Kamaz 5490 · risk 84 · 3 наруш. (1ВА+2тел) · 0 груб.
   Камеры: CAM-01 online, CAM-02 online, CAM-03 пониженный сигнал (degraded)
   Водители: Степанов Д.В. (primary, 3 рейса)

Только JSON. Без объяснений.
```
