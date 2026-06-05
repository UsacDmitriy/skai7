"""Tests for api.core.enrichment — deterministic enrichment functions."""

from __future__ import annotations

import pytest
from api.core.enrichment import (
    cameras_from_videofiles,
    continuous_driving_min,
    driver_for,
    driver_id_for,
    driver_phone_for,
    evidence_summary,
    is_night,
    risk_score,
    speed_limit_for,
    telemetry_from_trackpoints,
    vehicle_model_for,
)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_driver_for_stable(self):
        plate = "Т780РН198"
        assert driver_for(None, plate) == driver_for(None, plate)
        assert driver_for(None, plate) == driver_for(None, plate)  # third call

    def test_driver_for_returns_dict(self):
        result = driver_for(None, "А777ВВ77")
        assert set(result) == {"driver", "driver_id", "driver_phone"}
        assert isinstance(result["driver"], str)
        assert result["driver_id"].startswith("DRV-")
        assert result["driver_phone"].startswith("+7")

    def test_driver_id_stable(self):
        plate = "Т780РН198"
        assert driver_id_for(plate) == driver_id_for(plate)

    def test_driver_phone_stable(self):
        plate = "Т780РН198"
        assert driver_phone_for(plate) == driver_phone_for(plate)

    def test_vehicle_model_stable(self):
        plate = "Т780РН198"
        assert vehicle_model_for(plate) == vehicle_model_for(plate)

    def test_different_plates_may_differ(self):
        results = {driver_for(None, p)["driver"] for p in ["А111АА77", "В222ВВ99", "С333СС77", "Д444ДД77"]}
        assert len(results) >= 1  # can't be zero, just sanity


# ---------------------------------------------------------------------------
# driver_id_for format
# ---------------------------------------------------------------------------


class TestDriverId:
    def test_format(self):
        did = driver_id_for("А777ВВ77")
        assert did.startswith("DRV-")
        num = int(did[4:])
        assert 1000 <= num <= 9999

    def test_value_stable(self):
        assert driver_id_for("А777ВВ77") == driver_id_for("А777ВВ77")


# ---------------------------------------------------------------------------
# driver_phone_for format
# ---------------------------------------------------------------------------


class TestDriverPhone:
    def test_format(self):
        phone = driver_phone_for("К123НО77")
        assert phone.startswith("+7")
        assert len(phone) == 12  # +7 + 10 digits
        assert phone[2:].isdigit()

    def test_stable(self):
        assert driver_phone_for("К123НО77") == driver_phone_for("К123НО77")


# ---------------------------------------------------------------------------
# speed_limit_for
# ---------------------------------------------------------------------------


class TestSpeedLimit:
    def test_dms_drowsiness(self):
        assert speed_limit_for("Drowsiness") == 60

    def test_dms_yawning(self):
        assert speed_limit_for("Yawning") == 60

    def test_highway_default(self):
        assert speed_limit_for("SpeedLimitViolation") == 90

    def test_sharp_braking(self):
        assert speed_limit_for("SharpBraking") == 90

    def test_unknown_code_defaults_to_90(self):
        assert speed_limit_for("UNKNOWN_EVENT_XYZ") == 90

    def test_mock_dms_drowsy(self):
        assert speed_limit_for("DMS_DROWSY") == 60

    def test_mock_harsh_braking(self):
        assert speed_limit_for("HARSH_BRAKING") == 90

    def test_canonical_dms_codes_city_limit(self):
        # Реальные коды каталога DMS → 60 (раньше уходили в дефолт 90).
        for code in ("DMS_SMOKING", "DMS_YAWNING", "DMS_SEATBELT", "CAMERA_TAMPER"):
            assert speed_limit_for(code) == 60, code

    def test_canonical_adas_codes_city_limit(self):
        for code in ("ADAS_FCW", "ADAS_HMW", "ADAS_PCW"):
            assert speed_limit_for(code) == 60, code

    def test_canonical_highway_codes(self):
        for code in ("OVERSPEED", "HARSH_ACCEL", "HARSH_CORNERING"):
            assert speed_limit_for(code) == 90, code


# ---------------------------------------------------------------------------
# is_night
# ---------------------------------------------------------------------------


