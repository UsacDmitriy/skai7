# b8 · STT-сервис — stt_service.py

> Трек **Backend/Data**. Против `00-CONTRACT.md` §7.3. **Владеет:** `api/services/stt_service.py`.
> **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — детерминированная логика/вёрстка против контракта; гейт = секция Check.
> Кодит против контракта. **Зависит от:** b4 (`faster-whisper` в `api/requirements.txt`, конфиг в `api/core/config.py`). Параллелится с b7/b9/b11/b12 (не пересекаются по файлам). Используется роутером `POST /api/reports/transcribe` (b6+).

## Цель

Локальная транскрипция голосовых запросов диспетчера (идея #2) на `faster-whisper` `large-v3`,
языки **RU/KK/EN**. Модель тяжёлая → **ленивая загрузка** один раз на процесс.

## Модуль `api/services/stt_service.py`

- Конфиг из `api/core/config.py` (заводит b4): `whisper_model="large-v3"`, `whisper_device="cpu"`.
- Ленивый синглтон модели: модуль-уровневая переменная `_model = None`; функция `_get_model()`
  создаёт `WhisperModel(settings.whisper_model, device=settings.whisper_device, compute_type=...)`
  при первом вызове и кэширует. Импорт `faster_whisper` — **внутри** `_get_model` (не на уровне модуля),
  чтобы импорт сервиса не тянул тяжёлую зависимость при старте API.
- Сигнатура (точно по §7.3):
  ```python
  def transcribe(wav_bytes: bytes, lang: str | None = None) -> dict:
      # -> {"text": str, "lang": str, "confidence": float}
  ```
  - `wav_bytes` — содержимое WAV (из `multipart/form-data`). Передать в модель через
    `io.BytesIO(wav_bytes)` (faster-whisper принимает file-like/путь).
  - `lang` — если задан (`"ru"|"kk"|"en"`), фиксирует язык; иначе автоопределение.
  - `text` — конкатенация сегментов (`.strip()`).
  - `lang` в ответе — определённый/переданный язык (`info.language`).
  - `confidence` — агрегат по сегментам: среднее `exp(avg_logprob)` (clamp `[0,1]`), либо
    `info.language_probability` при автоопределении. При пустом распознавании — `0.0`.
- Без `GROQ`/сети: всё локально. Ошибки декодирования WAV → `ValueError` с понятным сообщением
  (роутер вернёт 400).

## Check

- `from api.services.stt_service import transcribe` импортируется **без** загрузки модели (ленивость).
- `faster-whisper` присутствует в `api/requirements.txt` (ответственность b4 — здесь только импорт внутри `_get_model`).
- `transcribe(open(test.wav,'rb').read())` возвращает dict с ключами `text`, `lang`, `confidence`;
  `confidence ∈ [0,1]`, `lang ∈ {"ru","kk","en",...}`.
- Повторные вызовы переиспользуют один экземпляр модели (`_get_model` создаёт её один раз).

## Edge cases / поведение

- **Нет модели/веса/`faster-whisper` недоступен:** детерминированный graceful-fallback — `transcribe` возвращает валидный dict `{"text":"", "lang": lang or "ru", "confidence":0.0}`, а не необработанное исключение (тяжёлый импорт изолирован в `_get_model`).
- **Пустой `wav_bytes` (`b""`):** не падать — `{"text":"", "lang": ..., "confidence":0.0}`; нулевая длина не доходит до тяжёлого декодирования.
- **Битый/не-WAV байт-поток:** ошибка декодирования → `ValueError` с понятным сообщением (роутер → 400); никаких трейсбеков наружу.
- **Пустое распознавание (тишина):** сегментов нет → `text=""`, `confidence=0.0`, `lang` = автоопределённый/переданный (без NULL).
- **Детерминизм по входу:** повтор одного и того же `wav_bytes` (+ тот же `lang`) даёт тот же `{text,lang,confidence}` в рамках процесса (модель загружена, `temperature` не применяется к decode).
- **Жёсткая локальность:** ни один путь не обращается к сети/`GROQ`; отсутствие `GROQ_API_KEY` на работу STT не влияет (STT и NLU независимы).
- **Фиксация языка:** при `lang∈{"ru","kk","en"}` ответный `lang` равен переданному (без переопределения автоопределением).

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**; незакоммиченная
работа в worktree на барьер не попадёт:

```bash
git add -A && git commit -m "b8: <что сделано>"
```
