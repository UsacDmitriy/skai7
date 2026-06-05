"""Сервис домена reb (§7.2/§7.4/§7.5, идея #8 — РЭБ/GPS-разрывы).

Восстановление трека при подавлении GPS: разрывы навигации (period_type=3)
из view `v_reb` сшиваются точками соседних видимых периодов
(`navigation__track_points`) и видеокадрами (`video_events__video_files`),
попадающими во временные окна разрывов — доказательство, что ТС двигалось,
пока GPS «молчал». Репозиторного слоя не требует: читает view/таблицы напрямую
через `rows_to_dicts` (b5-хелпер), сборку в `RebRecovery` (§7.5) делает здесь.
"""

from __future__ import annotations

from datetime import datetime

import duckdb

from api.domain.entities import GapPeriod, GpsPoint, RebRecovery, VideoFrame
from api.repositories import rows_to_dicts


def _parse_ts(value: str | None) -> datetime | None:
    """ISO-таймстамп → aware `datetime`. Нормализует `Z` → `+00:00`.

    Формат точек навигации (`...+00:00`) и видео (`...Z`) различается — сравнение
    как строк некорректно, поэтому окна разрывов считаются по `datetime`.
    """
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def get_reb(
    db: duckdb.DuckDBPyConnection, id: str
) -> RebRecovery | None:
    """`RebRecovery` (§7.5) по `id` ТС (`vehicle_plate` ИЛИ `unit_id`).

    `None`, если по `id` нет данных навигации вовсе (роутер → 404). ТС с
    непрерывным треком (нет period_type=3) → валидный `RebRecovery` с пустыми
    `gap_periods` (а не 404).
    """
    # Существование + резолв госномера (id может быть plate или public_unit_id).
    base = rows_to_dicts(
        db.execute(
            'SELECT "vehicle_id" '
            'FROM "navigation__track_periods" '
            'WHERE "vehicle_id" = ? OR "public_unit_id" = ? '
            'LIMIT 1',
            [id, id],
        )
    )
    if not base:
        return None
    plate: str = base[0]["vehicle_id"]

    # Разрывы и соседние видимые периоды — из v_reb по ТС.
    reb_rows = rows_to_dicts(
        db.execute(
            'SELECT "start", "end", "duration_sec", "is_gap" '
            'FROM "v_reb" WHERE "vehicle_plate" = ?',
            [plate],
        )
    )

    # gap_periods: только разрывы (is_gap, т.е. period_type=3).
    gap_periods = [
        GapPeriod(
            start=str(r["start"] or ""),
            end=str(r["end"] or ""),
            duration_sec=max(0, int(r["duration_sec"] or 0)),
        )
        for r in reb_rows
        if r["is_gap"]
    ]

    # gps_track: точки видимых (is_gap=FALSE) соседних периодов вокруг разрывов.
    gps_rows = rows_to_dicts(
        db.execute(
            'SELECT tp."latitude" AS lat, tp."longitude" AS lon, '
            '       tp."timestamp" AS ts '
            'FROM "navigation__track_points" tp '
            'JOIN "v_reb" r '
            '  ON r."unit_id" = tp."public_unit_id" '
            ' AND r."date" = tp."date" '
            ' AND r."period_index" = tp."period_index" '
            'WHERE r."vehicle_plate" = ? AND r."is_gap" = FALSE '
            'ORDER BY tp."timestamp"',
            [plate],
        )
    )
    gps_track = [
        GpsPoint(lat=float(r["lat"]), lon=float(r["lon"]), ts=str(r["ts"]))
        for r in gps_rows
        if r["lat"] is not None and r["lon"] is not None
    ]

    # video_frames: кадры ТС, попадающие во временные окна разрывов.
    windows = [
        (s, e)
        for g in gap_periods
        if (s := _parse_ts(g.start)) is not None
        and (e := _parse_ts(g.end)) is not None
    ]
    video_frames: list[VideoFrame] = []
    if windows:
        frame_rows = rows_to_dicts(
            db.execute(
                'SELECT "event_begin_utc" AS ts, "channel", '
                '       "media_relative_path" AS url '
                'FROM "video_events__video_files" '
                'WHERE "unit_state_number" = ? '
                'ORDER BY "event_begin_utc"',
                [plate],
            )
        )
        for fr in frame_rows:
            fts = _parse_ts(fr["ts"])
            if fts is None:
                continue
            if any(start <= fts <= end for start, end in windows):
                video_frames.append(
                    VideoFrame(
                        ts=str(fr["ts"]),
                        channel=int(fr["channel"]),
                        url=str(fr["url"] or ""),
                    )
                )

    return RebRecovery(
        vehicle_plate=plate,
        gps_track=gps_track,
        gap_periods=gap_periods,
        video_frames=video_frames,
    )
