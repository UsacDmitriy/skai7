#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# smoke_user_flows.sh — end-to-end user flow smoke tests via curl.
#
#   bash scripts/smoke_user_flows.sh [API_URL]
#
# Проверяет основные пользовательские сценарии SKAI через HTTP API.
# Требует запущенный бэкенд (make api).
# ---------------------------------------------------------------------------
set -euo pipefail

API_URL="${1:-http://localhost:8000}"

RED='\033[0;31m'
GREEN='\033[0;32m'
BOLD='\033[1m'
NC='\033[0m'

PASSED=0
FAILED=0
TOTAL=0

step() {
    TOTAL=$((TOTAL + 1))
    echo -e "\n${BOLD}[$TOTAL] $1${NC}"
}

ok() {
    PASSED=$((PASSED + 1))
    local time="$1"; shift
    echo -e "  ${GREEN}PASS${NC} (${time}s) $*"
}

fail() {
    FAILED=$((FAILED + 1))
    local time="$1"; shift
    echo -e "  ${RED}FAIL${NC} (${time}s) $*"
}

# ── Проверка API ──────────────────────────────────────────────
echo -e "${BOLD}========================================${NC}"
echo -e "${BOLD}  SKAI Smoke User Flows${NC}"
echo -e "${BOLD}========================================${NC}"
echo "API: $API_URL"

step "Health check"
START=$(python3 -c "import time; print(time.time())")
HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$API_URL/api/health" 2>/dev/null || echo "000")
END=$(python3 -c "import time; print(time.time())")
ELAPSED=$(python3 -c "print(round($END - $START, 2))")
if [ "$HTTP" = "200" ]; then
    ok "$ELAPSED" "health check OK"
else
    fail "$ELAPSED" "health check returned $HTTP"
fi

# ── 1. Лента событий ──────────────────────────────────────────
step "Лента событий: GET /api/incidents"
START=$(python3 -c "import time; print(time.time())")
RESP=$(curl -s --max-time 10 "$API_URL/api/incidents" 2>/dev/null || echo "[]")
END=$(python3 -c "import time; print(time.time())")
ELAPSED=$(python3 -c "print(round($END - $START, 2))")
COUNT=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d) if isinstance(d,list) else 0)" 2>/dev/null || echo "0")
if [ "$COUNT" -gt 0 ]; then
    ok "$ELAPSED" "найдено $COUNT инцидентов"
    FIRST_ID=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0].get('id','') if d else '')" 2>/dev/null || echo "")
    FIRST_PLATE=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0].get('vehicle_plate','') if d else '')" 2>/dev/null || echo "")
    echo "  First incident: $FIRST_ID ($FIRST_PLATE)"
else
    fail "$ELAPSED" "пустой список инцидентов"
    FIRST_ID=""
fi

# ── 2. Карточка инцидента ─────────────────────────────────────
if [ -n "$FIRST_ID" ]; then
    step "Карточка инцидента: GET /api/incidents/$FIRST_ID"
    START=$(python3 -c "import time; print(time.time())")
    RESP=$(curl -s --max-time 10 "$API_URL/api/incidents/$FIRST_ID" 2>/dev/null || echo "{}")
    END=$(python3 -c "import time; print(time.time())")
    ELAPSED=$(python3 -c "print(round($END - $START, 2))")
    HAS_PLATE=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print('yes' if d.get('vehicle_plate') else 'no')" 2>/dev/null || echo "no")
    HAS_VIDEO=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print('yes' if d.get('video_count',0)>0 else 'no')" 2>/dev/null || echo "no")
    if [ "$HAS_PLATE" = "yes" ]; then
        VEHICLE=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('vehicle_plate',''))" 2>/dev/null)
        ok "$ELAPSED" "vehicle=$VEHICLE, video=$HAS_VIDEO"
    else
        fail "$ELAPSED" "нет vehicle_plate в ответе"
    fi

    # ── 3. Видео ───────────────────────────────────────────────
    step "Видео: GET /api/incidents/$FIRST_ID/video/1"
    START=$(python3 -c "import time; print(time.time())")
    HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "$API_URL/api/incidents/$FIRST_ID/video/1" 2>/dev/null || echo "000")
    END=$(python3 -c "import time; print(time.time())")
    ELAPSED=$(python3 -c "print(round($END - $START, 2))")
    if [ "$HTTP" = "200" ] || [ "$HTTP" = "404" ]; then
        ok "$ELAPSED" "video channel 1 → $HTTP (200 or 404, no crash)"
    else
        fail "$ELAPSED" "video returned $HTTP (expected 200 or 404)"
    fi

    # ── 6. Action ──────────────────────────────────────────────
    step "Action: POST /api/actions (validate $FIRST_ID)"
    START=$(python3 -c "import time; print(time.time())")
    RESP=$(curl -s --max-time 10 -X POST "$API_URL/api/actions" \
        -H "Content-Type: application/json" \
        -d "{\"incident_id\": \"$FIRST_ID\", \"action\": \"validate\"}" 2>/dev/null || echo "{}")
    END=$(python3 -c "import time; print(time.time())")
    ELAPSED=$(python3 -c "print(round($END - $START, 2))")
    HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 -X POST "$API_URL/api/actions" \
        -H "Content-Type: application/json" \
        -d "{\"incident_id\": \"$FIRST_ID\", \"action\": \"validate\"}" 2>/dev/null || echo "000")
    if [ "$HTTP" = "200" ]; then
        ok "$ELAPSED" "action recorded → HTTP $HTTP"
    else
        fail "$ELAPSED" "action returned HTTP $HTTP"
    fi
