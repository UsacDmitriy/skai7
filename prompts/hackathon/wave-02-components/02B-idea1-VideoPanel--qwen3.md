# 02B · VideoEvidencePanel.tsx
> 🤖 **Модель: `qwen/qwen3-coder:free`** | кодинг
> 💰 **Бюджет:** читать max 1–3 файла · не читать `./data`, `.venv`, `node_modules` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия Cherry Studio.** Не запускать параллельно.

> Волна 2

**Файл:** `code/frontend/src/components/VideoEvidencePanel.tsx`

Передать: `code/frontend/src/types.ts` + `code/frontend/src/constants.ts`., `types.ts`.

**Props:**
```ts
incident:     Incident
onTimeUpdate: (offsetSec: number) => void
```

## Режим А — `incident.video_available === true`

Контейнер: bg #0F172A, border-radius 8px, padding 12px, flex flex-col gap-2.

Два видеоплеера 16:9:
```tsx
<video ref={adasRef} className="w-full rounded bg-black" controls playsInline>
  <source src={incident.cam_front_url} type="video/mp4" />
</video>
```
Лейблы: "CAM-01 · ADAS · Передняя" / "CAM-02 · DMS · Салон" (11px text-white/70)

Синхронизация через onTimeUpdate:
```ts
adasRef.current.ontimeupdate = () => {
  onTimeUpdate(adasRef.current.currentTime - 60);
  if (Math.abs(dmsRef.current.currentTime - adasRef.current.currentTime) > 0.3)
    dmsRef.current.currentTime = adasRef.current.currentTime;
};
```

Если видео не загружается — показать серый placeholder 16:9 (не краш):
```tsx
<div className="w-full aspect-video bg-slate-800 flex items-center justify-center rounded">
  <span className="text-white/40 text-sm">Видео загружается...</span>
</div>
```

## Режим Б — `incident.video_available === false`

Контейнер: flex flex-col items-center justify-center gap-3,
bg #F8FAFC, border 2px dashed #E2E8F0, border-radius 8px,
padding 32px, min-height 220px.

```tsx
const [requested, setRequested] = useState(false);
```

UI:
- 📷 иконка 48px text-slate-300
- "Видео недоступно" font-semibold text-slate-700
- "Камера CAM-03 не передала данные в архив" text-sm text-slate-500
- Кнопка: [📋 Запросить архивное видео]
  disabled если requested → текст "✓ Запрос создан"
- Если requested: "Ожидайте 15–30 минут" text-xs text-slate-400

**Check:**
- inc-001: два видеоблока с лейблами
- inc-003: placeholder с кнопкой → клик → disabled + "✓ Запрос создан"
