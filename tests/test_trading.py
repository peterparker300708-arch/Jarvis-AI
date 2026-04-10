"""Tests for the Bollinger Bands London Scalp trading strategy module."""

import pytest
from modules.trading.bollinger_strategy import BollingerStrategyConfig, BollingerStrategyGenerator


# ---------------------------------------------------------------------------
# BollingerStrategyConfig – defaults
# ---------------------------------------------------------------------------


def test_default_config_attributes():
    cfg = BollingerStrategyConfig()
    assert cfg.bb_length == 20
    assert cfg.bb_mult == 3.0
    assert cfg.rsi_length == 14
    assert cfg.rsi_oversold == 30.0
    assert cfg.rsi_overbought == 70.0
    assert cfg.ema_length == 200
    assert cfg.tp_pips == 10.0
    assert cfg.sl_pips == 10.0
    assert cfg.lot_size == 1.0
    assert cfg.initial_capital == 10_000.0
    assert cfg.session_start == "0700"
    assert cfg.session_end == "1600"


def test_session_string():
    cfg = BollingerStrategyConfig()
    assert cfg.session_string == "0700-1600"


def test_qty_units_one_lot():
    cfg = BollingerStrategyConfig(lot_size=1.0)
    assert cfg.qty_units == 100_000


def test_qty_units_half_lot():
    cfg = BollingerStrategyConfig(lot_size=0.5)
    assert cfg.qty_units == 50_000


def test_risk_per_trade_usd_default():
    # 1 lot × $10/pip × 10-pip SL = $100
    cfg = BollingerStrategyConfig()
    assert cfg.risk_per_trade_usd == 100.0


def test_risk_percent_default():
    # $100 / $10,000 = 1%
    cfg = BollingerStrategyConfig()
    assert cfg.risk_percent == 1.0


def test_to_dict_keys():
    cfg = BollingerStrategyConfig()
    d = cfg.to_dict()
    expected_keys = {
        "bb_length", "bb_mult", "rsi_length", "rsi_oversold", "rsi_overbought",
        "ema_length", "tp_pips", "sl_pips", "lot_size", "initial_capital",
        "session_start", "session_end",
    }
    assert set(d.keys()) == expected_keys


# ---------------------------------------------------------------------------
# BollingerStrategyConfig – validation
# ---------------------------------------------------------------------------


def test_validation_passes_for_valid_params():
    # Should not raise
    BollingerStrategyConfig(
        bb_length=14,
        bb_mult=2.5,
        rsi_length=10,
        rsi_oversold=25.0,
        rsi_overbought=75.0,
        ema_length=100,
        sl_pips=15.0,
        tp_pips=20.0,
        lot_size=0.1,
        initial_capital=5000.0,
        session_start="0800",
        session_end="1500",
    )


@pytest.mark.parametrize("bb_length", [0, 1, -5])
def test_invalid_bb_length(bb_length):
    with pytest.raises(ValueError, match="bb_length"):
        BollingerStrategyConfig(bb_length=bb_length)


@pytest.mark.parametrize("bb_mult", [0.0, -1.0])
def test_invalid_bb_mult(bb_mult):
    with pytest.raises(ValueError, match="bb_mult"):
        BollingerStrategyConfig(bb_mult=bb_mult)


@pytest.mark.parametrize("rsi_length", [0, 1])
def test_invalid_rsi_length(rsi_length):
    with pytest.raises(ValueError, match="rsi_length"):
        BollingerStrategyConfig(rsi_length=rsi_length)


def test_rsi_oversold_exceeds_overbought():
    with pytest.raises(ValueError, match="rsi thresholds"):
        BollingerStrategyConfig(rsi_oversold=70.0, rsi_overbought=30.0)


def test_rsi_equal_levels():
    with pytest.raises(ValueError, match="rsi thresholds"):
        BollingerStrategyConfig(rsi_oversold=50.0, rsi_overbought=50.0)


@pytest.mark.parametrize("ema_length", [0, 1, -10])
def test_invalid_ema_length(ema_length):
    with pytest.raises(ValueError, match="ema_length"):
        BollingerStrategyConfig(ema_length=ema_length)


@pytest.mark.parametrize("sl_pips", [0.0, -5.0])
def test_invalid_sl_pips(sl_pips):
    with pytest.raises(ValueError, match="sl_pips"):
        BollingerStrategyConfig(sl_pips=sl_pips)


@pytest.mark.parametrize("tp_pips", [0.0, -1.0])
def test_invalid_tp_pips(tp_pips):
    with pytest.raises(ValueError, match="tp_pips"):
        BollingerStrategyConfig(tp_pips=tp_pips)


@pytest.mark.parametrize("lot_size", [0.0, -0.1])
def test_invalid_lot_size(lot_size):
    with pytest.raises(ValueError, match="lot_size"):
        BollingerStrategyConfig(lot_size=lot_size)


@pytest.mark.parametrize("capital", [0.0, -1000.0])
def test_invalid_initial_capital(capital):
    with pytest.raises(ValueError, match="initial_capital"):
        BollingerStrategyConfig(initial_capital=capital)


@pytest.mark.parametrize("bad_time", ["070", "07000", "abcd", "25:00", "0760"])
def test_invalid_session_start(bad_time):
    with pytest.raises(ValueError):
        BollingerStrategyConfig(session_start=bad_time)


