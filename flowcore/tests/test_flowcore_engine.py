"""The engine on tiny cases worked out by hand (all spreads set to zero), plus statistical checks."""

import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest

from flowcore.engine import baselines
from flowcore.engine.time_to_gate import (TransferInputs, assess, draw_transfer, drivers,
                                          load_config, next_zone, rng_for)
from flowcore.engine.zones import load_zones

ROOT = Path(__file__).resolve().parents[2]
HKT = timezone(timedelta(hours=8))


def at(hour: int, minute: int) -> datetime:
    return datetime(2026, 11, 13, hour, minute, tzinfo=HKT)


@pytest.fixture(scope="module")
def zones():
    return load_zones(str(ROOT / "data" / "reference" / "hkg_zones.yaml"))


@pytest.fixture(scope="module")
def config():
    return load_config(str(ROOT / "config" / "engine.yaml"))


@pytest.fixture
def exact(config):
    """The real config with every spread set to zero, so results can be checked by hand."""
    flat = copy.deepcopy(config)
    flat["samples"] = 10
    for name in ("F", "J", "W", "Y"):
        flat["deplane"][name]["sd"] = 0
    for name in ("bus", "security", "walk_speed", "expedite"):
        flat[name]["sd"] = 0
    flat["train_sd"] = 0
    return flat


def test_hand_computed_transfer(exact, zones):
    # Business, stand W48 (west) → gate 64 (northwest), wave load 0.4.
    # deplane 5; no bus; security 7 + 9 × 0.4 = 10.6;
    # walk: |850 - 850| + 0 + 300 + 150 detour = 450 m ÷ 1.2 m/s = 375 s = 6.25 min.
    transfer = draw_transfer(TransferInputs("W48", "64", "J", wave_load=0.4), exact, zones, rng_for(1, "a"))
    assert transfer.deplane[0] == 5 and transfer.bus[0] == 0
    assert transfer.security[0] == pytest.approx(10.6)
    assert transfer.walk_m == 450 and transfer.walk[0] == pytest.approx(6.25)
    assert transfer.total[0] == pytest.approx(21.85)
    assert (transfer.from_zone, transfer.to_zone, transfer.remote) == ("west", "northwest", False)


def test_hand_computed_remote_stand_economy_back_row_with_expedite(exact, zones):
    # Economy back row from remote stand S108 → gate 23 (mid), wave load 1, escorted.
    # deplane 18; bus 10; security 7 + 9 = 16; walk: east (100) → mid (600) = 500 + 150 = 650 m = 9.03 min;
    # expedite -6. Total 47.03.
    inputs = TransferInputs("S108", "23", "Y", row_frac=1.0, wave_load=1.0, expedite=True)
    transfer = draw_transfer(inputs, exact, zones, rng_for(1, "b"))
    assert transfer.remote and transfer.bus[0] == 10 and transfer.deplane[0] == 18
    assert transfer.total[0] == pytest.approx(18 + 10 + 16 + 650 / 1.2 / 60 - 6)


def test_midfield_adds_the_train(exact, zones):
    transfer = draw_transfer(TransferInputs("W48", "210", "J"), exact, zones, rng_for(1, "c"))
    # west → midfield: 0 + 150 detour = 150 m = 2.08 min, plus the 6-minute train.
    assert transfer.walk[0] == pytest.approx(150 / 1.2 / 60 + 6)


def test_hand_computed_assessment(exact, zones):
    transfer = draw_transfer(TransferInputs("W48", "64", "J", wave_load=0.4), exact, zones, rng_for(1, "a"))
    # Inbound at gate 18:40, outbound 19:45 → gate close 19:30 → 50 min available, 21.85 needed.
    made = assess(at(18, 40), 0, transfer, at(19, 45), 0, exact)
    assert made.p_miss == 0.0 and made.gate_close == at(19, 30)
    assert made.minutes_available == 50 and made.minutes_needed == (22, 22)
    assert made.ready_p50 == at(18, 40) + timedelta(minutes=21.85)
    # Inbound 30 min later: 20 min available < 21.85 needed → certain miss.
    assert assess(at(19, 10), 0, transfer, at(19, 45), 0, exact).p_miss == 1.0
    # ... unless the outbound leaves 5 minutes late: a late outbound helps.
    assert assess(at(19, 10), 0, transfer, at(19, 45), 5.0, exact).p_miss == 0.0


