# SKAI Vibe Sprint 2026 datasets

Prepared from `source_data.xlsx`, local ZiS fuel reports in `Топливо/`, and SKAI MCP/API raw responses saved in `datasets/raw/`.

Full usage instructions: see `USAGE_GUIDE.md`.

SKAI MCP continuation notes for future agents: see `SKAI_MCP_USAGE.md`.

## Periods

- Fuel / ZiS / fuel cards: `2026-04-27` through `2026-05-03`.
- Sensor and navigation target vehicles: `2026-05-04` through `2026-05-10`.
- Video alarm event pack: base window `2026-05-08T00:00:00Z` through `2026-05-15T00:00:00Z`, plus a targeted Drowsiness/Smoking add-on from `2026-05-12T00:00:00Z` through `2026-05-19T00:00:00Z`.

## Folders

- `fuel_reconciliation/` - fuel card transactions, ZiS refuel/drain events, per-vehicle summaries, reconciliation rows, station summary.
- `sensor_diagnostics/` - target vehicles from the `БВ` sheet, public statistics, online snapshots, BO sensor catalog, graph fetch status, and point-level sensor graph values.
- `navigation_problem_tracks/` - vehicles from the `Навигация` sheet, problem descriptions, daily mileage/speed statistics, BO track fetch status, track periods, and point-level tracks.
- `normal_tracks_zis/` - ZiS vehicles suitable as normal/reference vehicles for cases that need non-problem context.
- `video_events/` - 21 vehicles with VA alarm events, downloaded video clips, video-file metadata, BO track windows around each selected event, and `work_rest_single_vehicle/` as a compact one-vehicle work/rest-mode subset.
- `reference/` - match tables between source vehicle labels and SKAI ids.

## API coverage note

The SKAI MCP BO catalog now exposes point-level methods used in this pack:

- `bo_statistics.CalculateGraphByUnitIdV2` (`POST /statistics/units/graph/V2`) for sensor graph points.
- `bo_composer.Tracks_get_api_tracks_by_unit` (`GET /api/tracks/by-unit`) for telemetry track points with coordinates, speed, angle, course, and EW flag.
- `bo_composer.GetSensors` (`GET /api/sensors/{terminalId}`) for sensor catalog metadata.
- `bo_va.odata/VaAlarms` and `bo_va.odata/VaAlarmVideo` for video-alarm event metadata.
- `GET https://vasign.skai.online/media-files/data/{VaAlarmVideo.Id}` for downloaded video binaries. The `media.MediaFiles_get_media_files_data_va_alarms_by_id` wrapper was also checked, but these VA video ids are served by the regular media-data route.

The exact historical report named `Сообщения от объекта` was not present in the catalog, so these BO graph/track responses are included as the closest message-level source alongside aggregate public statistics.

The BO extraction was scaled day-by-day for `2026-05-04` through `2026-05-10`: all 7 matched `БВ` vehicles for sensor graph points and all 5 matched `Навигация` vehicles for track points. See `sensor_graph_status.csv` and `track_fetch_status.csv` for empty/error days.

## Unmatched source vehicles

- `B927YM-797`
