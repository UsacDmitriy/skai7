#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# stress_transcribe.sh — STT stress-test: генерирует WAV 100 МБ,
# отправляет на /api/reports/transcribe, замеряет время и CPU, печатает отчёт.
#
#   bash scripts/stress_transcribe.sh
#
# Требования: ffmpeg (или sox, или python3), curl, bash 4+.
# Переменные:
#   KEEP_TEMP=1  — не удалять временный WAV после прогона.
#   API_URL      — base URL API (по умолчанию http://localhost:8000).
# ---------------------------------------------------------------------------
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMP_FILE="${TEMP_FILE:-/tmp/stress_test_100mb.wav}"
API_URL="${API_URL:-http://localhost:8000}"
TRANSCRIBE_URL="$API_URL/api/reports/transcribe"

# ── Цвета для вывода ──────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m' # No Color

log()  { echo -e "${GREEN}[STT-STRESS]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*"; }

# ── Проверка API ──────────────────────────────────────────────
log "Проверка API $API_URL ..."
if ! curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/health" | grep -q 200; then
    err "API не отвечает на $API_URL/api/health. Запусти сервер: make api"
    exit 1
fi
log "API доступен."

# ── Генерация WAV 100 МБ ──────────────────────────────────────
log "Генерация WAV 100 МБ ..."
# 16kHz mono PCM 16-bit: 32000 bytes/sec × 3277 сек ≈ 104.9 MB raw + 44-byte header
DURATION=3277

if command -v ffmpeg &> /dev/null; then
    log "Использую ffmpeg ..."
    ffmpeg -y -f lavfi -i "sine=frequency=440:duration=$DURATION" \
        -ar 16000 -ac 1 -sample_fmt s16 \
        "$TEMP_FILE" 2>&1 | tail -1
elif command -v sox &> /dev/null; then
    log "Использую sox ..."
    sox -n -r 16000 -c 1 -b 16 "$TEMP_FILE" synth $DURATION sine 440
elif python3 -c "import wave" 2>/dev/null; then
    log "Использую Python (wave) ..."
    python3 -c "
import wave, struct, math
duration = $DURATION
rate = 16000
n = int(duration * rate)
with wave.open('$TEMP_FILE', 'w') as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(rate)
    for i in range(n):
        val = int(16000 * math.sin(2 * math.pi * 440 * i / rate))
        w.writeframes(struct.pack('<h', max(-32768, min(32767, val))))
" 2>&1
elif python3 -c "import array" 2>/dev/null; then
    log "Использую Python (array) ..."
    python3 -c "
import array, math, struct
duration = $DURATION
rate = 16000
n = int(duration * rate)
samples = array.array('h')
for i in range(n):
    val = int(16000 * math.sin(2 * math.pi * 440 * i / rate))
    samples.append(max(-32768, min(32767, val)))
with open('$TEMP_FILE', 'wb') as f:
    # WAV header
    datasize = len(samples) * 2
    f.write(b'RIFF')
    f.write(struct.pack('<I', 36 + datasize))
    f.write(b'WAVE')
    f.write(b'fmt ')
    f.write(struct.pack('<IHHIIHH', 16, 1, 1, rate, rate * 2, 2, 16))
    f.write(b'data')
    f.write(struct.pack('<I', datasize))
    f.write(samples.tobytes())
" 2>&1
else
    err "Нет ни ffmpeg, ни sox, ни Python. Установи ffmpeg: brew install ffmpeg"
    exit 1
fi

FILE_SIZE=$(du -h "$TEMP_FILE" | cut -f1)
log "WAV сгенерирован: $TEMP_FILE ($FILE_SIZE)"

# ── Замер CPU во время транскрипции (фоновый сэмплер) ────────
CPU_LOG="/tmp/stress_cpu_$$.log"
sample_cpu() {
    while kill -0 $$ 2>/dev/null; do
        if [[ "$(uname)" == "Darwin" ]]; then
            # macOS: top -l 1 даёт одну итерацию
            top -l 1 -n 0 2>/dev/null | grep "CPU usage" | awk '{print $3}' | tr -d '%' >> "$CPU_LOG"
        else
            # Linux: ps или top -bn1
            top -bn1 2>/dev/null | grep "Cpu(s)" | awk '{print $2}' | tr -d '%' >> "$CPU_LOG"
        fi
        sleep 0.5
    done
}
sample_cpu &
CPU_PID=$!

