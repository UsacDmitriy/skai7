# Prompts — SKAI Hackathon: Единое окно видео и телематики

**Стек:** Python 3.12 + Streamlit + Pandas + Altair
**Приложение:** 3 вкладки — Data, Dashboard, Details
**Правило:** один промпт = один файл

```
prompts/
│
├── hackathon/              ← технические промпты по волнам для сборки Streamlit-приложения
│   ├── wave-00/            1 агент  — прочитать контекст
│   ├── wave-00a-architecture/ 4 агента — tech-design, data-контракт, design-tokens
│   ├── wave-01-foundation/ 4 агента — Python dataclasses, constants, data_loader, app skeleton + requirements
│   ├── wave-02-components/ 5 агентов — Python модули: metrics, charts, data_overview, actions, risk_table
│   ├── wave-03-screens/    3 агента  — три вкладки Streamlit: Data, Dashboard, Details
│   ├── wave-04-routing/    1 агент   — финальная интеграция и проверка импортов
│   └── wave-05-polish/     2 агента  — smoke-тест, демо-сценарий
│
│   Всего: 20 агентов/промптов
│
└── init/                   ← инициализационные промпты (запускаются до хакатона / на старте)
    ├── discovery-prompt.md       дискавери: 12 вопросов системного аналитика → черновик AGENTS.md
    ├── orchestration-prompt.md   оркестрация: multi-agent координация каждые 30–60 минут
    └── hackathon-init/           инициализация репозитория и инфраструктуры
        ├── 01-git-infra.md       Git + окружение
        ├── 02-backend.md         Python / Streamlit-база
        ├── 03-frontend.md        UI-структура (вкладки Data, Dashboard, Details)
        └── 04-qa-integration.md  QA и интеграция
```

## Правила запуска

- **Волна = параллельный запуск.** Все промпты внутри одной волны запускаются одновременно.
- **Следующая волна — только после завершения предыдущей.** Каждая волна создаёт артефакты, без которых следующая не имеет смысла.
- **Именование файлов:** `{wave}-{order}-{description}--{model}.md` — модель видна из имени файла.
- **Один промпт = один файл.** Каждый агент трогает только свой выходной файл.

## Где что лежит

| Папка | Назначение | Когда запускать |
|---|---|---|
| `init/discovery-prompt.md` | Системный аналитик задаёт 12 вопросов команде, выдаёт черновик AGENTS.md | Утром, после объявления темы |
| `init/orchestration-prompt.md` | Главный архитектор проверяет согласованность кусков от разных агентов | Каждые 30–60 минут |
| `init/hackathon-init/` | Параллельный запуск Git-инфраструктуры, бэкенда, фронтенда и QA | Один раз в начале хакатона |
| `hackathon/wave-*/` | Пошаговая сборка Streamlit-приложения по волнам | Основная работа хакатона |
