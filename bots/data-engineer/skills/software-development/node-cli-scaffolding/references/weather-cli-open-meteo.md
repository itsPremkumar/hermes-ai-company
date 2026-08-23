# weather-cli session reference (2026-08-01)

Project: `C:\one\weather-cli` — zero-dep TypeScript CLI, live Open-Meteo weather, 22/22 tests
green, committed locally (NO GitHub repo created per instruction). Uses the patterns in the
"Zero-dependency TypeScript CLI" section of SKILL.md.

## Open-Meteo API (free, no key, Node >= 18 global fetch)

- Geocoding: `https://geocoding-api.open-meteo.com/v1/search?name=<city>&count=1`
  - Response: `{ results: [{ name, latitude, longitude, country, admin1, timezone, population, ... }] }`
- Forecast: `https://api.open-meteo.com/v1/forecast?latitude=..&longitude=..&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m,precipitation&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto&forecast_days=N`
  - Unit switches: `temperature_unit=celsius|fahrenheit`, `wind_speed_unit=kmh|mph`, `precipitation_unit=mm|inch`
  - `timezone=auto` makes `daily.time` dates local; `current.time` carries an offset.
  - `forecast_days` 1-7 accepted (API allows up to 16).
- Env overrides for tests: `WEATHER_GEOCODE_BASE`, `WEATHER_API_BASE` (both default to the real
  base; strip trailing `/` with `new RegExp('/+$')`).

## WMO weather codes → icon/label (as implemented + tested)

| codes | label | emoji | ascii (--no-color) |
|---|---|---|---|
| 0 | Clear | ☀️ | [sun] |
| 1-3 | Partly cloudy | ⛅ | [clouds] |
| 45-48 | Fog | 🌫️ | [fog] |
| 51-67 | Rain | 🌧️ | [rain] |
| 71-77, 85-86 | Snow (+ snow showers) | 🌨️ | [snow] |
| 80-82 | Showers | 🌦️ | [showers] |
| 95-99 | Thunderstorm | ⛈️ | [storm] |
| else | Unknown | ❓ | [?] |

Use range checks (`code >= 51 && code <= 67`), NOT the sparse WMO list — unused in-range codes
(46, 47, 72, 74, 76...) should still resolve to their group.

## Color thresholds (metric °C)

- `>= 30` hot red `ESC[91m` · `<= 5` cold blue `ESC[94m` · else mild green `ESC[92m`
  (convert °F→°C first when units=imperial: `(f - 32) * 5 / 9`).
- Compass from degrees: `Math.round(((deg % 360) + 360) % 360 / 22.5) % 16` over the 16-point array.
  Verified: `windDirection(-10) === 'N'` (350° rounds to N, NOT NNW — write the test accordingly).

## Canned integration-test fixture (local node:http server)

- Server: `createServer` on `listen(0, '127.0.0.1')`, JSON responses, EXACT pathname match
  (`/search`, `/forecast`), default 500 for anything else (this default doubles as the HTTP-error test).
- Geocode hit: `{ name: 'Chennai', latitude: 13.08784, longitude: 80.27847, country: 'India',
  admin1: 'Tamil Nadu', timezone: 'Asia/Kolkata', population: 4681087 }`; unknown name → `{ results: [] }`.
- Forecast: `current: { time, temperature_2m: 31.2, relative_humidity_2m: 70, apparent_temperature: 35.1,
  weather_code: 2, wind_speed_10m: 12.3, wind_direction_10m: 160, precipitation: 0 }`,
  `daily: { time: ['2026-08-01','2026-08-02','2026-08-03'], weather_code: [2,80,95],
  temperature_2m_max: [33,29,28], temperature_2m_min: [27,25,24], precipitation_probability_max: [40,80,90] }`
- HTTP-error test: point `WEATHER_API_BASE` at `${base}/boom` → path `/boom/forecast` → server default
  500 → `assert.rejects(..., /HTTP 500/)`. Requires the exact-pathname fix (see SKILL.md).
- Null-tolerance test: `temperature_2m: null, weather_code: null` → parse to `NaN`/0, never throw.
- Cleanup: `server.closeAllConnections(); server.close();` in the `after()` hook (undici keep-alive
  sockets otherwise hold the test runner).

## Verified live demo (real Open-Meteo, 2026-08-01)

- `weather-cli Chennai --days 3` → boxed table: `⛅ 33.5°C Partly cloudy`, feels/humidity/wind/precip,
  3 daily rows (`Sat, Aug 1   🌦️ Showers  37.5°C / 27.6°C  precip 88%`).
- `weather-cli "New York" --days 2 --units imperial` → °F / mph / inches.
- `weather-cli --lat 48.8566 --lon 2.3522 --days 1` → coordinate mode (name "48.86, 2.35").
- `--json` → structured snapshot (`location`, `units`, `current`, `daily`, `fetchedAt`).
- Exit codes verified: unknown city → 1 + helpful message; no args / `--days 9` / `--bogus` → 2.
- Colors verified via `cat -v`: raw `^[[91m33.5°C^[[0m` — ANSI emits even when piped.

## Project layout (16 committed files)

`package.json` (type module, bin → dist/src/cli.js, scripts build=tsc / test=build+node --test 3
files, devDeps typescript + @types/node only) · `tsconfig.json` (ES2022/NodeNext, rootDir '.',
outDir dist, strict, include src+test) · `.gitignore` (node_modules/, dist/) · `.gitattributes`
(* text=auto eol=lf) · `LICENSE` (MIT 2026 Premkumar M) · `.github/workflows/ci.yml` (node 20/22
matrix, npm ci + npm test) · `src/{types,geocode,api,format,render,cli}.ts` ·
`test/{geocode,format,api}.test.ts` · `package-lock.json` · `README.md` (CI badge, usage, WMO table).