def test_p_miss_rises_as_the_inbound_slips(config, zones):
    transfer = draw_transfer(TransferInputs("N64", "23", "Y", row_frac=0.8), config, zones, rng_for(7, "x"))
    noise = rng_for(7, "x", "inbound").normal(0, 6, config["samples"])
    chances = [assess(at(18, minute), noise, transfer, at(19, 45), 0, config).p_miss
               for minute in (20, 35, 50, 59)]
    # 85, 70, 55 and 46 minutes between gate arrival and departure.
    assert chances == sorted(chances) and chances[0] < 0.05 and chances[-1] > 0.7


def test_same_seed_same_answer_and_order_does_not_matter(config, zones):
    inputs = TransferInputs("N64", "23", "Y")
    first = draw_transfer(inputs, config, zones, rng_for(7, "conn-1")).total
    draw_transfer(inputs, config, zones, rng_for(7, "conn-2"))
    again = draw_transfer(inputs, config, zones, rng_for(7, "conn-1")).total
    assert np.array_equal(first, again)
    assert not np.array_equal(first, draw_transfer(inputs, config, zones, rng_for(8, "conn-1")).total)


def test_expedite_lowers_the_chance(config, zones):
    plain = draw_transfer(TransferInputs("N64", "23", "Y"), config, zones, rng_for(7, "e"))
    fast = draw_transfer(TransferInputs("N64", "23", "Y", expedite=True), config, zones, rng_for(7, "e"))
    without = assess(at(18, 50), 0, plain, at(19, 45), 0, config).p_miss
    assert assess(at(18, 50), 0, fast, at(19, 45), 0, config).p_miss < without


def test_typical_transfer_sits_inside_the_design_range(config, zones):
    """Calibration: typical Business transfer about 20 to 35 min, so with the 15-minute gate close
    it sits under Hong Kong's 50-minute minimum connecting time (docs/decisions.md)."""
    transfer = draw_transfer(TransferInputs("S23", "44", "J", wave_load=0.4), config, zones, rng_for(3, "m"))
    p10, p50, p90 = np.percentile(transfer.total, [10, 50, 90])
    assert 15 <= p10 < p50 < p90 <= 40
    assert p50 + config["gate_close_minutes"] <= 50


def test_drivers_name_the_biggest_causes(exact, zones):
    inputs = TransferInputs("S108", "64", "Y", row_frac=1.0, wave_load=1.0)
    transfer = draw_transfer(inputs, exact, zones, rng_for(1, "d"))
    found = drivers(transfer, 25, inputs, exact)
    assert [item["key"] for item in found] == ["inbound_delay", "remote_stand", "far_gate"]
    assert found[0]["minutes"] == 25 and "25 min late" in found[0]["text"]
    assert drivers(draw_transfer(TransferInputs("S23", "30", "J"), exact, zones, rng_for(1, "q")),
                   0, TransferInputs("S23", "30", "J"), exact) == []


def test_zone_thresholds_and_hysteresis():
    args = (0.20, 0.70, 0.05)
    assert next_zone(None, 0.19, *args) == "SAFE"
    assert next_zone(None, 0.20, *args) == "AT_RISK"
    assert next_zone(None, 0.71, *args) == "WONT_MAKE"
    # A status only changes once the chance clears the band.
    assert next_zone("SAFE", 0.22, *args) == "SAFE"
    assert next_zone("SAFE", 0.26, *args) == "AT_RISK"
    assert next_zone("AT_RISK", 0.17, *args) == "AT_RISK"
    assert next_zone("AT_RISK", 0.14, *args) == "SAFE"
    assert next_zone("AT_RISK", 0.73, *args) == "AT_RISK"
    assert next_zone("AT_RISK", 0.76, *args) == "WONT_MAKE"
    assert next_zone("WONT_MAKE", 0.67, *args) == "WONT_MAKE"
    assert next_zone("WONT_MAKE", 0.64, *args) == "AT_RISK"
    assert next_zone("SAFE", 0.80, *args) == "WONT_MAKE"


def test_baselines(config):
    assert baselines.r0_misses(at(19, 8), at(19, 45), config) is True     # 37 min
    assert baselines.r0_misses(at(19, 7), at(19, 45), config) is False    # 38 min
    assert baselines.r1_misses(at(19, 8), at(19, 45), 5, config) is False  # 37 + 5
    assert baselines.r1_misses(at(19, 8), at(19, 45), -9, config) is True  # early departures don't count
