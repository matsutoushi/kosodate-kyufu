"""
Instagram リール(縦動画 1080x1920)の自動生成。
カルーセルと同じ配色・フォントで、数字のカウントアップなど動きのある短尺動画を作る。

実行: python pipeline/reel.py
出力: out/instagram/reels/<name>.mp4 (+ caption.txt)
ffmpeg は imageio-ffmpeg 同梱バイナリを使う(別途インストール不要)。
"""
import os
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from carousel import THEMES, font, EMOJI_FONT  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "instagram", "reels")

W, H = 1080, 1920
FPS = 30
MARGIN = 90


def ease_out(t):
    return 1 - (1 - t) ** 3


def emoji_layer(ch, size):
    f = ImageFont.truetype(EMOJI_FONT, size)
    layer = Image.new("RGBA", (size + 40, size + 40), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((10, 10), ch, font=f, embedded_color=True)
    return layer


def text_layer(text, f, fill):
    """複数行テキストをRGBAレイヤーに描く(中央揃え)。フェード合成用。"""
    lines = text.split("\n")
    lh = f.size + int(f.size * 0.4)
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    w = max(int(probe.textlength(ln, font=f)) for ln in lines) + 20
    h = lh * len(lines) + 20
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    y = 0
    for ln in lines:
        lw = d.textlength(ln, font=f)
        d.text(((w - lw) / 2, y), ln, font=f, fill=fill)
        y += lh
    return layer


def paste_center(img, layer, cy, alpha=1.0, dy=0):
    """レイヤーを横中央・指定Y(中心)に、透明度と縦オフセットつきで貼る。"""
    if alpha <= 0:
        return
    lay = layer
    if alpha < 1.0:
        lay = layer.copy()
        a = lay.getchannel("A").point(lambda v: int(v * alpha))
        lay.putalpha(a)
    x = (W - lay.width) // 2
    y = int(cy - lay.height / 2 + dy)
    img.paste(lay, (x, y), lay)


def render_018(T):
    """018サポートのカウントアップリール。約13秒。"""
    scenes = []

    # 事前レイヤー(毎フレーム作らない)
    hook1 = text_layer("東京都に\n住んでいる人へ", font(96), T["ink"])
    hook2 = text_layer("お子さん1人につき", font(64), T["sub"])
    em_money = emoji_layer("💰", 230)
    label_m = text_layer("月 5,000 円", font(88), T["ink"])
    label_y = text_layer("年間", font(72), T["sub"])
    warn = text_layer("でも、申請しないと", font(76), T["ink"])
    zero = text_layer("0 円", font(200), T["brand_d"])
    em_warn = emoji_layer("⚠️", 200)
    cta1 = text_layer("018サポート", font(88), T["brand_d"])
    cta2 = text_layer("対象かどうか、\nプロフィールのリンクから\n30秒でチェック", font(64), T["ink"])
    brand = text_layer("@こそだて給付ナビ", font(44), T["sub"])
    counter_font = font(170)

    def frame(t):
        img = Image.new("RGB", (W, H), T["bg"])
        d = ImageDraw.Draw(img)
        # 上下の帯(常時)
        d.rectangle([0, 0, W, 14], fill=T["brand"])
        d.rectangle([0, H - 14, W, H], fill=T["brand"])

        if t < 3.0:  # シーン1: フック
            p = ease_out(min(1, t / 0.6))
            paste_center(img, em_money, 620, alpha=p, dy=int((1 - p) * 60))
            paste_center(img, hook1, 940, alpha=p, dy=int((1 - p) * 80))
            if t > 1.0:
                p2 = ease_out(min(1, (t - 1.0) / 0.5))
                paste_center(img, hook2, 1180, alpha=p2)
        elif t < 7.5:  # シーン2: 月5,000円 → 年間カウントアップ
            tt = t - 3.0
            paste_center(img, label_m, 500, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.8:
                p = ease_out(min(1, (tt - 0.8) / 0.4))
                paste_center(img, label_y, 760, alpha=p)
                cp = ease_out(min(1, max(0.0, (tt - 1.2) / 2.2)))
                val = int(60000 * cp)
                txt = f"{val:,} 円"
                tw = d.textlength(txt, font=counter_font)
                d.text(((W - tw) / 2, 880), txt, font=counter_font, fill=T["brand_d"])
                if cp >= 1.0:
                    paste_center(img, text_layer("所得制限なし・第2子以降も同額", font(56), T["sub"]), 1250,
                                 alpha=ease_out(min(1, (tt - 3.6) / 0.5)))
        elif t < 10.5:  # シーン3: 申請しないと0円
            tt = t - 7.5
            paste_center(img, em_warn, 560, alpha=ease_out(min(1, tt / 0.4)))
            paste_center(img, warn, 860, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.6:
                p = min(1, (tt - 0.6) / 0.35)
                scale = 1.6 - 0.6 * ease_out(p)  # ドンと縮んで決まる
                z = zero.resize((int(zero.width * scale), int(zero.height * scale)))
                paste_center(img, z, 1120, alpha=p)
        else:  # シーン4: CTA
            tt = t - 10.5
            p = ease_out(min(1, tt / 0.5))
            paste_center(img, cta1, 700, alpha=p, dy=int((1 - p) * 40))
            paste_center(img, cta2, 980, alpha=ease_out(min(1, max(0.0, tt - 0.3) / 0.5)))
            paste_center(img, brand, 1780, alpha=p)
        return img

    return frame, 13.0


def encode(frame_fn, duration, name, caption=""):
    import imageio_ffmpeg
    os.makedirs(OUT, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="reel_")
    n = int(duration * FPS)
    for i in range(n):
        frame_fn(i / FPS).save(os.path.join(tmp, f"{i:04d}.png"))
    out = os.path.join(OUT, f"{name}.mp4")
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ff, "-y", "-framerate", str(FPS), "-i", os.path.join(tmp, "%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart", out],
                   check=True, capture_output=True)
    shutil.rmtree(tmp, ignore_errors=True)
    if caption:
        with open(os.path.join(OUT, f"{name}_caption.txt"), "w", encoding="utf-8") as f:
            f.write(caption.strip() + "\n")
    return out, n


CAPTION_018 = """【東京都民、申請しないと年6万円損します】

018(ゼロイチハチ)サポートの話です。

▶ 0〜18歳の子ども1人につき月5,000円(年6万円)
▶ 所得制限なし・第2子以降も同額
▶ 令和8年度も継続

ただし児童手当と違って、申請しないと振り込まれません。
対象なのに未申請の家庭が毎年あります。

プロフィールのリンクから、受け取れる制度を30秒でチェックできます。

※詳しくは東京都の公式ページでご確認ください。

#018サポート #東京都 #東京子育て #子育て #給付金 #ワーママ #新米ママ #プレママ #節約 #家計管理 #知って得する"""


def main():
    T = THEMES["mint"]
    frame_fn, dur = render_018(T)
    out, n = encode(frame_fn, dur, "018support", CAPTION_018)
    size = os.path.getsize(out) / 1024
    print(f"  018support.mp4: {dur}秒 / {n}フレーム / {size:.0f}KB → {out}")


if __name__ == "__main__":
    main()