# ── Отправка и замер ─────────────────────────────────────────
log "Отправка WAV на $TRANSCRIBE_URL (lang=ru) ..."
START_TS=$(date +%s.%N 2>/dev/null || python3 -c "import time; print(time.time())")
HTTP_CODE=$(curl -s -o /tmp/stress_response.json -w "%{http_code}" \
    -F "file=@$TEMP_FILE" \
    -F "lang=ru" \
    --max-time 600 \
    "$TRANSCRIBE_URL" 2>/tmp/stress_curl_err.log)
CURL_EXIT=$?
END_TS=$(date +%s.%N 2>/dev/null || python3 -c "import time; print(time.time())")

# Остановить сэмплер CPU
kill $CPU_PID 2>/dev/null || true
wait $CPU_PID 2>/dev/null || true

# ── Расчёт времени ────────────────────────────────────────────
ELAPSED=$(python3 -c "print(round($END_TS - $START_TS, 2))")
RESPONSE_TEXT=$(python3 -c "
import json
try:
    with open('/tmp/stress_response.json') as f:
        data = json.load(f)
    text = data.get('text', '')
    print(text[:200])
except: print('(parse error)')
" 2>/dev/null || echo "(parse error)")

# ── Анализ CPU ────────────────────────────────────────────────
if [ -f "$CPU_LOG" ] && [ -s "$CPU_LOG" ]; then
    PEAK_CPU=$(sort -rn "$CPU_LOG" | head -1)
    AVG_CPU=$(awk '{sum+=$1; n++} END {if(n>0) printf "%.1f", sum/n; else print "0"}' "$CPU_LOG")
else
    PEAK_CPU="N/A"
    AVG_CPU="N/A"
fi

# ── Отчёт ─────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}============================================${NC}"
echo -e "${BOLD}  STT STRESS TEST — ОТЧЁТ${NC}"
echo -e "${BOLD}============================================${NC}"
echo ""
echo -e "  Файл:         ${BOLD}$TEMP_FILE${NC} ($FILE_SIZE)"
echo -e "  HTTP статус:  ${BOLD}$HTTP_CODE${NC} (curl exit: $CURL_EXIT)"
echo -e "  Время:        ${BOLD}${ELAPSED}s${NC}"
echo -e "  CPU (пик):    ${BOLD}${PEAK_CPU}%${NC}"
echo -e "  CPU (сред.):  ${BOLD}${AVG_CPU}%${NC}"
echo -e "  Результат:    ${BOLD}${RESPONSE_TEXT}${NC}"
echo ""

# Проверка: curl не упал, HTTP 200, CPU ≥ 50%
PASS=true
if [ "$CURL_EXIT" -ne 0 ]; then
    err "curl завершился с ошибкой (код $CURL_EXIT). Лог:"
    cat /tmp/stress_curl_err.log 2>/dev/null || true
    PASS=false
fi
if [ "$HTTP_CODE" != "200" ]; then
    err "HTTP статус $HTTP_CODE (ожидался 200). Ответ:"
    cat /tmp/stress_response.json 2>/dev/null || true
    PASS=false
fi

# ── Очистка ───────────────────────────────────────────────────
if [ "${KEEP_TEMP:-0}" != "1" ]; then
    rm -f "$TEMP_FILE" /tmp/stress_response.json /tmp/stress_curl_err.log "$CPU_LOG"
    log "Временные файлы удалены (KEEP_TEMP=1 чтобы сохранить)."
else
    log "KEEP_TEMP=1 — временные файлы сохранены."
fi

if [ "$PASS" = true ]; then
    log "${BOLD}STRESS TEST: PASSED${NC}"
    exit 0
else
    err "STRESS TEST: FAILED"
    exit 1
fi