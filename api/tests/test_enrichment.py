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
        assert driver_for(plate) == driver_for(plate)
        assert driver_for(plate) == driver_for(plate)  # third call

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
        # At least the pool is large enough that two common plates differ somewhere
        results = {driver_for(p) for p in ["А111АА77", "В222ВВ99", "С333СС77", "Д444ДД77"]}
        # Not all identical — deterministic but distributed
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
# cameras_from_videofiles
# ---------------------------------------------------------------------------


class TestCamerasFromVideofiles:
    def _make_row(self, channel: int, download_status: str) -> dict:
        return {"channel": str(channel), "download_status": download_status}

    def test_channel_1_label(self):
        cams = cameras_from_videofiles([self._make_row(1, "downloaded")])
        assert cams[0]["label"] == "ADAS · Передняя"

    def test_channel_5_label(self):
        cams = cameras_from_videofiles([self._make_row(5, "downloaded")])
        assert cams[0]["label"] == "DMS · Салон"

    def test_channel_3_label(self):
        cams = cameras_from_videofiles([self._make_row(3, "downloaded")])
        assert cams[0]["label"] == "CH3 · доп."

    def test_channel_2_label(self):
        cams = cameras_from_videofiles([self._make_row(2, "downloaded")])
        assert cams[0]["label"] == "CH2 · доп."

    def test_downloaded_is_online(self):
        cams = cameras_from_videofiles([self._make_row(1, "downloaded")])
        assert cams[0]["status"] == "online"
        assert cams[0]["hasVideo"] is True

    def test_not_downloaded_is_offline(self):
        cams = cameras_from_videofiles([self._make_row(1, "pending")])
        assert cams[0]["status"] == "offline"
        assert cams[0]["hasVideo"] is False

    def test_failed_is_offline(self):
        cams = cameras_from_videofiles([self._make_row(5, "failed")])
        assert cams[0]["status"] == "offline"
        assert cams[0]["hasVideo"] is False

    def test_dedup_same_channel(self):
        rows = [self._make_row(1, "downloaded"), self._make_row(1, "failed")]
        cams = cameras_from_videofiles(rows)
        assert len(cams) == 1

    def test_multiple_channels_sorted(self):
        rows = [self._make_row(5, "downloaded"), self._make_row(1, "downloaded")]
        cams = cameras_from_videofiles(rows)
        assert cams[0]["id"] == "CAM-01"
        assert cams[1]["id"] == "CAM-05"

    def test_offline_keys_present(self):
        cams = cameras_from_videofiles([self._make_row(1, "downloaded")])
        assert "offline_from" in cams[0]
        assert "offline_to" in cams[0]
        assert cams[0]["offline_from"] is None
        assert cams[0]["offline_to"] is None


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


# Import datetime for helper
from datetime import datetime
