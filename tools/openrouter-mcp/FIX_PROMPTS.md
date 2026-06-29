# DeepSeek fix-промпты · 5 падающих фронт-тестов (skai_7)

> Модель: `ask_deepseek_flash` (deepseek-v4-flash, самый дешёвый).
> После перезагрузки сессии оркестратор (я) вызывает эти промпты и применяет diff'ы.
> Каждый — атомарная подзадача (METHODOLOGY §4): явный input→output, детерминизм, Check.

---

## T1 · VideoPlayer — дописать рендер маркера события (БАГ КОМПОНЕНТА)

Файл: `web/src/components/ui/VideoPlayer.tsx`. Проп `eventMarkerPct?: number` (0..100)
объявлен и принимается, но НЕ рендерится. Его передают 4 места (DispatchAlert, IncidentCard,
_StyleGuide) — жёлтая метка события на таймлайне отсутствует везде.

Тест-ожидание (`VideoPlayer.test.tsx`): при `eventMarkerPct={50}` в DOM есть элемент
с классом `.bg-warning` и инлайн-стилем `left: 50%`.

Требуется: внутри блока с `<video>` (return при наличии `src`) добавить абсолютно
спозиционированный оверлей-маркер. Условие рендера: `eventMarkerPct != null &&
Number.isFinite(eventMarkerPct)`. Стиль: `left: ${eventMarkerPct}%`, класс содержит
`bg-warning`, вертикальная полоска поверх видео (`absolute top-0 bottom-0 w-0.5 bg-warning`),
`pointer-events-none`, `aria-hidden`. Не ломать существующую разметку и a11y.

Check: `npx vitest run src/components/ui/VideoPlayer.test.tsx` — 5/5 зелёных;
маркер не появляется при `eventMarkerPct=undefined`; `npx tsc --noEmit` чист.

---

## T2 · RoleToggle.test.tsx — обновить устаревшие названия ролей (ДРЕЙФ ТЕСТА)

Файл: `web/src/components/map/RoleToggle.test.tsx`. Компонент после рефакторинга
S488/S489 рендерит лейблы: `logist`→«Логист», `dispatcher`→«Спец. мониторинга»,
`security`→«Диспетчер». «Безопасник» как лейбл удалён. Тест держит старые названия.

Требуется обновить матчеры под текущие лейблы, СОХРАНИВ смысл проверок:
- `value="dispatcher"` → активен сегмент «Спец. мониторинга» (aria-checked=true),
  «Логист» и «Диспетчер» — false.
- клик по «Логист» → onChange('logist'); клик по «Диспетчер» → onChange('security').
- смена value logist→security: «Логист» становится false, «Диспетчер» — true.
Внутренние коды ролей (logist/dispatcher/security) НЕ менять — меняются только тексты в матчерах.

Check: `npx vitest run src/components/map/RoleToggle.test.tsx` — все зелёные.

---

## T3 · RiskWaterfall.test.tsx — лейбл «Погода/сцена»→«Погода» (ДРЕЙФ ТЕСТА)

Файл: `web/src/components/ai/RiskWaterfall.test.tsx`, тест «weather_bonus=0…».
Компонент (`RiskWaterfall.tsx`) использует лейбл слагаемого `weather_bonus` = «Погода».
Тест ищет `getByText('Погода/сцена')` → падает.

Требуется: заменить в этом тесте `'Погода/сцена'` на `'Погода'`. Больше ничего.

Check: `npx vitest run src/components/ai/RiskWaterfall.test.tsx` — все зелёные.

---

## Финальный барьер (после применения T1–T3)
```
cd web && npx vitest run && npx tsc --noEmit
cd .. && ruff check api/   # заодно убрать unused `import pytest` в api/tests/test_reb_anomaly_api.py
```
Ожидание: 238/238 фронт-тестов зелёные, бэкенд 652 зелёных, lint чист.
