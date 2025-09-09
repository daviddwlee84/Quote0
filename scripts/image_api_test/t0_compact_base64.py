# save as t0_compact_base64.py
from typing import Literal
from datetime import datetime
import io, base64
import requests, numpy as np, pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _is_all_zero(lst):
    return all((v or 0) == 0 for v in lst)


def _fetch_t0_json(product: Literal["stock", "conbond"] = "stock"):
    url = f"http://192.168.2.{119 if product=='conbond' else 201}:8001/statistical/t0profit/cash"
    r = requests.get(url, timeout=5)
    r.raise_for_status()
    return r.json()


def _parse_series(data):
    times = []
    floatProfit_vals, settleProfit_vals = [], []
    duoFloat_vals, kongFloat_vals = [], []
    duoMkt_vals, kongMkt_vals = [], []
    buyMkt_vals, sellMkt_vals = [], []
    totalProfit_vals = []

    for item in data:
        dt = datetime.fromtimestamp(item["time"] / 1000.0)
        d = item["data"]
        fp = float(d.get("floatProfit", 0))
        sp = float(d.get("settleProfit", 0))
        df = float(d.get("duo", {}).get("float", 0))
        kf = float(d.get("kong", {}).get("float", 0))
        dm = float(d.get("duo", {}).get("mkt", 0))
        km = float(d.get("kong", {}).get("mkt", 0))
        bm = float(d.get("buyMkt", 0))
        sm = float(d.get("sellMkt", 0))

        times.append(dt)
        floatProfit_vals.append(fp)
        settleProfit_vals.append(sp)
        totalProfit_vals.append(fp + sp)
        duoFloat_vals.append(df)
        kongFloat_vals.append(kf)
        duoMkt_vals.append(dm)
        kongMkt_vals.append(km)
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
        "float_profit": np.array(floatProfit_vals, dtype=float),
        "settle_profit": np.array(settleProfit_vals, dtype=float),
        "turnover": np.array(turnover_vals, dtype=float),
        "metrics": dict(
            total=latest_total_profit,
            settle=latest_settle_profit,
            float=latest_float_profit,
            return_bp=rate_of_return_bp,
        ),
    }


def render_compact_base64_from_api(
    product: Literal["stock", "conbond"] = "stock", width=296, height=152, dpi=100
) -> str:
    """
    讀 API → 製作一張 296x152 的 PNG，回傳 base64（無 data: 前綴）。
    """
    data = _fetch_t0_json(product)
    s = _parse_series(data)

    # --- 版面：上方文字指標 + 下方收益曲線 ---
    fig = plt.figure(figsize=(width / dpi, height / dpi), dpi=dpi)

    # Header (簡短指標) —— 小螢幕上用短字串最清楚
    m = s["metrics"]
    fig.text(0.02, 0.92, "Key Metrics", fontsize=8, weight="bold")
    fig.text(0.02, 0.78, f"Total: {m['total']:,.0f}", fontsize=8)
    fig.text(0.35, 0.78, f"Settle: {m['settle']:,.0f}", fontsize=8)
    fig.text(0.68, 0.78, f"Float: {m['float']:,.0f}", fontsize=8)
    fig.text(0.02, 0.64, f"Return: {m['return_bp']:.2f} bp", fontsize=8)

    # Profit curve（去軸、滿版）
    ax = fig.add_axes([0.06, 0.08, 0.90, 0.50])
    y = s["total_profit"]
    x = np.arange(len(y)) if len(y) > 0 else np.arange(1)
    ax.plot(x, y, linewidth=1.6)  # 預設顏色，e-ink 清晰
    if len(y) > 0:
        ymin, ymax = float(y.min()), float(y.max())
        pad = (ymax - ymin) * 0.07 if ymax > ymin else 1.0
        ax.set_ylim(ymin - pad, ymax + pad)
    ax.set_xlim(x.min(), x.max())
    ax.axis("off")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi)
    plt.close(fig)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return b64


if __name__ == "__main__":
    # Example: 直接印 base64（貼進你的 JSON "image"）
    # b64 = render_compact_base64_from_api(product="stock")
    b64 = render_compact_base64_from_api(product="conbond")
    print(b64)
