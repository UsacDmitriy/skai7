# Волна 3-A — screens/EventFeedScreen.tsx
> 🤖 **Модель: `qwen/qwen3-coder:free`** | кодинг
> 💰 **Бюджет:** читать max 1–3 файла · не читать `./data`, `.venv`, `node_modules` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия Cherry Studio.** Не запускать параллельно.

> Волна 3 · ПОТОК 1


> **. Зависит от всей волны 2.**
> Создать **один файл**: code/frontend/src/screens/EventFeedScreen.tsx

## Промпт

```
Прочитай AGENTS.md, design-prompts/claude-design/02-live-monitor.md.
Убедись: все компоненты волны 2 существуют (IncidentCard, VideoEvidencePanel...).

Создай code/frontend/src/screens/EventFeedScreen.tsx.

Назначение: лента событий слева + главный контент справа.
ЭТО НЕ UnifiedIncidentWindow — это только лента с навигацией в него.

СТЕЙТ:
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all'|'critical'|'no_video'>('all');
  const [role, setRole] = useState<'logist'|'dispatcher'|'safety'>('dispatcher');
  const navigate = useNavigate();

  // Фильтрация по роли — Маслов (Балтика): «Логисты видят только телематику»
  const visibleIncidents = incidents.filter(inc => {
    if (role === 'logist') return inc.source !== 'va'; // скрыть VA-only события
    return true;
  });

ЗАГРУЗКА (при mount):
  import incidentsData from '../../data/mock/incidents.json';
  useEffect(() => setIncidents(incidentsData as Incident[]), []);

ФИЛЬТР:
  const filtered = incidents.filter(inc => {
    if (filter === 'critical')  return inc.riskLevel === 'critical';
    if (filter === 'no_video')  return !inc.hasVideo;
    return true;
  });

LAYOUT flex h-full:

LEFT PANEL (w-80 shrink-0 border-r border-skai-border flex flex-col):

  TOP BAR (px-4 py-3 border-b border-skai-border bg-white flex justify-between items-center):
    <div>
      <h2 className="font-semibold text-skai-text text-sm">События</h2>
      <span className="text-xs text-skai-muted">{visibleIncidents.length} за сегодня</span>
    </div>
    {/* Переключатель роли — Маслов (Балтика) */}
    <div className="flex rounded-lg border border-slate-200 overflow-hidden text-xs">
      {(['logist','dispatcher','safety'] as const).map(r => (
        <button key={r} onClick={() => setRole(r)}
          className={`px-3 py-1 ${role===r ? 'bg-skai-primary text-white' : 'text-slate-500 hover:bg-slate-50'}`}>
          {r==='logist' ? '🏭 Логист' : r==='dispatcher' ? '🛡 Диспетчер' : '🔒 Безопасность'}
        </button>
      ))}
    </div>

  FILTER CHIPS (px-3 py-2 flex gap-1 border-b border-skai-border bg-white):
    3 кнопки-чипа (text-xs px-2 py-1 rounded-full):
      "Все"       filter=all     (active: bg-skai-primary text-white)
      "Критичные" filter=critical
      "Нет видео" filter=no_video
    при клике setFilter(...)

  SCROLL LIST (flex-1 overflow-y-auto):
    {filtered.map(inc => (
      <IncidentCard
        key={inc.id}
        incident={inc}
        isSelected={selectedId === inc.id}
        onClick={() => { setSelectedId(inc.id); navigate(`/incident/${inc.id}`); }}
      />
    ))}
    {filtered.length === 0 && (
      <div className="p-8 text-center text-skai-muted text-sm">Нет событий</div>
    )}

RIGHT PANEL (flex-1 flex items-center justify-center bg-skai-bg):
  <div className="text-center text-skai-muted">
    <div className="text-5xl mb-4">⚡</div>
    <p className="font-medium text-skai-text">Выберите событие</p>
    <p className="text-sm mt-1">Нажмите на событие в ленте слева</p>
  </div>

Экспорт: export default EventFeedScreen
```

## Acceptance criteria
- Файл создан, импортирует IncidentCard из волны 2.
- При загрузке в левой панели — 8 карточек (все из incidents.json).
- Фильтр "Нет видео" показывает inc-003 и inc-006.
- При клике на карточку — навигация на /incident/{id}.
- Правая панель показывает placeholder до выбора события.