class TestIsNight:
    def test_night_23h(self):
        assert is_night("2026-05-14T23:37:22Z") is True

    def test_day_10h(self):
        assert is_night("2026-05-15T10:15:00Z") is False

    def test_midnight_is_night(self):
        assert is_night("2026-05-15T00:00:00Z") is True

    def test_hour_22_is_night(self):
        assert is_night("2026-05-15T22:00:00Z") is True

    def test_hour_06_is_day(self):
        assert is_night("2026-05-15T06:00:00Z") is False

    def test_hour_05_is_night(self):
        assert is_night("2026-05-15T05:59:59Z") is True

    def test_with_offset_notation(self):
        # +00:00 notation instead of Z
        assert is_night("2026-05-14T23:37:22+00:00") is True


# ---------------------------------------------------------------------------
# continuous_driving_min
# ---------------------------------------------------------------------------


class TestContinuousDrivingMin:
    def test_parse_normal(self):
        assert continuous_driving_min("02:58:00") == 178

    def test_parse_zero(self):
        assert continuous_driving_min("00:00:00") == 0

    def test_parse_hours_and_minutes(self):
        assert continuous_driving_min("01:30:45") == 90  # 1*60 + 30 = 90

    def test_none_returns_zero(self):
        assert continuous_driving_min(None) == 0

    def test_empty_string_returns_zero(self):
        assert continuous_driving_min("") == 0

    def test_invalid_format_returns_zero(self):
        assert continuous_driving_min("garbage") == 0

    def test_1h45m(self):
        assert continuous_driving_min("01:45:00") == 105


# ---------------------------------------------------------------------------
# risk_score
# ---------------------------------------------------------------------------


class TestRiskScore:
    def test_critical_high_speed_night_high_freq(self):
        score = risk_score("critical", 107, 90, True, 5)
        assert 0 <= score <= 100
        assert score > 70  # should be high

    def test_low_low_speed_day_zero_freq(self):
        score = risk_score("low", 30, 90, False, 0)
        assert 0 <= score <= 100

    def test_critical_beats_low(self):
        score_critical = risk_score("critical", 107, 90, True, 5)
        score_low = risk_score("low", 30, 90, False, 0)
        assert score_critical > score_low

    def test_clamped_at_100(self):
        score = risk_score("critical", 999, 60, True, 100)
        assert score == 100

    def test_clamped_at_0(self):
        score = risk_score("low", 0, 90, False, 0)
        assert score >= 0

    def test_divide_by_zero_speed_limit(self):
        # speed_limit_kmh == 0 must not raise
        score = risk_score("medium", 50, 0, False, 3)
        assert 0 <= score <= 100

    def test_formula_sanity(self):
        # manual check: critical, speed=90/90 (ratio=1), night, 7 events
        # sev_w=1.0, speed_ratio=1/1.5=0.667, night=1, freq=1
        # raw = 100*(0.45*1 + 0.25*0.667 + 0.15*1 + 0.15*1)
        # = 100*(0.45 + 0.167 + 0.15 + 0.15) = 100*0.917 = 91.7 → 92
        score = risk_score("critical", 90, 90, True, 7)
        assert score == 92


# ---------------------------------------------------------------------------
# evidence_summary
# ---------------------------------------------------------------------------


class TestEvidenceSummary:
    def test_known_code_contains_speed(self):
        summary = evidence_summary("Drowsiness", 72.0, "critical")
        assert "72" in summary

    def test_known_code_contains_severity(self):
        summary = evidence_summary("Yawning", 60.0, "high")
        assert "high" in summary

    def test_unknown_code_fallback(self):
        summary = evidence_summary("UNKNOWN_XYZ_CODE", 55.0, "low")
        assert "55" in summary
        assert len(summary) > 10


# ---------------------------------------------------------------------------
# cameras_from_videofiles — CONTRACT §2 (frozen)
# ---------------------------------------------------------------------------


