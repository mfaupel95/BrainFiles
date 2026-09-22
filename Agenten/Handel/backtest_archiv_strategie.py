"""Archiv-Fremdstrategie (Harvard-Algorithmic-Trading-with-AI) mit LOKALEN Daten fahren.

Strategie unveraendert aus backtest/bb_squeeze_adx.py uebernommen
(Bollinger-Squeeze + Keltner = "TTM Squeeze", ADX>25 bestaetigt Trend,
Ausbruch long/short, TP 5 % / SL 3 %).

Nur geaendert: Datenquelle (lokal statt Mac-Pfad), Gebuehr als Parameter,
Optimierung abgeschaltet (Dauer), Buy-and-Hold als Vergleich.
"""
import json
from pathlib import Path
import pandas as pd
import talib
from backtesting import Backtest, Strategy

# Pfade relativ zur eigenen Datei (SSD-umzugsfaehig, keine absoluten
# Benutzerpfade): Agenten/Handel/<datei> -> parents[2] ist die Wurzel.
WURZEL = Path(__file__).resolve().parents[2]
REPO = WURZEL / "Werkstatt" / "Repos" / "Harvard-Algorithmic-Trading-with-AI" / "backtest" / "data"


def lade_harvard(datei="BTC-1h-1000wks-data.csv"):
    p = REPO / datei
    df = pd.read_csv(p, parse_dates=["datetime"], index_col="datetime")
    df.columns = ["Open", "High", "Low", "Close", "Volume"]
    return df


def lade_frisch():
    """Agenten/Handel/kerzen_BTC-USDT_1H_8760.json - 1 Jahr Stundenkerzen bis heute."""
    p = WURZEL / "Agenten" / "Handel" / "kerzen_BTC-USDT_1H_8760.json"
    with open(p, "r", encoding="utf-8") as f:
        roh = json.load(f)
    if roh and isinstance(roh[0], dict):
        df = pd.DataFrame(roh)
    else:
        breite = len(roh[0])
        df = pd.DataFrame(roh)
        if breite == 5:  # Hausformat: [ts, o, h, l, c] ohne Volumen
            df.columns = ["datetime", "Open", "High", "Low", "Close"]
            df["Volume"] = 0.0
        else:
            df = df.iloc[:, :6]
            df.columns = ["datetime", "Open", "High", "Low", "Close", "Volume"]
    df["datetime"] = pd.to_datetime(df["datetime"].astype("int64"), unit="ms", errors="coerce")
    df = df.dropna(subset=["datetime"]).set_index("datetime").sort_index()
    for c in ["Open", "High", "Low", "Close", "Volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype(float)
    return df.dropna()


class BBSqueezeADX(Strategy):
    bb_window = 20
    bb_std = 2.0
    keltner_window = 20
    keltner_atr_mult = 1.5
    adx_period = 14
    adx_threshold = 25
    take_profit = 0.05
    stop_loss = 0.03

    def init(self):
        self.upper_bb, self.middle_bb, self.lower_bb = self.I(
            talib.BBANDS, self.data.Close, self.bb_window, self.bb_std, self.bb_std)
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, self.keltner_window)
        self.keltner_middle = self.I(talib.SMA, self.data.Close, self.keltner_window)
        self.upper_kc = self.I(lambda: self.keltner_middle + self.keltner_atr_mult * self.atr)
        self.lower_kc = self.I(lambda: self.keltner_middle - self.keltner_atr_mult * self.atr)
        self.squeeze = self.I(lambda: (self.upper_bb < self.upper_kc) & (self.lower_bb > self.lower_kc))
        self.adx = self.I(talib.ADX, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        self.squeeze_released = False

    def next(self):
        if len(self.data) < max(self.bb_window, self.keltner_window, self.adx_period):
            return
        squeeze_now = self.squeeze[-1]
        squeeze_prev = self.squeeze[-2] if len(self.data) > (max(self.bb_window, self.keltner_window) + 1) else True
        if squeeze_prev and not squeeze_now:
            self.squeeze_released = True
        if self.squeeze_released and self.adx[-1] > self.adx_threshold:
            if self.data.Close[-1] > self.upper_bb[-1] and not self.position:
                self.buy(sl=self.data.Close[-1] * (1 - self.stop_loss),
                         tp=self.data.Close[-1] * (1 + self.take_profit))
                self.squeeze_released = False
            elif self.data.Close[-1] < self.lower_bb[-1] and not self.position:
                self.sell(sl=self.data.Close[-1] * (1 + self.stop_loss),
                          tp=self.data.Close[-1] * (1 - self.take_profit))
                self.squeeze_released = False


def lauf(name, df, gebuehr):
    n = len(df)
    zeit = f"{df.index[0]:%Y-%m-%d} -> {df.index[-1]:%Y-%m-%d}"
    bt = Backtest(df, BBSqueezeADX, cash=100000, commission=gebuehr, exclusive_orders=False)
    stats = bt.run()
    kauf_halten = (df["Close"].iloc[-1] / df["Close"].iloc[0] - 1) * 100
    print(f"\n### {name}  |  {n} Kerzen  |  {zeit}  |  Gebuehr {gebuehr*100:.2f}% je Seite")
    print(f"  Rendite Strategie : {stats['Return [%]']:+8.2f} %   (Buy&Hold {kauf_halten:+8.2f} %)")
    print(f"  Trades            : {stats['# Trades']}")
    print(f"  Trefferquote      : {stats['Win Rate [%]']:.1f} %")
    print(f"  Max Drawdown      : {stats['Max. Drawdown [%]']:.2f} %")
    print(f"  SQN               : {stats.get('SQN', float('nan')):.2f}")
    print(f"  Profilfaktor      : {stats.get('Profit Factor', float('nan')):.2f}")
    print(f"  Erwartung/Trade   : {stats.get('Avg. Trade [%]', float('nan')):+.3f} %")
    return stats


if __name__ == "__main__":
    print("=" * 78)
    print("ARCHIV-STRATEGIE: Bollinger-Squeeze + Keltner + ADX (Harvard-Repo, Original-Code)")
    print("=" * 78)

    hist = lade_harvard("BTC-1h-1000wks-data.csv")
    lauf("BTC 1h, 9 Jahre (Originaldaten des Repos)", hist, 0.002)
    lauf("BTC 1h, 9 Jahre, Gebuehr der Haus-Spuren (0,05 %)", hist, 0.0005)

    for d in ("BTC-6h-1000wks-data.csv", "ETH-1d-1000wks-data.csv", "SOL-1d-1000wks-data.csv"):
        try:
            lauf(d.replace("-1000wks-data.csv", ""), lade_harvard(d), 0.0005)
        except Exception as e:
            print(f"  {d}: nicht gelaufen - {e}")

    try:
        frisch = lade_frisch()
        lauf("BTC 1h, frische Hausdaten (bis heute)", frisch, 0.0005)
    except Exception as e:
        print(f"  Frischdaten: nicht gelaufen - {type(e).__name__}: {e}")
