# Video events dataset

Prepared for hackathon cases that combine video-alarm events with nearby telemetry tracks.

## Source period

- Alarm search window: base `2026-05-08T00:00:00Z` through `2026-05-15T00:00:00Z`; targeted Drowsiness/Smoking add-on `2026-05-12T00:00:00Z` through `2026-05-19T00:00:00Z`.
- Selected event windows: `2026-05-14`, `2026-05-15`, and `2026-05-18`.
- Track windows: about 15 minutes before each alarm begin and 15 minutes after each alarm end.

## Files

- `vehicles.csv` - the 21 selected vehicles and counts by dataset layer.
- `selected_video_alarms.csv` - 54 selected VA alarms, including 12 Smoking and 15 Drowsiness cases.
- `video_files.csv` - 94 downloaded `VaAlarmVideo` files with channel, media id, relative media path, size, duration, codec, and server filename metadata.
- `track_summary.csv` - one row per alarm track window.
- `track_periods.csv` - movement/parking/break periods returned by BO tracks.
- `track_points.csv` - point-level coordinates, speed, angle, course, and EW flag.
- `max_speed_points.csv` - max-speed points returned by the track endpoint.
- `work_rest_single_vehicle/` - one-vehicle subset for work/rest-mode cases: 6 Drowsiness alarms and 6 MP4 files for `У126ТК124` (`U126TK124`) on `2026-05-18`.

## Video download status

The event and video metadata methods worked:

- `GET /va/odata/VaAlarms`
- `GET /va/odata/VaAlarmVideo`

The binary media files were downloaded directly from the production media host:

- `GET https://vasign.skai.online/media-files/data/{VaAlarmVideo.Id}`

All 94 selected video files downloaded successfully as `video/mp4`; the per-file result is recorded in `video_files.csv` as `download_status=downloaded`. `local_path` and `media_relative_path` are relative to the archive/project root. The MCP `media.MediaFiles_get_media_files_data_va_alarms_by_id` wrapper returned `404` for these ids because the working endpoint is the regular media-data route on `vasign.skai.online`, not `/media-files/data/va-alarms/{id}`.