class TestCamerasFromVideofiles:
    """CONTRACT §2: всегда ровно 3 камеры в порядке ADAS / DMS / СНЗ."""

    def _row(self, channel: int, download_status: str, **extra) -> dict:
        d = {"channel": str(channel), "download_status": download_status}
        d.update(extra)
        return d

    # ------------------------------------------------------------------
    # Always exactly 3 entries
    # ------------------------------------------------------------------

    def test_always_3_cameras_full(self):
        """Все каналы присутствуют → 3 камеры."""
        rows = [self._row(1, "downloaded"), self._row(5, "downloaded"), self._row(2, "downloaded")]
        cams = cameras_from_videofiles(rows)
        assert len(cams) == 3

    def test_always_3_cameras_empty(self):
        """Пустой список → всё равно 3 camera (все offline)."""
        cams = cameras_from_videofiles([])
        assert len(cams) == 3

    def test_always_3_cameras_partial(self):
        """Только ch1 → 3 камеры."""
        cams = cameras_from_videofiles([self._row(1, "downloaded")])
        assert len(cams) == 3

    # ------------------------------------------------------------------
    # Fixed order: ADAS / DMS / СНЗ
    # ------------------------------------------------------------------

    def test_order_adas_first(self):
        rows = [self._row(1, "downloaded"), self._row(5, "downloaded"), self._row(2, "downloaded")]
        cams = cameras_from_videofiles(rows)
        assert cams[0]["id"] == "CAM-01"

    def test_order_dms_second(self):
        rows = [self._row(1, "downloaded"), self._row(5, "downloaded"), self._row(2, "downloaded")]
        cams = cameras_from_videofiles(rows)
        assert cams[1]["id"] == "CAM-05"

    def test_order_snz_third_from_ch2(self):
        rows = [self._row(1, "downloaded"), self._row(5, "downloaded"), self._row(2, "downloaded")]
        cams = cameras_from_videofiles(rows)
        assert cams[2]["id"] == "CAM-02"

    def test_order_snz_third_from_ch3(self):
        rows = [self._row(1, "downloaded"), self._row(5, "downloaded"), self._row(3, "downloaded")]
        cams = cameras_from_videofiles(rows)
        assert cams[2]["id"] == "CAM-03"

    # ------------------------------------------------------------------
    # Canonical labels
    # ------------------------------------------------------------------

    def test_adas_label(self):
        cams = cameras_from_videofiles([self._row(1, "downloaded")])
        assert cams[0]["label"] == "ADAS · Фронт"

    def test_dms_label(self):
        cams = cameras_from_videofiles([self._row(5, "downloaded")])
        assert cams[1]["label"] == "DMS · Салон"

    def test_snz_label_from_ch2(self):
        rows = [self._row(2, "downloaded")]
        cams = cameras_from_videofiles(rows)
        assert cams[2]["label"] == "СНЗ · Доп."

    def test_snz_label_from_ch3(self):
        rows = [self._row(3, "downloaded")]
        cams = cameras_from_videofiles(rows)
        assert cams[2]["label"] == "СНЗ · Кузов"

    def test_snz_label_absent_placeholder(self):
        """Ни ch2, ни ch3 → placeholder "СНЗ · Доп."."""
        cams = cameras_from_videofiles([])
        assert cams[2]["label"] == "СНЗ · Доп."

    def test_snz_ch2_preferred_over_ch3(self):
        """Если оба ch2 и ch3 присутствуют — слот СНЗ использует ch2."""
        rows = [self._row(2, "downloaded"), self._row(3, "downloaded")]
        cams = cameras_from_videofiles(rows)
        assert cams[2]["label"] == "СНЗ · Доп."
        assert cams[2]["id"] == "CAM-02"

    # ------------------------------------------------------------------
    # Status: online / warning / offline
    # ------------------------------------------------------------------

    def test_downloaded_is_online(self):
        cams = cameras_from_videofiles([self._row(1, "downloaded")])
        assert cams[0]["status"] == "online"

    def test_partial_is_warning(self):
        cams = cameras_from_videofiles([self._row(1, "partial")])
        assert cams[0]["status"] == "warning"

    def test_unknown_nonempty_is_warning(self):
        """Любое непустое значение кроме 'downloaded' → warning."""
        cams = cameras_from_videofiles([self._row(1, "pending")])
        assert cams[0]["status"] == "warning"

    def test_failed_is_warning(self):
        """'failed' → warning (непустой, не 'downloaded')."""
        cams = cameras_from_videofiles([self._row(5, "failed")])
        assert cams[1]["status"] == "warning"

    def test_empty_status_is_offline(self):
        cams = cameras_from_videofiles([self._row(1, "")])
        assert cams[0]["status"] == "offline"

    def test_absent_channel_is_offline(self):
        """Отсутствующий канал → offline."""
        cams = cameras_from_videofiles([])
        assert cams[0]["status"] == "offline"  # ADAS absent
        assert cams[1]["status"] == "offline"  # DMS absent
        assert cams[2]["status"] == "offline"  # СНЗ absent

    # ------------------------------------------------------------------
    # hasVideo
    # ------------------------------------------------------------------

    def test_hasvideo_true_when_online(self):
        cams = cameras_from_videofiles([self._row(1, "downloaded")])
        assert cams[0]["hasVideo"] is True

    def test_hasvideo_true_when_warning(self):
        """warning → реальный файл есть, hasVideo = True."""
        cams = cameras_from_videofiles([self._row(1, "partial")])
        assert cams[0]["hasVideo"] is True

    def test_hasvideo_false_when_offline(self):
        cams = cameras_from_videofiles([])
        assert cams[0]["hasVideo"] is False

    def test_hasvideo_false_empty_status(self):
        cams = cameras_from_videofiles([self._row(1, "")])
        assert cams[0]["hasVideo"] is False

    # ------------------------------------------------------------------
    # offline_from / offline_to
    # ------------------------------------------------------------------

    def test_offline_keys_present(self):
        cams = cameras_from_videofiles([self._row(1, "downloaded")])
        for cam in cams:
            assert "offline_from" in cam
            assert "offline_to" in cam

    def test_online_offline_times_none(self):
        cams = cameras_from_videofiles([self._row(1, "downloaded")])
        assert cams[0]["offline_from"] is None
        assert cams[0]["offline_to"] is None

    def test_absent_channel_offline_times_none(self):
        """Канал отсутствует → offline_from/to = None."""
        cams = cameras_from_videofiles([])
        assert cams[0]["offline_from"] is None
        assert cams[0]["offline_to"] is None

    def test_warning_with_created_at_has_offline_from(self):
        """warning + created_at_utc → offline_from заполнен."""
        row = self._row(1, "partial", created_at_utc="2026-05-14T10:00:00Z")
        cams = cameras_from_videofiles([row])
        assert cams[0]["offline_from"] == "2026-05-14T10:00:00Z"
        assert cams[0]["offline_to"] is None

    def test_offline_status_with_empty_download_status_no_ts(self):
        """offline (пустой статус, нет ts) → offline_from = None."""
        cams = cameras_from_videofiles([self._row(1, "")])
        assert cams[0]["offline_from"] is None

    # ------------------------------------------------------------------
    # Dedup: first occurrence wins
    # ------------------------------------------------------------------

    def test_dedup_first_wins(self):
        rows = [self._row(1, "downloaded"), self._row(1, "partial")]
        cams = cameras_from_videofiles(rows)
        assert cams[0]["status"] == "online"  # first row wins

    # ------------------------------------------------------------------
    # Unknown channels ignored (don't leak into output)
    # ------------------------------------------------------------------

    def test_unknown_channel_ignored(self):
        """ch4 не входит ни в один из 3 слотов."""
        rows = [self._row(4, "downloaded"), self._row(1, "downloaded")]
        cams = cameras_from_videofiles(rows)
        assert len(cams) == 3
        ids = [c["id"] for c in cams]
        assert "CAM-04" not in ids


