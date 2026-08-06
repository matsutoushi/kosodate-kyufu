"""
Instagram カルーセル画像の自動生成。
data/posts.json の投稿定義 → out/instagram/<post_id>/01.png ... を出力。

サイズは 1080x1350(4:5)。Instagramのフィードで最も縦に大きく表示される比率。
実行: python pipeline/carousel.py
"""
import json
import os
import textwrap

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS = os.path.join(ROOT, "data", "posts.json")
OUT = os.path.join(ROOT, "out", "instagram", "carousels")

W, H = 1080, 1350
MARGIN = 80

# 配色テーマ。投稿ごとに変えて、並んだときの単調さを避ける。
# サイトのブランド(温かみ・信頼)から外れない範囲で振り幅を持たせている。
THEMES = {
    "peach": {  # 基本。温かい
        "bg": "#FFFDF9", "ink": "#2B2B33", "sub": "#6B6B76",
        "brand": "#FF8A65", "brand_d": "#F4643B", "accent": "#4DB6AC",
        "tint": "#FFD9C9", "soft": "#FFF5EF", "note_bg": "#F2FAF8", "note_ink": "#3F6F69",
    },
    "mint": {  # 爽やか。データ系の回に
        "bg": "#FAFDFC", "ink": "#25332F", "sub": "#63756F",
        "brand": "#4DB6AC", "brand_d": "#2F8A80", "accent": "#F4643B",
        "tint": "#CDEBE6", "soft": "#EFF9F7", "note_bg": "#FFF5EF", "note_ink": "#8A5A44",
    },
    "lavender": {  # 落ち着き。制度の解説回に
        "bg": "#FCFBFE", "ink": "#2C2838", "sub": "#6B6478",
        "brand": "#9B8AD4", "brand_d": "#6F5CB5", "accent": "#E8A33D",
        "tint": "#E2DBF5", "soft": "#F4F1FC", "note_bg": "#FDF6EA", "note_ink": "#8A6A2F",
    },
    "navy": {  # 信頼・比較。ランキングや地域比較に
        "bg": "#F7F9FC", "ink": "#1F2A3C", "sub": "#5C6B82",
        "brand": "#3D6EA8", "brand_d": "#2A5285", "accent": "#E8A33D",
        "tint": "#D5E2F2", "soft": "#EDF3FA", "note_bg": "#FDF6EA", "note_ink": "#7A5C22",
    },
    "coral": {  # 明るい。行動を促す回に
        "bg": "#FFFBFA", "ink": "#33262A", "sub": "#7A6569",
        "brand": "#EF6E7B", "brand_d": "#D14757", "accent": "#3FA796",
        "tint": "#FBD5D9", "soft": "#FEF0F1", "note_bg": "#EFF9F7", "note_ink": "#2F6F66",
    },
}
THEME_ORDER = ["peach", "mint", "lavender", "navy", "coral"]

# 現在のテーマ(build_post のたびに差し替える)
T = THEMES["peach"]

FONT_DIR = "C:/Windows/Fonts"
CANDIDATES = ["NotoSansJP-VF.ttf", "YuGothB.ttc", "meiryob.ttc", "YuGothR.ttc", "meiryo.ttc"]


def font(size, bold=True):
    """日本語フォントを返す。太字優先で探す。"""
    order = CANDIDATES if bold else ["YuGothR.ttc", "meiryo.ttc", "NotoSansJP-VF.ttf"]
    for name in order:
        p = os.path.join(FONT_DIR, name)
        if os.path.exists(p):
            try:
                f = ImageFont.truetype(p, size)
                # 可変フォントは太さを指定
                if name.endswith("-VF.ttf"):
                    try:
                        f.set_variation_by_name("Bold" if bold else "Regular")
                    except Exception:
                        pass
                return f
            except Exception:
                continue
    return ImageFont.load_default()


def text_h(draw, s, f, width, spacing):
    lines = wrap(draw, s, f, width)
    return len(lines) * (line_h(f) + spacing)


def line_h(f):
    return f.size + int(f.size * 0.35)


