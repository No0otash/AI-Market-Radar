# Conflict Risk Monitor (additive module)

This feature is intentionally isolated from the existing bot. It adds:
- `src/conflict_risk_monitor.py`
- `.github/workflows/conflict-risk-monitor.yml`
- a separate scheduled GitHub Actions job that can post an alert to `@HuntFlo`

It does **not** import, patch, or change `src/main.py`, the existing market/news logic, the existing workflow, or `state.json`.

## What it currently monitors

1. **News signals:** BBC Middle East and Al Jazeera RSS by default. The feeds can be overridden with the `RISK_NEWS_FEEDS` environment variable (semicolon-separated RSS/Atom URLs). News is a triage signal, not proof.
2. **Persian Gulf / Strait of Hormuz shipping:** aggregate counts from the public Strait of Hormuz Ship Monitor API:
   - `https://hormuz.data-tracking.net/api/summary?hours=24`
   - `https://hormuz.data-tracking.net/api/crossings/daily?days=14`
   - The provider documents a 30-minute update cadence and CC BY 4.0 attribution for non-commercial research/publication. Credit the provider in derived public reports and confirm the license fits the channel's use.
3. **Flightradar24:** optional official API request for aggregate flight-position counts over a broad Persian Gulf/Gulf of Oman bounding box. Set the repository secret `FR24_API_TOKEN` to enable it. The official FR24 API is separate from the consumer Flightradar24 subscription and requires a paid API plan; do not enable it unless the owner accepts that cost. The monitor stores only the count, never raw flight positions, registrations, or callsigns. It respects a low result limit to constrain credit use.

Official API references:
- Flightradar24 API: https://fr24api.flightradar24.com/docs/getting-started
- FR24 endpoint overview: https://fr24api.flightradar24.com/docs/endpoints/overview
- Strait of Hormuz monitor API and terms: https://hormuz.data-tracking.net/api-docs

## GitHub Actions setup

The workflow runs every six hours and supports manual runs. It uses the existing repository secret `TELEGRAM_BOT_TOKEN` and sends only to `TELEGRAM_CHANNEL_ID` (falling back to `@HuntFlo`). The bot must already be an administrator in that channel. No secret values should be committed to Git.

Optional secret:
- `FR24_API_TOKEN`: a valid Flightradar24 API token. If absent, flight data is skipped and the run continues.

Optional repository/environment variables:
- `RISK_ALERT_THRESHOLD` (default `70`): heuristic index threshold from 0 to 100.
- `RISK_MIN_DOMAINS` (default `2`): minimum number of independent signal families required.
- `RISK_ALERT_COOLDOWN_HOURS` (default `24`).
- `FR24_LIMIT` (default `20`, hard-capped at 20).
- `FR24_BOUNDS` (default `31,22,45,62`, N,S,W,E).
- `RISK_NEWS_FEEDS`: semicolon-separated RSS/Atom feed URLs.

History is stored as a GitHub Actions cache containing daily aggregate observations only. The workflow does not write to the repository or change any existing bot state.

## Alert policy and limitations

- An alert requires a heuristic score of at least 70/100 **and** at least two elevated, independent signal families. Alerts are deduplicated; another alert requires the signal to leave the elevated state and re-enter it, or to rise at least 10 points after the cooldown.
- The score is **not a probability**. An index of 70/100 must never be described as a 70% chance of war.
- A flight-count change can be caused by ordinary airline schedules, weather, data coverage, or API limits. It is weak context only; no aircraft is classified as hostile or as preparing an attack.
- A fall in AIS-reported vessel crossings may reflect GPS/AIS interference, transponders being switched off, weather, or incomplete coverage. It is not proof of an attack or blockade.
- RSS keyword matches can miss context, repeat old events, or reflect inaccurate claims. Cross-source confirmation is required for the news family.
- The current score is a deliberately conservative **prototype**, not a calibrated forecasting model. Do not publish a numeric attack probability until a historical dataset has been labeled, the target event has a stable definition, and out-of-sample calibration has been tested (for example, Brier score and calibration plots).
- GitHub scheduled jobs are best-effort and may start late. This is not a real-time emergency alert system.

## Safe rollout

1. Open the pull request and review only the added files.
2. Confirm that the existing channel ID secret points to `@HuntFlo` or leave it unset to use the fallback.
3. Merge only after reviewing the diff. The monitor is a separate workflow and does not change `src/main.py`.
4. Run the workflow manually once and inspect its logs. A Telegram alert is sent only when the alert policy is met.
5. Add `FR24_API_TOKEN` only if the official paid API is acceptable. Without it, the monitor still uses news and shipping signals.

## Attribution

Shipping aggregates: Strait of Hormuz Ship Monitor, https://hormuz.data-tracking.net/ (CC BY 4.0 as documented by the provider). News headlines remain linked to their source. Flightradar24 data, if enabled, is subject to FR24 API terms and storage limits.