# ---------------------------------------------------------------------------
# telemetry_from_trackpoints
# ---------------------------------------------------------------------------


class TestTelemetryFromTrackpoints:
    def _make_rows(self, offsets_and_speeds: list[tuple[int, float]], event_ts: str) -> list[dict]:
        """Build synthetic track_points rows with given offsets from event_ts."""
        from datetime import timezone
        event_dt = datetime.fromisoformat(event_ts.replace("Z", "+00:00")).astimezone(timezone.utc)
        from datetime import timedelta
        rows = []
        for offset_s, speed in offsets_and_speeds:
            pt_dt = event_dt + timedelta(seconds=offset_s)
            rows.append({
                "timestamp_utc": pt_dt.isoformat(),
                "speed_kmh": str(speed),
            })
        return rows

    def _import_datetime(self):
        from datetime import datetime
        return datetime

    def test_basic_output_shape(self):
        rows = self._make_rows([(-30, 80.0), (0, 72.0), (30, 70.0)], "2026-05-15T10:00:00Z")
        result = telemetry_from_trackpoints(rows, "2026-05-15T10:00:00Z")
        assert len(result) == 3
        for pt in result:
            assert "ts_offset" in pt
            assert "speed" in pt
            assert "ax" in pt
            assert "ay" in pt

    def test_filtered_outside_60s(self):
        rows = self._make_rows([(-90, 80.0), (0, 72.0), (90, 70.0)], "2026-05-15T10:00:00Z")
        result = telemetry_from_trackpoints(rows, "2026-05-15T10:00:00Z")
        assert len(result) == 1
        assert result[0]["ts_offset"] == 0

    def test_first_point_ax_zero(self):
        rows = self._make_rows([(-30, 80.0), (0, 72.0)], "2026-05-15T10:00:00Z")
        result = telemetry_from_trackpoints(rows, "2026-05-15T10:00:00Z")
        assert result[0]["ax"] == 0.0

    def test_ax_derivative_nonzero_when_speed_changes(self):
        # Speed drops from 80 to 72 over 30 seconds → ax should be negative
        rows = self._make_rows([(-30, 80.0), (0, 72.0)], "2026-05-15T10:00:00Z")
        result = telemetry_from_trackpoints(rows, "2026-05-15T10:00:00Z")
        ax = result[1]["ax"]
        assert ax != 0.0
        assert ax < 0  # deceleration

    def test_ax_derivative_formula(self):
        # speed: 80 km/h → 72 km/h over 30s
        # Δv = (72-80)*1000/3600 = -8/3.6 ≈ -2.222 m/s
        # ax = -2.222 / 30 ≈ -0.074 m/s²
        rows = self._make_rows([(-30, 80.0), (0, 72.0)], "2026-05-15T10:00:00Z")
        result = telemetry_from_trackpoints(rows, "2026-05-15T10:00:00Z")
        expected_ax = round(((72.0 - 80.0) * 1000.0 / 3600.0) / 30.0, 3)
        assert result[1]["ax"] == pytest.approx(expected_ax, abs=1e-3)

    def test_ay_always_zero(self):
        rows = self._make_rows([(-30, 80.0), (0, 72.0)], "2026-05-15T10:00:00Z")
        result = telemetry_from_trackpoints(rows, "2026-05-15T10:00:00Z")
        for pt in result:
            assert pt["ay"] == 0.0

    def test_empty_rows(self):
        result = telemetry_from_trackpoints([], "2026-05-15T10:00:00Z")
        assert result == []

    def test_sorted_by_ts_offset(self):
        # Provide rows out of order
        rows = self._make_rows([(30, 70.0), (-30, 80.0), (0, 72.0)], "2026-05-15T10:00:00Z")
        result = telemetry_from_trackpoints(rows, "2026-05-15T10:00:00Z")
        offsets = [pt["ts_offset"] for pt in result]
        assert offsets == sorted(offsets)


