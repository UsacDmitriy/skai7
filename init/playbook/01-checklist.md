# Чеклист до 21 мая — Team 7

## За неделю

### Инструменты
- [ ] Cherry Studio установлен: https://cherry-ai.com
- [ ] Node.js 18+ установлен (`node -v`)
- [ ] Python 3.11+ установлен (`python3 -V`)
- [ ] Git настроен с именем и почтой (`git config --list`)

### OpenRouter
- [ ] Получить team key у организаторов
- [ ] Открыть Cherry Studio → Settings → Model Providers → OpenRouter → вставить key
- [ ] Добавить и проверить модели:
  - [ ] `qwen/qwen3-coder:free` — написать «print hello world» в Python
  - [ ] `nvidia/nemotron-3-super-120b-a12b:free`
  - [ ] `openai/gpt-oss-120b:free`
  - [ ] `moonshotai/kimi-k2.6`
  - [ ] `poolside/laguna-xs.2:free`

### Репозиторий
- [ ] `git clone` репо и `npm install` прошли без ошибок
- [ ] `npm run dev` → :5173 открылся
- [ ] Прочитал `AGENTS.md` — знаю что строим
- [ ] Прочитал `AGENTS.md` раздел 0 — знаю какие модели и правила
- [ ] Прочитал `prompts/hackathon/README.md`

### Контекст продукта
- [ ] Знаю 5 mock-кейсов наизусть (госномер + ФИО + тип события)
- [ ] Знаю Flow 1 (inc-002, Петров, есть видео) и Flow 2 (inc-003, Сидоров, нет видео)
- [ ] Прочитал `hackathon/playbook/02-pitch-template.md`

---

## За день до (20 мая)

- [ ] Запустил проект локально, `npm run dev` работает
- [ ] Сделал тестовый запрос через Cherry Studio — модель ответила
- [ ] Ноутбук заряжен, зарядка лежит в рюкзаке

---

## Утром 21 мая

- [ ] Нормально поел (обед может быть скомканным)
- [ ] Заряжен ноутбук и телефон
- [ ] Адаптер HDMI или USB-C для проектора (у Demo-пилота)
- [ ] Cherry Studio открыт, team key работает
- [ ] Репо свежий (`git pull`)

---

## Не делать накануне

- Не обновлять Cherry Studio или Node.js в день хакатона
- Не переносить настройки на новый ноутбук
- Не засиживаться допоздна

---

## Экстренные контакты

- Лимит/ошибка модели → организатор (team key)
- Репо недоступен → Усачёв Дмитрий
- Детальный план промптов → `hackathon/playbook/00-day-plan.md`
- Матрица моделей → `prompts/hackathon/README.md`
