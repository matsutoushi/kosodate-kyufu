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


# --- マイルド案 -------------------------------------------------------------
# A案(濃いオレンジのベタ塗り + 白抜き「給付」)は視認性は高いが、
# 色の強さと「給付」の直接さで広告色が出る。以下は同じ可読性を保ったまま
# 圧を下げた案。地色を淡くする / 主役の文字を「こそだて」に移す のが基本方針。
CREAM_W = "#FFFEFC"
PEACH_L = "#FFE7DA"   # 淡いピーチ(地色用)
INK_S = "#5A4038"     # 茶みのあるインク。真っ黒より柔らかい
MINT_L = "#DFF1EE"
MINT_D = "#2F7D74"


def fit(d, text, target_w, start=320):
    """target_w に収まる最大のフォントを返す。"""
    size = start
    while size > 40 and d.textlength(text, font=font(size)) > target_w:
        size -= 6
    return font(size)


def icon_d():
    """D案: ふきだし + 「こそだて」。情報・会話の印象で金銭感が出ない。"""
    img = Image.new("RGB", (S, S), CREAM_W)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([90, 170, 910, 640], radius=90, fill=PEACH_L)
    # ふきだしのしっぽ
    d.polygon([(400, 630), (470, 745), (530, 630)], fill=PEACH_L)
    f = fit(d, "こそだて", 660, 240)
    center(d, "こそだて", f, 300, INK_S)
    center(d, "給付ナビ", font(120), 790, BRAND_D)
    return img


def icon_e():
    """E案: 淡いピーチのベタ + 「こそだて」主役。A案の色だけ和らげた形。"""
    img = Image.new("RGB", (S, S), PEACH_L)
    d = ImageDraw.Draw(img)
    f = fit(d, "こそだて", 780, 280)
    center(d, "こそだて", f, 270, INK_S)
    center(d, "給付ナビ", font(150), 600, BRAND_D)
    return img


def icon_f():
    """F案: クリーム地 + ピーチの丸に白抜き「給付」。A案の文字を残しつつ余白で圧を下げる。"""
    img = Image.new("RGB", (S, S), CREAM_W)
    d = ImageDraw.Draw(img)
    d.ellipse([110, 110, 890, 890], fill=BRAND)
    center(d, "こそだて", font(130), 300, "#FFFFFF")
    center(d, "給付", font(280), 450, "#FFFFFF")
    return img


def icon_g():
    """G案: 淡いミント。オレンジ(セール・お金)の連想そのものを外す。"""
    img = Image.new("RGB", (S, S), MINT_L)
    d = ImageDraw.Draw(img)
    f = fit(d, "こそだて", 780, 280)
    center(d, "こそだて", f, 270, "#25332F")
    center(d, "給付ナビ", font(150), 600, MINT_D)
    return img


def contact_sheet(items):
    """候補を並べた比較シート。実寸(小さいとき)の見え方も併記する。"""
    cell_w, cell_h = 620, 520
    cols = 2
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cell_w * cols, cell_h * rows + 90), "#FFFFFF")
    d = ImageDraw.Draw(sheet)
    center(d, "アイコン候補(左=拡大 / 右=実際の表示サイズ)", font(38), 26, "#2B2B33", w=cell_w * cols)
    for i, (name, img) in enumerate(items):
        ox = (i % cols) * cell_w
        oy = (i // cols) * cell_h + 90
        c = circle_preview(img, name)
        sheet.paste(c.resize((360, 360), Image.LANCZOS), (ox + 30, oy + 60))
        # 実寸(Instagramのプロフィール一覧はおよそ44px、投稿上部は32px)
        sheet.paste(c.resize((110, 110), Image.LANCZOS), (ox + 430, oy + 120))
        sheet.paste(c.resize((44, 44), Image.LANCZOS), (ox + 463, oy + 250))
        d.text((ox + 30, oy + 12), name, font=font(44), fill="#2B2B33")
        d.text((ox + 430, oy + 300), "44px", font=font(26), fill="#6B6B76")
    return sheet


def circle_preview(img, name):
    """実際の円形表示を確認するためのプレビュー(丸く切り抜き)。"""
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, S, S], fill=255)
    out = Image.new("RGB", (S, S), "#FFFFFF")
    out.paste(img, (0, 0), mask)
    return out


def main():
    # 採用案(E)だけを icon/ 直下に置き、比較用の他案は _candidates/ に隔離する。
    # 全案を平置きすると、どれをアップロードするのか分からなくなる。
    ADOPTED = "e"
    ARC = os.path.join(OUT, "_candidates")
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(ARC, exist_ok=True)
    made = []
    for name, fn in [("a", icon_a), ("b", icon_b), ("c", icon_c),
                     ("d", icon_d), ("e", icon_e), ("f", icon_f), ("g", icon_g)]:
        img = fn()
        c = circle_preview(img, name)
        made.append((name.upper() + "案", img))
        if name == ADOPTED:
            # アップロードするのはこの1枚
            img.save(os.path.join(OUT, "PROFILE-icon.png"))
            c.save(os.path.join(OUT, "PROFILE-icon-円形プレビュー.png"))
            print(f"  PROFILE-icon.png  ← 採用({name.upper()}案・これをアップロードする)")
        else:
            img.save(os.path.join(ARC, f"icon_{name}.png"))
            c.resize((120, 120), Image.LANCZOS).save(os.path.join(ARC, f"icon_{name}_small.png"))
            print(f"  _candidates/icon_{name}.png")
    soft = [x for x in made if x[0][0] in "DEFG"]
    contact_sheet(soft).save(os.path.join(ARC, "比較シート.png"))
    print(f"\n→ {OUT}")


if __name__ == "__main__":
    main()