# ---------------------------------------------------------------------------
# b14 · Enrichment hardening — DoD edge-cases поверх b2 (CONTRACT §2)
# Гейт b14: эти проверки фиксируют граничные ветки/детерминизм.
# ---------------------------------------------------------------------------


class TestB14RiskScoreHardening:
    """risk_score: clamp [0,100] на крайних входах + монотонность по severity."""

    def test_clamp_low_extreme(self):
        # speed=0, events=0, day, low → минимально возможный, всё ещё в [0,100]
        score = risk_score("low", 0.0, 90, False, 0)
        assert 0 <= score <= 100

    def test_clamp_high_extreme(self):
        # speed ≫ limit, events ≫ 7, critical, night → максимум, не выходит за 100
        score = risk_score("critical", 9999.0, 60, True, 9999)
        assert score == 100

    def test_clamp_zero_speed_limit_no_raise(self):
        # деление на 0 не должно падать
        score = risk_score("critical", 80.0, 0, True, 7)
        assert 0 <= score <= 100

    def test_unknown_severity_defaults_no_raise(self):
        # неизвестная severity → дефолтный вес (как low), без исключения/NULL
        score = risk_score("__UNKNOWN__", 70.0, 90, False, 3)
        assert isinstance(score, int)
        assert 0 <= score <= 100

    def test_monotonic_by_severity(self):
        # при фиксированных speed/limit/night/events: critical ≥ high ≥ medium ≥ low
        kw = dict(speed_kmh=80.0, speed_limit_kmh=90, is_night=True, events_last_7d=4)
        s_low = risk_score("low", **kw)
        s_med = risk_score("medium", **kw)
        s_high = risk_score("high", **kw)
        s_crit = risk_score("critical", **kw)
        assert s_crit >= s_high >= s_med >= s_low

    def test_result_always_int(self):
        for sev in ("low", "medium", "high", "critical"):
            assert isinstance(risk_score(sev, 55.0, 90, False, 2), int)


