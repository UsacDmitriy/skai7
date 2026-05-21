# Промпт 1 — Git & Infra (Streamlit MVP)

Задача: настроить Git-репозиторий и проектную инфраструктуру для Streamlit-приложения «05. Единое окно видео и телематики».

Рабочая директория: `05_video_telematics_single_window/`

## 1. Синхронизация Git

- Проверь remote-репозиторий: `git remote -v`
- Получи последние изменения: `git fetch origin`
- Выполни `git status`, чтобы понять текущее состояние.
- Создай feature-ветку: `git checkout -b hackathon/streamlit-mvp`
- Если есть незакоммиченные изменения — закоммить их в новой ветке.

## 2. Структура проекта

Убедись, что структура соответствует схеме:

```
05_video_telematics_single_window/
├── app/               # Модули Streamlit (app.py, pages/, utils/)
├── data/              # CSV-файлы (уже существуют — не изменять)
├── sample_data/       # Демо-CSV (уже существуют — не изменять)
├── output/            # Сгенерированные отчеты (создать mkdir, если нет)
├── requirements.txt   # Зависимости Python
└── README.md          # Инструкция по запуску
```

Создай недостающие директории (`app/`, `output/`) и базовые файлы (`requirements.txt`, `README.md`), только если они отсутствуют.

## 3. `.gitignore`

Проверь и дополни `.gitignore` — он должен содержать:

```
.venv/
__pycache__/
*.pyc
.DS_Store
output/actions.csv
output/incident_reports.csv
```

## 4. Проверка Python

- Проверь версию: `python3 --version` или `python3.12 --version`
- Требуется Python 3.12+. Если нет — установи через `pyenv` или системный пакетный менеджер.

## 5. Виртуальное окружение

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

## 6. Зависимости

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Минимальный `requirements.txt` для старта:

```
streamlit>=1.28.0
pandas>=2.0.0
```

## 7. Проверка запуска

Убедись, что `streamlit run app/app.py` стартует (даже с заглушкой-плейсхолдером).

Минимальный `app/app.py`:

```python
import streamlit as st

st.set_page_config(page_title="Единое окно видео и телематики", layout="wide")
st.title("SKAI Hackathon: Единое окно видео и телематики")
st.write("MVP готова к наполнению.")
```

## Запрещено

- Делать force-push в main.
- Удалять или изменять существующие наборы данных в `data/` и `sample_data/`.
- Менять файлы за пределами `05_video_telematics_single_window/` без явного согласования.

## Результат

Чистый `git status` на ветке `hackathon/streamlit-mvp`, готовое виртуальное окружение, `streamlit run app/app.py` стартует без ошибок.
