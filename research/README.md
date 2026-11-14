# Research

The backtest and the evidence on the impact panel (AGENTS.md §9). It runs the same parser and engine as the app
(`flowcore`). `research/` never imports `backend/`; the policy replay, which needs the backend's simulation, lives
in `scripts/`.

## Reproduce every number

```
make data-down                                   # the stored HKIA days from S3 into data/raw/hkia
uv run python -m flowresearch.build_scenario     # data/scenarios/2026-10-22-evening (OAG calls cached)
uv run python -m flowresearch.backtest           # data/backtest.json
uv run python scripts/build_evidence.py          # data/evidence.json (shown on /impact)
```

## Notebooks (charts for the presentation)

Both are saved with their outputs, so they open ready to read. `make notebooks` re-runs them from the stored data
(no outside calls, about 4 minutes). Charts share one style (`flowresearch/charts.py`); tables come from
`flowresearch/eda.py` and the backtest's own records (`backtest.build_records`).

- **`notebooks/01_gate_planner_road_and_terminal.ipynb`:** the Google Routes road times, the terminal zone and
  walking model, when gates are published, and a worked Gate Planner example.
- **`notebooks/02_flight_data_and_model_accuracy.ipynb`:** the 91 days of flight data, tight connections and break
  rates, how accurate OAG's in-flight estimates are, the engine's accuracy and calibration, and what each
  ingredient added.

## What the backtest measures

- **Data:** every Cathay-operated arrival and departure at Hong Kong, 2026-08-15 to 2026-11-13 (HKIA, REAL).
- **Tight connections:** Cathay → Cathay, 50 to 89 minutes scheduled, plausible route, neither cancelled.
- **"Broke":** the real gate-arrival time plus one passenger's transfer time is later than the real gate close
  (15 min before the later of scheduled and actual departure). The transfer time is drawn from the engine's model
  (ASSUMED, `config/engine.yaml`). There are no public passenger outcomes.
- **Training and test:** delay histories come from the first 30 days only; scores are reported on the other 61.
- **Forecasts compared:**
  - **Fixed 38-minute rule:** it never flags a 50–89 minute connection.
  - **Engine a day ahead:** from the schedule and delay history only.
  - **Engine 90 minutes before landing:** with an in-flight estimate exactly as wrong as OAG's estimates measured on
    30 real arrivals (typically ±11 min, 4 min early on average).

## Limits

- **Transfer times are a model, not measured.** The backtest tests the timing forecast, not the transfer model.
- **In-flight error comes from one evening.** It was measured on 30 flights; a larger OAG pull would firm it up.
- **No trained model.** Delays use empirical distributions from history (no LightGBM), and nothing is uploaded to
  `models/`.
