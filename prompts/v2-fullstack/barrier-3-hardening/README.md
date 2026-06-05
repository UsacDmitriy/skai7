# Барьер 3 · хардненинг Волны 3

Основное окно `skai_7`, ветка `integration` → `main`, **последовательно**. Схема — [`../EXECUTION.md`](../EXECUTION.md).

```text
Выполни @prompts/v2-fullstack/barrier-3-hardening/x5-wave3-hardening.md
```

- `x5` — merge `feat/backend`+`feat/tests` → полный регресс (unit+API+фронт) + гейт покрытия
  (`api/` ≥ 85%, `web/src` ≥ 80%) → `main` (ff). Проверяет пункты Волны 3 (W3-1…W3-5).
