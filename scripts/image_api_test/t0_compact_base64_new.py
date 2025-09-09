# save as t0_compact_base64.py
from typing import Literal
from datetime import datetime
import io, base64
import requests, numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates  # for "time" x_mode


def _fetch_t0_json(product: Literal["stock", "conbond"] = "stock"):
    url = f"http://192.168.2.{119 if product=='conbond' else 201}:8001/statistical/t0profit/cash"
    r = requests.get(url, timeout=5)
    r.raise_for_status()
    return r.json()


def _parse_series(data):
    times = []
    floatProfit_vals, settleProfit_vals = [], []
    buyMkt_vals, sellMkt_vals = [], []
    totalProfit_vals = []

    for item in data:
        dt = datetime.fromtimestamp(item["time"] / 1000.0)
        d = item["data"]
        fp = float(d.get("floatProfit", 0))
        sp = float(d.get("settleProfit", 0))
        bm = float(d.get("buyMkt", 0))
        sm = float(d.get("sellMkt", 0))

        times.append(dt)
        floatProfit_vals.append(fp)
        settleProfit_vals.append(sp)
        totalProfit_vals.append(fp + sp)
        buyMkt_vals.append(bm)
        sellMkt_vals.append(sm)

    turnover_vals = [b + s for b, s in zip(buyMkt_vals, sellMkt_vals)]
    latest_total_profit = totalProfit_vals[-1] if totalProfit_vals else 0.0
    latest_settle_profit = settleProfit_vals[-1] if settleProfit_vals else 0.0
    latest_float_profit = floatProfit_vals[-1] if floatProfit_vals else 0.0
    latest_total_turnover = turnover_vals[-1] if turnover_vals else 0.0
    rate_of_return_bp = (
        (latest_total_profit / latest_total_turnover * 10000)
        if latest_total_turnover
        else 0.0
    )

    return {
        "times": times,
        "total_profit": np.array(totalProfit_vals, dtype=float),
        "metrics": dict(
            total=latest_total_profit,
            settle=latest_settle_profit,
            float=latest_float_profit,
            return_bp=rate_of_return_bp,
        ),
    }


def render_compact_base64_from_api(
    product: Literal["stock", "conbond"] = "stock",
    *,
    width=296,
    height=152,
    dpi=100,
    show_zero_axis: bool = True,
    x_mode: Literal[
        "index", "time"
    ] = "index",  # 'index' 忽略時間、'time' 依實際時間間隔
    facecolor: str | None = None,  # 例如 "#E0E0E0" 做灰底
) -> str:
    """
    讀 API → 製作一張 296x152 的 PNG，回傳 base64（無 data: 前綴）。
    - show_zero_axis: 是否畫一條 y=0 的橫線
    - x_mode:
        'index' -> 連續索引，無中午休市的長水平線（預設）
        'time'  -> 使用實際 datetime 間距（會出現休市平線）
    - facecolor: 設定整體背景色（例如 '#E0E0E0' 做淺灰）
    """
    s = _parse_series(_fetch_t0_json(product))

    # --- 畫布 ---
    fig = plt.figure(figsize=(width / dpi, height / dpi), dpi=dpi, facecolor=facecolor)

    # --- 指標（上方文字） ---
    m = s["metrics"]
    fig.text(
        0.02,
        0.92,
        f"{product.capitalize()} Strategy Performance",
        fontsize=8,
        weight="bold",
    )
    fig.text(0.02, 0.78, f"Total: {m['total']:,.0f}", fontsize=8)
    fig.text(0.35, 0.78, f"Settle: {m['settle']:,.0f}", fontsize=8)
    fig.text(0.68, 0.78, f"Float: {m['float']:,.0f}", fontsize=8)
    fig.text(0.02, 0.64, f"Return: {m['return_bp']:.2f} bp", fontsize=8)

    # --- 收益曲線（下方） ---
    ax = fig.add_axes([0.06, 0.08, 0.90, 0.50])

    y = s["total_profit"]
    if len(y) == 0:
        y = np.array([0.0])
    if x_mode == "time" and len(s["times"]) == len(y):
        x = mdates.date2num(s["times"])
    else:
        x = np.arange(len(y))  # 忽略時間(預設)

    # y-limits：若需要 0 軸，確保 0 在範圍內
    ymin, ymax = float(y.min()), float(y.max())
    if show_zero_axis:
        ymin = min(ymin, 0.0)
        ymax = max(ymax, 0.0)
    pad = (ymax - ymin) * 0.07 if ymax > ymin else 1.0
    ax.set_ylim(ymin - pad, ymax + pad)
    ax.set_xlim(x.min(), x.max())

    # 曲線
    ax.plot(x, y, linewidth=1.6)

    # 0 軸（細線，e-ink 上比較乾淨）
    if show_zero_axis:
        ax.axhline(0, linewidth=0.8)

    # 極簡：關掉座標軸、格線
    ax.axis("off")

    # --- 輸出 base64 ---
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


if __name__ == "__main__":
    # 範例：忽略時間 + 0 軸 + 灰底
    b64 = render_compact_base64_from_api(
        product="stock",
        # product="conbond",
        show_zero_axis=True,
        x_mode="index",  # 改成 "time" 會依實際時間間隔
        # facecolor="#E0E0E0",  # 想要白底就設 None
        facecolor=None,  # 想要白底就設 None
    )
    # Flush to prevent broken pipe
    # [Python Print Flush: Complete Guide | by ryan | Medium](https://medium.com/@ryan_forrester_/python-print-flush-complete-guide-b10ab1512390)
    # https://chatgpt.com/share/68bffdd2-2e20-8012-bf7a-3a0cac109328
    print(b64, flush=True)
    # try:
    #     print(b64)
    # except BrokenPipeError:
    #     # 處理管道被提前關閉的情況（例如 head, grep 等命令）
    #     pass
