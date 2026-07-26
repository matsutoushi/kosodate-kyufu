"""
Instagram プロフィール画像を生成する。
円形にトリミングされ、実際は直径40px程度で表示されるため
「小さくても読める」ことを最優先にする(要素を詰め込まない)。

出力: out/instagram/icon/icon_a.png ほか
"""
import os

from PIL import Image, ImageDraw

from carousel import font  # フォント解決を共用

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "instagram", "icon")

S = 1000  # 大きめに作る(Instagram側で縮小される)
CREAM = "#FFFDF9"
INK = "#2B2B33"
BRAND = "#FF8A65"
BRAND_D = "#F4643B"
PEACH = "#FFD9C9"
ACCENT = "#4DB6AC"


def center(d, text, f, y, fill, w=S):
    x = (w - d.textlength(text, font=f)) / 2
    d.text((x, y), text, font=f, fill=fill)


def icon_a():
    """A案: ブランド色ベタ + 「給付」大きく。最も視認性が高い。"""
    img = Image.new("RGB", (S, S), BRAND)
    d = ImageDraw.Draw(img)
    center(d, "こそだて", font(150), 210, "#FFFFFF")
    center(d, "給付", font(330), 400, "#FFFFFF")
    return img


def icon_b():
    """B案: クリーム地 + コインのモチーフ。やわらかい印象。"""
    img = Image.new("RGB", (S, S), CREAM)
    d = ImageDraw.Draw(img)
    # コイン
    d.ellipse([300, 150, 700, 550], fill=PEACH, outline=BRAND, width=14)
    center(d, "¥", font(240), 235, BRAND_D)
    center(d, "こそだて", font(120), 610, INK)
    center(d, "給付ナビ", font(120), 760, INK)
    return img


def icon_c():
    """C案: 上下2色。ブランドらしさと可読性の折衷。"""
    img = Image.new("RGB", (S, S), CREAM)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, S, 480], fill=PEACH)
    center(d, "もらえる", font(140), 190, BRAND_D)
    center(d, "お金", font(300), 340, INK)
    center(d, "こそだて給付ナビ", font(96), 730, "#8A5A44")
    return img


def circle_preview(img, name):
    """実際の円形表示を確認するためのプレビュー(丸く切り抜き)。"""
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, S, S], fill=255)
    out = Image.new("RGB", (S, S), "#FFFFFF")
    out.paste(img, (0, 0), mask)
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, fn in [("a", icon_a), ("b", icon_b), ("c", icon_c)]:
        img = fn()
        img.save(os.path.join(OUT, f"icon_{name}.png"))
        # 円形&小サイズのプレビューも出す(実際の見え方の確認用)
        c = circle_preview(img, name)
        c.save(os.path.join(OUT, f"icon_{name}_circle.png"))
        c.resize((120, 120), Image.LANCZOS).save(os.path.join(OUT, f"icon_{name}_small.png"))
        print(f"  icon_{name}.png (+円形/小サイズのプレビュー)")
    print(f"\n→ {OUT}")


if __name__ == "__main__":
    main()