def wrap(draw, s, f, width):
    """日本語は単語区切りがないので1文字ずつ測って折り返す。"""
    lines, cur = [], ""
    for ch in s:
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        t = cur + ch
        if draw.textlength(t, font=f) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def draw_wrapped(draw, xy, s, f, fill, width, spacing=8, center=False):
    x, y = xy
    for ln in wrap(draw, s, f, width):
        if center:
            w = draw.textlength(ln, font=f)
            draw.text((x + (width - w) / 2, y), ln, font=f, fill=fill)
        else:
            draw.text((x, y), ln, font=f, fill=fill)
        y += line_h(f) + spacing
    return y


def rounded(draw, box, r, fill, outline=None, w=0):
    draw.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=w)


EMOJI_FONT = "C:/Windows/Fonts/seguiemj.ttf"


def draw_emoji(img, ch, size, xy):
    """Windowsのカラー絵文字(COLR)を描く。文字だけの単調さを解消する視覚アンカー。"""
    try:
        f = ImageFont.truetype(EMOJI_FONT, size)
        layer = Image.new("RGBA", (size + 40, size + 40), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((10, 10), ch, font=f, embedded_color=True)
        img.paste(layer, xy, layer)
    except Exception:
        pass


def deco_corner(d):
    """右上にテーマ色のやわらかい円。余白の単調さを消す。"""
    d.ellipse([W - 240, -160, W + 160, 240], fill=T["soft"])


def base(bg=None):
    img = Image.new("RGB", (W, H), bg or T["bg"])
    return img, ImageDraw.Draw(img)


def footer_brand(draw, dark=False):
    f = font(30, bold=True)
    c = "#FFFFFF" if dark else T["sub"]
    draw.text((MARGIN, H - 78), "@こそだて給付ナビ", font=f, fill=c)
    draw.text((W - MARGIN - draw.textlength("kosodate-kyufu.com", font=f), H - 78),
              "kosodate-kyufu.com", font=f, fill=c)


# ---- スライド種別 -----------------------------------------------------------

def slide_cover(s):
    """表紙。ここで指を止めさせる。layoutで見た目を変えられる。"""
    layout = s.get("layout", "band")
    if layout == "full":
        return _cover_full(s)
    if layout == "split":
        return _cover_split(s)
    return _cover_band(s)


def _cover_band(s):
    """上に色帯。落ち着いた定番。"""
    img, d = base()
    d.rectangle([0, 0, W, 300], fill=T["tint"])
    if s.get("eyebrow"):
        d.text((MARGIN, 90), s["eyebrow"], font=font(38), fill=T["brand_d"])
    y = max(200, 360)
    f = font(int(s.get("size", 92)))
    y = draw_wrapped(d, (MARGIN, y), s["title"], f, T["ink"], W - MARGIN * 2, spacing=18)
    if s.get("sub"):
        y += 40
        y = draw_wrapped(d, (MARGIN, y), s["sub"], font(42, bold=False), T["sub"], W - MARGIN * 2, spacing=12)
    if s.get("emoji"):
        ez = 210
        draw_emoji(img, s["emoji"], ez, (int((W - ez) / 2), max(int(y) + 30, H - 500)))
    rounded(d, [MARGIN, H - 250, W - MARGIN, H - 150], 50, T["brand"])
    t = s.get("cta", "スワイプで見る →")
    f3 = font(44)
    d.text(((W - d.textlength(t, font=f3)) / 2, H - 228), t, font=f3, fill="#FFFFFF")
    footer_brand(d)
    return img


def _cover_full(s):
    """全面ブランド色。白抜きで強い。数字やニュース性の高い回に。"""
    img, d = base(T["brand"])
    if s.get("eyebrow"):
        rounded(d, [MARGIN, 96, MARGIN + 40 + int(d.textlength(s["eyebrow"], font=font(36))), 168], 36, "#FFFFFF")
        d.text((MARGIN + 20, 110), s["eyebrow"], font=font(36), fill=T["brand_d"])
    y = 260
    f = font(int(s.get("size", 92)))
    y = draw_wrapped(d, (MARGIN, y), s["title"], f, "#FFFFFF", W - MARGIN * 2, spacing=18)
    if s.get("sub"):
        y += 44
        y = draw_wrapped(d, (MARGIN, y), s["sub"], font(42, bold=False), "#FFF0E9", W - MARGIN * 2, spacing=12)
    if s.get("emoji"):
        ez = 210
        draw_emoji(img, s["emoji"], ez, (int((W - ez) / 2), max(int(y) + 30, H - 500)))
    rounded(d, [MARGIN, H - 250, W - MARGIN, H - 150], 50, "#FFFFFF")
    t = s.get("cta", "スワイプで見る →")
    f3 = font(44)
    d.text(((W - d.textlength(t, font=f3)) / 2, H - 228), t, font=f3, fill=T["brand_d"])
    footer_brand(d, dark=True)
    return img


def _cover_split(s):
    """下半分が色面。タイトルを上に置いて視線を上から下へ運ぶ。"""
    img, d = base()
    d.rectangle([0, int(H * 0.52), W, H], fill=T["tint"])
    if s.get("eyebrow"):
        d.text((MARGIN, 110), s["eyebrow"], font=font(38), fill=T["brand_d"])
    y = 200
    f = font(int(s.get("size", 92)))
    y = draw_wrapped(d, (MARGIN, y), s["title"], f, T["ink"], W - MARGIN * 2, spacing=18)
    if s.get("sub"):
        y = max(y + 40, int(H * 0.52) + 60)
        y = draw_wrapped(d, (MARGIN, y), s["sub"], font(42, bold=False), T["note_ink"], W - MARGIN * 2, spacing=12)
    if s.get("emoji"):
        ez = 210
        draw_emoji(img, s["emoji"], ez, (int((W - ez) / 2), max(int(y) + 30, H - 500)))
    rounded(d, [MARGIN, H - 250, W - MARGIN, H - 150], 50, T["brand"])
    t = s.get("cta", "スワイプで見る →")
    f3 = font(44)
    d.text(((W - d.textlength(t, font=f3)) / 2, H - 228), t, font=f3, fill="#FFFFFF")
    footer_brand(d)
    return img


def slide_point(s, idx=None, total=None):
    """本文スライド。1枚1メッセージ。"""
    img, d = base()
    if s.get("emoji"):
        deco_corner(d)
        draw_emoji(img, s["emoji"], 120, (W - MARGIN - 130, 78))
    y = 100
    if idx:
        # 番号バッジ
        rounded(d, [MARGIN, y, MARGIN + 110, y + 66], 33, T["brand"])
        f = font(38)
        t = f"{idx}"
        d.text((MARGIN + (110 - d.textlength(t, font=f)) / 2, y + 10), t, font=f, fill="#FFFFFF")
        y += 100

    f = font(int(s.get("size", 66)))
    tw = W - MARGIN * 2 - (150 if s.get("emoji") else 0)
    y = draw_wrapped(d, (MARGIN, y), s["title"], f, T["ink"], tw, spacing=16)

    if s.get("amount"):
        y += 30
        aw = W - MARGIN * 2 - 80
        # 1行に収まるよう文字を少しずつ小さくする(下限46)。それでも入らなければ折り返す
        fa = font(64)
        for size in range(64, 44, -4):
            fa = font(size)
            if d.textlength(s["amount"], font=fa) <= aw:
                break
        lines = wrap(d, s["amount"], fa, aw)
        pad = 34
        h = len(lines) * line_h(fa) + pad * 2 - int(fa.size * 0.35)
        rounded(d, [MARGIN, y, W - MARGIN, y + h], 28, T["soft"], outline=T["brand"], w=3)
        draw_wrapped(d, (MARGIN + 40, y + pad), s["amount"], fa, T["brand_d"], aw, spacing=0, center=True)
        y += h + 30

    if s.get("body"):
        y += 20
        fb = font(42, bold=False)
        y = draw_wrapped(d, (MARGIN, y), s["body"], fb, T["sub"], W - MARGIN * 2, spacing=14)

    if s.get("note"):
        fn = font(36, bold=False)
        lines = wrap(d, s["note"], fn, W - MARGIN * 2 - 60)
        h = len(lines) * (line_h(fn) + 10) + 40
        yy = H - 190 - h
        rounded(d, [MARGIN, yy, W - MARGIN, yy + h], 20, T["note_bg"])
        d.rectangle([MARGIN, yy, MARGIN + 8, yy + h], fill=T["accent"])
        draw_wrapped(d, (MARGIN + 34, yy + 20), s["note"], fn, T["note_ink"], W - MARGIN * 2 - 60, spacing=10)

    footer_brand(d)
    return img


def slide_list(s):
    """リスト型(ランキングや一覧)。"""
    img, d = base()
    y = 100
    f = font(60)
    y = draw_wrapped(d, (MARGIN, y), s["title"], f, T["ink"], W - MARGIN * 2, spacing=14)
    y += 40

    fi = font(44)
    fs = font(30, bold=False)
    fnum = font(32)
    for i, item in enumerate(s["items"], 1):
        rowh = 122
        if y + rowh > H - 220:
            break
        bg = "#FFFFFF" if i % 2 else T["soft"]
        rounded(d, [MARGIN, y, W - MARGIN, y + rowh - 14], 18, bg)
        # 番号
        d.ellipse([MARGIN + 24, y + 30, MARGIN + 76, y + 82], fill=T["brand"])
        t = str(i)
        d.text((MARGIN + 24 + (52 - d.textlength(t, font=fnum)) / 2, y + 42), t, font=fnum, fill="#FFFFFF")
        # 本文(名前と補足が重ならないよう行間を確保)
        d.text((MARGIN + 104, y + 22), item["name"], font=fi, fill=T["ink"])
        if item.get("meta"):
            d.text((MARGIN + 104, y + 74), item["meta"], font=fs, fill=T["sub"])
        y += rowh

    if s.get("note"):
        fn = font(36, bold=False)
        draw_wrapped(d, (MARGIN, H - 250), s["note"], fn, T["sub"], W - MARGIN * 2, spacing=10)
    footer_brand(d)
    return img


def slide_cta(s):
    """最終スライド。保存とプロフィール誘導。"""
    img, d = base(T["ink"])
    y = 180
    f = font(76)
    y = draw_wrapped(d, (MARGIN, y), s.get("title", "保存して、あとで確認を"), f,
                     "#FFFFFF", W - MARGIN * 2, spacing=18, center=True)
    y += 50
    fb = font(42, bold=False)
    body = s.get("body", "制度は申請しないともらえません。\n忘れないうちに保存しておいてください。")
    y = draw_wrapped(d, (MARGIN, y), body, fb, "#C9C4CE", W - MARGIN * 2, spacing=14, center=True)

    y += 70
    rounded(d, [MARGIN, y, W - MARGIN, y + 200], 30, "#33313C")
    f2 = font(40)
    d.text((MARGIN + 50, y + 40), "🔍 あなたの街の助成額は?", font=f2, fill=T["brand"])
    f3 = font(36, bold=False)
    draw_wrapped(d, (MARGIN + 50, y + 100), "プロフィールのリンクから、全国1,740市区町村を検索できます。",
                 f3, "#C9C4CE", W - MARGIN * 2 - 100, spacing=8)

    footer_brand(d, dark=True)
    return img


RENDER = {"cover": slide_cover, "point": slide_point, "list": slide_list, "cta": slide_cta}


def build_post(post, index=0):
    global T
    T = THEMES.get(post.get("theme_color") or THEME_ORDER[index % len(THEME_ORDER)], THEMES["peach"])
    d = os.path.join(OUT, post["id"])
    os.makedirs(d, exist_ok=True)
    n = 0
    pts = [s for s in post["slides"] if s["type"] == "point"]
    pi = 0
    for s in post["slides"]:
        fn = RENDER[s["type"]]
        if s["type"] == "point":
            pi += 1
            img = fn(s, idx=pi, total=len(pts))
        else:
            img = fn(s)
        n += 1
        img.save(os.path.join(d, f"{n:02d}.png"), quality=95)
    # キャプションも書き出す
    with open(os.path.join(d, "caption.txt"), "w", encoding="utf-8") as f:
        f.write(post.get("caption", "").strip() + "\n")
    return n, d


def main():
    posts = json.load(open(POSTS, encoding="utf-8"))["posts"]
    os.makedirs(OUT, exist_ok=True)
    for i, p in enumerate(posts):
        n, d = build_post(p, i)
        print(f"  {p['id']}: {n}枚 [{p.get('theme_color') or THEME_ORDER[i % len(THEME_ORDER)]}] → {d}")
    print(f"\n完了: {len(posts)}投稿")


if __name__ == "__main__":
    main()
