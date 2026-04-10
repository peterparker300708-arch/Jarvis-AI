"""Bollinger Bands London-session scalp strategy for EUR/USD.

This module provides configuration, validation, and Pine Script v5 code
generation for the "ultimate" Bollinger Bands scalping strategy discussed
in the Jarvis AI assistant conversation.  The strategy targets the London
session on a 15-minute EUR/USD chart and incorporates:

* Bollinger Bands (20, 3) — mean-reversion entry on 3-SD band touch.
* 200 EMA trend filter — only trade in the direction of the macro trend.
* RSI (14) momentum filter — confirm exhaustion before entering.
* Dynamic Take Profit at the Middle Bollinger Band (20 SMA).
* Fixed 10-pip Stop Loss.
* One-trade-per-day limit on a $10,000 account (1 standard lot).
* Automatic session-end position close (07:00–16:00 UTC).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------


@dataclass
class BollingerStrategyConfig:
    """All tunable parameters for the BB London Scalp strategy.

    Attributes:
        bb_length: Look-back period for the Bollinger Bands SMA. Default 20.
        bb_mult: Number of standard deviations for the outer bands. Default 3.0.
        rsi_length: RSI indicator period. Default 14.
        rsi_oversold: RSI threshold below which price is considered oversold
            (buy signal). Default 30.
        rsi_overbought: RSI threshold above which price is considered
            overbought (sell signal). Default 70.
        ema_length: EMA period used as the macro trend filter. Default 200.
        tp_pips: Take-profit distance in pips (used as fallback if the middle
            band target is unavailable). Default 10.0.
        sl_pips: Stop-loss distance in pips. Default 10.0.
        lot_size: Position size in standard lots (1 lot = 100,000 units).
            Default 1.0.
        initial_capital: Starting account balance in USD. Default 10,000.
        session_start: London session open in "HHmm" format (UTC). Default
            "0700".
        session_end: London session close in "HHmm" format (UTC). Default
            "1600".
    """

    bb_length: int = 20
    bb_mult: float = 3.0
    rsi_length: int = 14
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    ema_length: int = 200
    tp_pips: float = 10.0
    sl_pips: float = 10.0
    lot_size: float = 1.0
    initial_capital: float = 10_000.0
    session_start: str = "0700"
    session_end: str = "1600"

    # Validation is run automatically after __init__ via __post_init__.
    def __post_init__(self) -> None:
        self.validate()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> None:
        """Raise *ValueError* if any parameter is out of its valid range."""
        if self.bb_length < 2:
            raise ValueError(f"bb_length must be >= 2, got {self.bb_length}")
        if self.bb_mult <= 0:
            raise ValueError(f"bb_mult must be > 0, got {self.bb_mult}")
        if self.rsi_length < 2:
            raise ValueError(f"rsi_length must be >= 2, got {self.rsi_length}")
        if not (0 < self.rsi_oversold < self.rsi_overbought < 100):
            raise ValueError(
                f"rsi thresholds must satisfy 0 < rsi_oversold ({self.rsi_oversold}) "
                f"< rsi_overbought ({self.rsi_overbought}) < 100"
            )
        if self.ema_length < 2:
            raise ValueError(f"ema_length must be >= 2, got {self.ema_length}")
        if self.tp_pips <= 0:
            raise ValueError(f"tp_pips must be > 0, got {self.tp_pips}")
        if self.sl_pips <= 0:
            raise ValueError(f"sl_pips must be > 0, got {self.sl_pips}")
        if self.lot_size <= 0:
            raise ValueError(f"lot_size must be > 0, got {self.lot_size}")
        if self.initial_capital <= 0:
            raise ValueError(f"initial_capital must be > 0, got {self.initial_capital}")
        self._validate_session_time(self.session_start, "session_start")
        self._validate_session_time(self.session_end, "session_end")
        if self.session_start >= self.session_end:
            raise ValueError(
                f"session_start ({self.session_start}) must be earlier "
                f"than session_end ({self.session_end})"
            )

    @staticmethod
    def _validate_session_time(value: str, name: str) -> None:
        if not value.isdigit() or len(value) != 4:
            raise ValueError(f"{name} must be a 4-digit string like '0700', got '{value}'")
        hours, minutes = int(value[:2]), int(value[2:])
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError(f"{name} '{value}' is not a valid HHmm time")

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return all parameters as a plain dictionary."""
        return {
            "bb_length": self.bb_length,
            "bb_mult": self.bb_mult,
            "rsi_length": self.rsi_length,
            "rsi_oversold": self.rsi_oversold,
            "rsi_overbought": self.rsi_overbought,
            "ema_length": self.ema_length,
            "tp_pips": self.tp_pips,
            "sl_pips": self.sl_pips,
            "lot_size": self.lot_size,
            "initial_capital": self.initial_capital,
            "session_start": self.session_start,
            "session_end": self.session_end,
        }

    @property
    def session_string(self) -> str:
        """Pine Script session string, e.g. ``'0700-1600'``."""
        return f"{self.session_start}-{self.session_end}"

    @property
    def qty_units(self) -> int:
        """Position size in currency units (lot_size × 100 000)."""
        return int(self.lot_size * 100_000)

    @property
    def risk_per_trade_usd(self) -> float:
        """Estimated USD risk per trade at 1 pip = $10 for 1 standard lot."""
        pip_value_usd = self.lot_size * 10.0
        return round(self.sl_pips * pip_value_usd, 2)

    @property
    def risk_percent(self) -> float:
        """Risk as a percentage of *initial_capital*."""
        return round(self.risk_per_trade_usd / self.initial_capital * 100, 2)