else
    step "Карточка инцидента: SKIP (нет инцидентов)"
    echo "  (SKIP) первый инцидент не найден"
    step "Видео: SKIP"
    echo "  (SKIP) нет ID инцидента"
    step "Action: SKIP"
    echo "  (SKIP) нет ID инцидента"
fi

# ── 4. Отчёт по парку ─────────────────────────────────────────
step "Отчёт по парку: GET /api/reports/fleet?period_days=3"
START=$(python3 -c "import time; print(time.time())")
RESP=$(curl -s --max-time 10 "$API_URL/api/reports/fleet?period_days=3" 2>/dev/null || echo "{}")
END=$(python3 -c "import time; print(time.time())")
ELAPSED=$(python3 -c "print(round($END - $START, 2))")
VC=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('vehicles_count',-1))" 2>/dev/null || echo "-1")
HAS_DRIVERS=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print('yes' if d.get('by_drivers') else 'no')" 2>/dev/null || echo "no")
if [ "$VC" -ge 0 ] && [ "$HAS_DRIVERS" = "yes" ]; then
    ok "$ELAPSED" "vehicles_count=$VC, has by_drivers"
else
    fail "$ELAPSED" "vehicles_count=$VC, drivers=$HAS_DRIVERS"
fi

# ── 5. NLU-запрос ─────────────────────────────────────────────
step "NLU-запрос: POST /api/reports/query"
START=$(python3 -c "import time; print(time.time())")
RESP=$(curl -s --max-time 15 -X POST "$API_URL/api/reports/query" \
    -H "Content-Type: application/json" \
    -d '{"text": "Сводка по парку за неделю"}' 2>/dev/null || echo "{}")
END=$(python3 -c "import time; print(time.time())")
ELAPSED=$(python3 -c "print(round($END - $START, 2))")
HAS_QUERY=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print('yes' if d.get('query') else 'no')" 2>/dev/null || echo "no")
HAS_REPORT=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print('yes' if d.get('report') else 'no')" 2>/dev/null || echo "no")
KIND=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('query',{}).get('kind','?'))" 2>/dev/null || echo "?")
if [ "$HAS_QUERY" = "yes" ] && [ "$HAS_REPORT" = "yes" ]; then
    ok "$ELAPSED" "NLU query → kind=$KIND, has report"
else
    fail "$ELAPSED" "query=$HAS_QUERY, report=$HAS_REPORT"
fi

# ── 7. Здоровье парка ─────────────────────────────────────────
step "Здоровье парка: GET /api/fleet-health"
START=$(python3 -c "import time; print(time.time())")
HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$API_URL/api/fleet-health" 2>/dev/null || echo "000")
END=$(python3 -c "import time; print(time.time())")
ELAPSED=$(python3 -c "print(round($END - $START, 2))")
if [ "$HTTP" = "200" ]; then
    ok "$ELAPSED" "fleet-health → HTTP $HTTP"
else
    fail "$ELAPSED" "fleet-health returned HTTP $HTTP"
fi

# ── 8. OpenAPI схема ─────────────────────────────────────────
step "OpenAPI схема: GET /openapi.json"
START=$(python3 -c "import time; print(time.time())")
HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$API_URL/openapi.json" 2>/dev/null || echo "000")
END=$(python3 -c "import time; print(time.time())")
ELAPSED=$(python3 -c "print(round($END - $START, 2))")
if [ "$HTTP" = "200" ]; then
    ok "$ELAPSED" "OpenAPI schema → HTTP $HTTP"
else
    fail "$ELAPSED" "OpenAPI returned HTTP $HTTP"
fi

# ── Итого ────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}========================================${NC}"
echo -e "${BOLD}  РЕЗУЛЬТАТ: $PASSED / $TOTAL пройдено${NC}"
if [ "$FAILED" -gt 0 ]; then
    echo -e "  ${RED}Провалено: $FAILED${NC}"
fi
echo -e "${BOLD}========================================${NC}"

if [ "$FAILED" -gt 0 ]; then
    exit 1
else
    exit 0
fi