def test_session_start_after_end():
    with pytest.raises(ValueError, match="session_start"):
        BollingerStrategyConfig(session_start="1700", session_end="0700")


def test_session_start_equals_end():
    with pytest.raises(ValueError, match="session_start"):
        BollingerStrategyConfig(session_start="0700", session_end="0700")


# ---------------------------------------------------------------------------
# BollingerStrategyGenerator – Pine Script generation
# ---------------------------------------------------------------------------


@pytest.fixture
def generator():
    return BollingerStrategyGenerator()


def test_generate_returns_string(generator):
    script = generator.generate_pine_script()
    assert isinstance(script, str)
    assert len(script) > 100


def test_pine_script_version_tag(generator):
    script = generator.generate_pine_script()
    assert "//@version=5" in script


def test_pine_script_strategy_declaration(generator):
    script = generator.generate_pine_script()
    assert "strategy(" in script


def test_pine_script_initial_capital(generator):
    script = generator.generate_pine_script()
    assert "initial_capital   = 10000" in script


def test_pine_script_default_qty_value(generator):
    script = generator.generate_pine_script()
    assert "default_qty_value = 100000" in script


def test_pine_script_contains_bb_calculation(generator):
    script = generator.generate_pine_script()
    assert "ta.sma(close, bb_length)" in script
    assert "ta.stdev(close, bb_length)" in script


def test_pine_script_contains_ema_filter(generator):
    script = generator.generate_pine_script()
    assert "ta.ema(close, ema_length)" in script


def test_pine_script_contains_rsi_filter(generator):
    script = generator.generate_pine_script()
    assert "ta.rsi(close, rsi_length)" in script


def test_pine_script_rsi_crossover_entry(generator):
    script = generator.generate_pine_script()
    assert "ta.crossover(rsi_val, rsi_os)" in script
    assert "ta.crossunder(rsi_val, rsi_ob)" in script


def test_pine_script_dynamic_tp_at_basis(generator):
    script = generator.generate_pine_script()
    # TP should reference the middle band (basis), not a fixed pip count
    assert "limit = basis" in script


def test_pine_script_session_time_default(generator):
    script = generator.generate_pine_script()
    assert '"0700-1600"' in script


def test_pine_script_one_trade_per_day_guard(generator):
    script = generator.generate_pine_script()
    assert "last_trade_day" in script
    assert "can_trade_today" in script
    assert "dayofmonth(time)" in script


def test_pine_script_session_end_close(generator):
    script = generator.generate_pine_script()
    assert "strategy.close_all" in script
    assert "Session End Close" in script


def test_pine_script_long_entry_uses_ema_above(generator):
    script = generator.generate_pine_script()
    # Long entries should only fire when price is ABOVE the 200 EMA
    assert "close > ema200" in script


def test_pine_script_short_entry_uses_ema_below(generator):
    script = generator.generate_pine_script()
    # Short entries should only fire when price is BELOW the 200 EMA
    assert "close < ema200" in script


def test_custom_config_reflected_in_script():
    cfg = BollingerStrategyConfig(
        bb_length=14,
        bb_mult=2.0,
        rsi_length=10,
        rsi_oversold=25.0,
        rsi_overbought=75.0,
        ema_length=100,
        sl_pips=15.0,
        lot_size=2.0,
        initial_capital=20_000.0,
        session_start="0800",
        session_end="1500",
    )
    gen = BollingerStrategyGenerator(cfg)
    script = gen.generate_pine_script()
    assert "initial_capital   = 20000" in script
    assert "default_qty_value = 200000" in script
    assert '"0800-1500"' in script
    assert "input.int(14," in script
    assert "input.float(2.0," in script


# ---------------------------------------------------------------------------
# BollingerStrategyGenerator – describe / get_summary
# ---------------------------------------------------------------------------


def test_describe_returns_string(generator):
    desc = generator.describe()
    assert isinstance(desc, str)
    assert "EUR/USD" in desc
    assert "M15" in desc
    assert "London" in desc


def test_describe_contains_risk_info(generator):
    desc = generator.describe()
    assert "$10,000" in desc
    assert "1.0%" in desc


def test_get_summary_keys(generator):
    summary = generator.get_summary()
    assert "name" in summary
    assert "instrument" in summary
    assert "timeframe" in summary
    assert "indicators" in summary
    assert "entry" in summary
    assert "exit" in summary
    assert "risk" in summary


def test_get_summary_instrument(generator):
    summary = generator.get_summary()
    assert summary["instrument"] == "EUR/USD"


def test_get_summary_timeframe(generator):
    summary = generator.get_summary()
    assert summary["timeframe"] == "M15"


def test_get_summary_dynamic_tp(generator):
    summary = generator.get_summary()
    assert "Middle Bollinger Band" in summary["exit"]["take_profit"]


def test_get_summary_risk_values(generator):
    summary = generator.get_summary()
    risk = summary["risk"]
    assert risk["initial_capital_usd"] == 10_000.0
    assert risk["lot_size"] == 1.0
    assert risk["qty_units"] == 100_000
    assert risk["risk_per_trade_usd"] == 100.0
    assert risk["risk_percent"] == 1.0


def test_get_summary_max_trades_per_day(generator):
    summary = generator.get_summary()
    assert summary["exit"]["max_trades_per_day"] == 1


def test_get_summary_session_end_close(generator):
    summary = generator.get_summary()
    assert summary["exit"]["session_end_close"] is True