# ---------------------------------------------------------------------------
# Pine Script generator
# ---------------------------------------------------------------------------


class BollingerStrategyGenerator:
    """Generates TradingView Pine Script v5 code for the BB London Scalp strategy.

    The generated script implements the "ultimate" mean-reversion setup:

    1. **Session filter** — entries only within the configured London window.
    2. **One-trade-per-day limit** — prevents multiple entries on the same day.
    3. **200 EMA trend filter** — longs only above the EMA, shorts only below.
    4. **RSI (14) momentum filter** — longs require RSI < rsi_oversold (crossing
       back above), shorts require RSI > rsi_overbought (crossing back below).
    5. **BB (20, 3) entry** — price must close below the lower band (long) or
       above the upper band (short).
    6. **Dynamic TP** — profit target is the Middle Bollinger Band (20 SMA),
       yielding a better risk-to-reward ratio than a fixed 10-pip target.
    7. **Fixed SL** — stop loss is 10 pips below/above the entry candle.
    8. **Session-end close** — all open positions are closed when the London
       session ends to avoid overnight exposure.

    Args:
        config: Strategy parameters.  Defaults to ``BollingerStrategyConfig()``.
    """

    def __init__(self, config: BollingerStrategyConfig | None = None) -> None:
        self.config = config or BollingerStrategyConfig()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_pine_script(self) -> str:
        """Return the complete Pine Script v5 strategy as a string."""
        cfg = self.config
        session = cfg.session_string
        qty = cfg.qty_units

        script = f"""\
//@version=5
// ============================================================
// BB (20,3) London Scalp – Ultimate Edition
// Instrument : EUR/USD
// Timeframe  : 15 minutes (M15)
// Account    : ${cfg.initial_capital:,.0f}  |  Lot size: {cfg.lot_size} standard lot(s)
// ============================================================
strategy(
     title             = "BB ({cfg.bb_length},{cfg.bb_mult}) London Scalp – Ultimate",
     overlay           = true,
     initial_capital   = {int(cfg.initial_capital)},
     default_qty_type  = strategy.fixed,
     default_qty_value = {qty},
     currency          = currency.USD
)

// ──────────────────────────────────────────────────────────────
// INPUTS
// ──────────────────────────────────────────────────────────────
bb_length    = input.int({cfg.bb_length},   title = "BB Length")
bb_mult      = input.float({cfg.bb_mult},  title = "BB StdDev Multiplier", step = 0.1)
rsi_length   = input.int({cfg.rsi_length},  title = "RSI Length")
rsi_os       = input.float({cfg.rsi_oversold},  title = "RSI Oversold Level")
rsi_ob       = input.float({cfg.rsi_overbought},  title = "RSI Overbought Level")
ema_length   = input.int({cfg.ema_length}, title = "EMA Trend Filter Length")
sl_pips      = input.float({cfg.sl_pips},  title = "Stop Loss (Pips)")
session_time = input.session("{session}", title = "London Session (UTC)")

// ──────────────────────────────────────────────────────────────
// SESSION FILTER
// ──────────────────────────────────────────────────────────────
in_session = not na(time(timeframe.period, session_time + ":1234567", "UTC"))

// ──────────────────────────────────────────────────────────────
// ONE-TRADE-PER-DAY GUARD
// ──────────────────────────────────────────────────────────────
var int last_trade_day = na
can_trade_today = na(last_trade_day) or last_trade_day != dayofmonth(time)

// ──────────────────────────────────────────────────────────────
// INDICATORS
// ──────────────────────────────────────────────────────────────
// Bollinger Bands
basis = ta.sma(close, bb_length)
dev   = bb_mult * ta.stdev(close, bb_length)
upper = basis + dev
lower = basis - dev

// 200 EMA trend filter
ema200 = ta.ema(close, ema_length)

// RSI momentum filter
rsi_val = ta.rsi(close, rsi_length)

// ──────────────────────────────────────────────────────────────
// PLOTS
// ──────────────────────────────────────────────────────────────
plot(basis,  "BB Middle (TP target)", color = color.orange, linewidth = 1)
plot(upper,  "BB Upper",              color = color.blue,   linewidth = 1)
plot(lower,  "BB Lower",              color = color.blue,   linewidth = 1)
plot(ema200, "200 EMA",               color = color.purple, linewidth = 2)

// ──────────────────────────────────────────────────────────────
// ENTRY CONDITIONS
// ──────────────────────────────────────────────────────────────
// Long: price closes below lower band AND above 200 EMA (uptrend)
//       AND RSI crosses back above oversold level (exhaustion confirmed)
long_setup  = close < lower and close > ema200 and ta.crossover(rsi_val, rsi_os)
long_entry  = long_setup and in_session and can_trade_today and strategy.position_size == 0

// Short: price closes above upper band AND below 200 EMA (downtrend)
//        AND RSI crosses back below overbought level (exhaustion confirmed)
short_setup = close > upper and close < ema200 and ta.crossunder(rsi_val, rsi_ob)
short_entry = short_setup and in_session and can_trade_today and strategy.position_size == 0

// ──────────────────────────────────────────────────────────────
// EXECUTE ENTRIES
// ──────────────────────────────────────────────────────────────
if long_entry
    strategy.entry("Long", strategy.long)
    last_trade_day := dayofmonth(time)

if short_entry
    strategy.entry("Short", strategy.short)
    last_trade_day := dayofmonth(time)

// ──────────────────────────────────────────────────────────────
// EXIT LOGIC
// ──────────────────────────────────────────────────────────────
// Stop-loss: fixed {cfg.sl_pips} pips  (10 ticks = 1 pip on 5-digit brokers)
ticks_in_pip = 10
sl_ticks     = sl_pips * ticks_in_pip

// Take-profit: dynamic — target the Middle Bollinger Band (20 SMA).
// Using limit orders placed at the current 'basis' value.
// Because 'basis' changes each bar, we use strategy.exit with a
// 'limit' parameter recalculated on every bar when we are in a trade.

if strategy.position_size > 0   // we are long
    strategy.exit("Exit Long",  from_entry = "Long",  limit = basis, loss = sl_ticks)

if strategy.position_size < 0   // we are short
    strategy.exit("Exit Short", from_entry = "Short", limit = basis, loss = sl_ticks)

// ──────────────────────────────────────────────────────────────
// SESSION-END CLOSE
// ──────────────────────────────────────────────────────────────
// Close all open positions when the London session ends to avoid
// holding trades in low-liquidity hours.
if not in_session and strategy.position_size != 0
    strategy.close_all(comment = "Session End Close")
"""
        return script

    def describe(self) -> str:
        """Return a human-readable summary of the strategy configuration."""
        cfg = self.config
        lines = [
            "═" * 60,
            "  BB London Scalp – Ultimate Edition",
            "═" * 60,
            f"  Instrument     : EUR/USD",
            f"  Timeframe      : 15 minutes (M15)",
            f"  Session        : {cfg.session_start[:2]}:{cfg.session_start[2:]} – "
            f"{cfg.session_end[:2]}:{cfg.session_end[2:]} UTC (London)",
            "",
            "  INDICATORS",
            f"    Bollinger Bands : length={cfg.bb_length}, std={cfg.bb_mult}",
            f"    EMA (trend)     : {cfg.ema_length}-period EMA",
            f"    RSI (momentum)  : length={cfg.rsi_length}, "
            f"OS={cfg.rsi_oversold}, OB={cfg.rsi_overbought}",
            "",
            "  ENTRY RULES",
            "    Long  : close < lower BB  AND  close > 200 EMA",
            f"            AND  RSI crosses above {cfg.rsi_oversold}",
            "    Short : close > upper BB  AND  close < 200 EMA",
            f"            AND  RSI crosses below {cfg.rsi_overbought}",
            "",
            "  TRADE MANAGEMENT",
            f"    Stop Loss       : {cfg.sl_pips} pips (fixed)",
            "    Take Profit     : Middle BB (20 SMA) — dynamic",
            "    Max trades/day  : 1",
            f"    Position size   : {cfg.lot_size} lot ({cfg.qty_units:,} units)",
            "",
            "  RISK",
            f"    Initial capital : ${cfg.initial_capital:,.0f}",
            f"    Risk per trade  : ${cfg.risk_per_trade_usd:.2f} ({cfg.risk_percent:.1f}%)",
            "═" * 60,
        ]
        return "\n".join(lines)

    def get_summary(self) -> Dict[str, Any]:
        """Return strategy metadata as a plain dictionary (useful for APIs)."""
        cfg = self.config
        return {
            "name": f"BB ({cfg.bb_length},{cfg.bb_mult}) London Scalp – Ultimate",
            "instrument": "EUR/USD",
            "timeframe": "M15",
            "session": f"{cfg.session_start}-{cfg.session_end} UTC",
            "indicators": {
                "bollinger_bands": {"length": cfg.bb_length, "std_dev": cfg.bb_mult},
                "ema_trend_filter": {"length": cfg.ema_length},
                "rsi_momentum_filter": {
                    "length": cfg.rsi_length,
                    "oversold": cfg.rsi_oversold,
                    "overbought": cfg.rsi_overbought,
                },
            },
            "entry": {
                "long": f"close < lower BB AND close > {cfg.ema_length} EMA AND RSI crosses above {cfg.rsi_oversold}",
                "short": f"close > upper BB AND close < {cfg.ema_length} EMA AND RSI crosses below {cfg.rsi_overbought}",
            },
            "exit": {
                "stop_loss_pips": cfg.sl_pips,
                "take_profit": "Middle Bollinger Band (dynamic)",
                "session_end_close": True,
                "max_trades_per_day": 1,
            },
            "risk": {
                "initial_capital_usd": cfg.initial_capital,
                "lot_size": cfg.lot_size,
                "qty_units": cfg.qty_units,
                "risk_per_trade_usd": cfg.risk_per_trade_usd,
                "risk_percent": cfg.risk_percent,
            },
        }