class TestB14SpeedLimitHardening:
    """speed_limit_for: неизвестный код → 90, без NULL/исключения."""

    def test_unknown_literal_defaults_to_90(self):
        assert speed_limit_for("__UNKNOWN__") == 90

    def test_empty_code_defaults_to_90(self):
        assert speed_limit_for("") == 90

    def test_unknown_never_none(self):
        assert speed_limit_for("__UNKNOWN__") is not None

    def test_evidence_summary_unknown_not_null(self):
        # label/«версия» неизвестного кода → дефолтный шаблон, без NULL
        summary = evidence_summary("__UNKNOWN__", 50.0, "low")
        assert summary is not None
        assert isinstance(summary, str) and len(summary) > 0


class TestB14CamerasHardening:
    """cameras: ровно 3, status ∈ {online,warning,offline}, no-video → offline."""

    _STATUSES = {"online", "warning", "offline"}

    def test_empty_yields_three_offline(self):
        cams = cameras_from_videofiles([])
        assert len(cams) == 3
        for cam in cams:
            assert cam["status"] == "offline"
            assert cam["hasVideo"] is False

    def test_status_always_in_enum(self):
        rows = [
            {"channel": "1", "download_status": "downloaded"},
            {"channel": "5", "download_status": "partial"},
            {"channel": "2", "download_status": ""},
        ]
        cams = cameras_from_videofiles(rows)
        assert len(cams) == 3
        for cam in cams:
            assert cam["status"] in self._STATUSES

    def test_missing_channel_offline_no_raise(self):
        # только ADAS — DMS/СНЗ отсутствуют, не падаем
        cams = cameras_from_videofiles([{"channel": "1", "download_status": "downloaded"}])
        assert len(cams) == 3
        assert cams[1]["status"] == "offline" and cams[1]["hasVideo"] is False
        assert cams[2]["status"] == "offline" and cams[2]["hasVideo"] is False


class TestB14IsNightBoundary:
    """is_night: граница [22, 06) детерминирована."""

    def test_22_is_night(self):
        assert is_night("2026-05-15T22:00:00Z") is True

    def test_06_is_day(self):
        assert is_night("2026-05-15T06:00:00Z") is False

    def test_05_59_is_night(self):
        assert is_night("2026-05-15T05:59:59Z") is True

    def test_21_59_is_day(self):
        assert is_night("2026-05-15T21:59:59Z") is False


class TestB14Determinism:
    """is_night / speed_limit_for / ax — один вход → один выход."""

    def test_is_night_stable(self):
        ts = "2026-05-15T23:10:00Z"
        assert is_night(ts) == is_night(ts) == is_night(ts)

    def test_speed_limit_stable(self):
        assert speed_limit_for("OVERSPEED") == speed_limit_for("OVERSPEED")

    def test_ax_stable(self):
        rows = [
            {"timestamp_utc": "2026-05-15T09:59:30Z", "speed_kmh": "80"},
            {"timestamp_utc": "2026-05-15T10:00:00Z", "speed_kmh": "72"},
        ]
        r1 = telemetry_from_trackpoints(rows, "2026-05-15T10:00:00Z")
        r2 = telemetry_from_trackpoints(rows, "2026-05-15T10:00:00Z")
        assert r1 == r2
        assert r1[0]["ax"] == 0.0  # первая точка — нет предыдущей


# Import datetime for helper
from datetime import datetime
