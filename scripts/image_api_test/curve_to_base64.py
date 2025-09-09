# save as curve_to_base64.py
import io
import base64
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def curve_to_base64(
    y,
    x=None,
    width=296,
    height=152,
    dpi=100,
    line_width=1.8,
    line_color="black",  # e-ink 上黑線最清楚
    bg_color="white",  # 背景白；要灰底可改 "#808080"
    remove_axes=True,
):
    """
    將曲線轉為 PNG（width×height 像素），並回傳 base64（不含 data URI 前綴）。
    """
    y = np.asarray(y)
    if x is None:
        x = np.arange(len(y))
    else:
        x = np.asarray(x)

    # 圖片尺寸： inches = 像素 / dpi
    fig = plt.figure(figsize=(width / dpi, height / dpi), dpi=dpi, facecolor=bg_color)
    ax = fig.add_axes([0, 0, 1, 1])  # 滿版無邊距
    ax.plot(x, y, linewidth=line_width, color=line_color)
    ax.set_xlim(x.min(), x.max())

    # 一點 padding，避免線貼邊
    ymin, ymax = y.min(), y.max()
    pad = (ymax - ymin) * 0.05 if ymax > ymin else 1.0
    ax.set_ylim(ymin - pad, ymax + pad)

    if remove_axes:
        ax.axis("off")
    else:
        ax.set_frame_on(False)

    # 存成 PNG 並轉 base64（單行）
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi)
    plt.close(fig)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return b64


if __name__ == "__main__":
    # ---- 範例數據：做一條隨機但上升的「收益」曲線 ----
    np.random.seed(42)
    t = np.linspace(0, 6 * 60, 200)  # 6 小時、200 點
    noise = np.random.normal(0, 0.5, t.shape)
    trend = np.piecewise(
        t,
        [t < 60, (t >= 60) & (t < 120), t >= 120],
        [
            lambda u: 0.1 * u,
            lambda u: 6 + 0.02 * (u - 60),
            lambda u: 7 + 0.03 * (u - 120),
        ],
    )
    profit = (trend + np.cumsum(noise) * 0.02) * 1000

    b64 = curve_to_base64(profit, x=t, width=296, height=152, line_width=1.6)
    print(b64)  # 直接印出；複製後貼進 JSON 的 "image" 欄位即可
