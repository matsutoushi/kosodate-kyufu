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

from PIL import Image, ImageDraw, ImageFilter, ImageFont

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


def paste_at(img, layer, x, cy, alpha=1.0, dx=0):
    """レイヤーを左端x・指定Y(中心)に貼る。リスト行など左揃えに使う。"""
    if alpha <= 0:
        return
    lay = layer
    if alpha < 1.0:
        lay = layer.copy()
        a = lay.getchannel("A").point(lambda v: int(v * alpha))
        lay.putalpha(a)
    img.paste(lay, (int(x + dx), int(cy - lay.height / 2)), lay)


def bar_layer(text, note, T, w=900, h=150):
    """リスト1行(角丸の帯 + 制度名 + 補足)。左から流し込む用。"""
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([0, 0, w, h], radius=28, fill=T["soft"])
    d.rounded_rectangle([0, 0, 16, h], radius=8, fill=T["brand"])
    # 枠からはみ出したら縮める。手で文字数を調整すると必ずどこかで溢れる
    def fit(txt, size, floor):
        while size > floor and d.textlength(txt, font=font(size)) > w - 68:
            size -= 2
        return font(size)
    d.text((48, 26), text, font=fit(text, 56, 34), fill=T["ink"])
    d.text((48, 92), note, font=fit(note, 36, 24), fill=T["sub"])
    return lay


def render_shinsei(T):
    """A案: 申請しないともらえないお金。損失回避で一番強い。約15秒。"""
    hook1 = text_layer("知らないと\nずっと 0 円", font(96), T["ink"])
    hook2 = text_layer("申請しないともらえないお金", font(56), T["sub"])
    em = emoji_layer("⚠️", 200)
    ITEMS = [
        ("児童手当", "出生届とは別に「認定請求」が必要"),
        ("妊婦のための支援給付", "妊娠5万＋胎児の数×5万円"),
        ("高額療養費", "限度額認定証か、あとから申請"),
        ("医療費控除", "年末調整では不可。確定申告で"),
        ("018サポート(東京都)", "児童手当と違い自動では入らない"),
    ]
    bars = [bar_layer(a, b, T) for a, b in ITEMS]
    key1 = text_layer("どれも共通点は", font(58), T["sub"])
    key2 = text_layer("申請主義", font(150), T["brand_d"])
    key3 = text_layer("役所からは教えてくれません", font(52), T["ink"])
    c = cta_save(T, "あとで申請するときのために", "保存 しておく")

    def frame(t):
        img = Image.new("RGB", (W, H), T["bg"])
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 14], fill=T["brand"])
        d.rectangle([0, H - 14, W, H], fill=T["brand"])

        if t < 2.8:  # フック
            p = ease_out(min(1, t / 0.35))
            paste_center(img, em, 640, dy=int((1 - p) * 40))
            paste_center(img, hook1, 960, dy=int((1 - p) * 50))
            if t > 1.1:
                paste_center(img, hook2, 1210, alpha=ease_out(min(1, (t - 1.1) / 0.5)))
        elif t < 9.6:  # リストが1つずつ積み上がる
            tt = t - 2.8
            paste_center(img, text_layer("たとえば、この5つ", font(60), T["sub"]), 400,
                         alpha=ease_out(min(1, tt / 0.4)))
            for i, bar in enumerate(bars):
                st = 0.5 + i * 1.15
                if tt < st:
                    break
                p = ease_out(min(1, (tt - st) / 0.4))
                paste_at(img, bar, 90, 560 + i * 210, alpha=p, dx=int((1 - p) * -70))
        elif t < 12.4:  # キーワード
            tt = t - 9.6
            paste_center(img, key1, 640, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.35:
                p = min(1, (tt - 0.35) / 0.35)
                scale = 1.5 - 0.5 * ease_out(p)
                z = key2.resize((int(key2.width * scale), int(key2.height * scale)))
                paste_center(img, z, 900, alpha=p)
            if tt > 1.1:
                paste_center(img, key3, 1180, alpha=ease_out(min(1, (tt - 1.1) / 0.5)))
        else:  # CTA
            draw_cta(img, c, t - 12.4)
        return img

    return frame, 15.0


def render_shussan(T):
    """B案: 出産でもらえるお金の合計。保存されやすい。約15秒。"""
    hook1 = text_layer("出産でもらえるお金\nぜんぶでいくら？", font(88), T["ink"])
    em = emoji_layer("👶", 220)
    r1 = bar_layer("妊婦のための支援給付", "妊娠時5万＋胎児の数×5万円", T)
    r2 = bar_layer("出産育児一時金", "子ども1人につき50万円", T)
    total_l = text_layer("だれでも、あわせて", font(58), T["sub"])
    plus1 = text_layer("会社員・公務員なら さらに", font(56), T["ink"])
    p1 = bar_layer("出産手当金", "標準報酬日額の2/3 × 最大98日", T)
    p2 = bar_layer("育児休業給付金", "休業前賃金の67% →その後50%", T)
    note = text_layer("※金額は2026年時点。条件は加入先で異なります", font(38), T["sub"])
    c = cta_save(T, "申請のときに見返せるように", "保存 しておく")
    cf = font(180)

    def frame(t):
        img = Image.new("RGB", (W, H), T["bg"])
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 14], fill=T["brand"])
        d.rectangle([0, H - 14, W, H], fill=T["brand"])

        if t < 2.6:
            p = ease_out(min(1, t / 0.35))
            paste_center(img, em, 660, dy=int((1 - p) * 40))
            paste_center(img, hook1, 1010, dy=int((1 - p) * 55))
        elif t < 8.4:  # 2つ積んで合計をカウントアップ
            tt = t - 2.6
            paste_at(img, r1, 90, 560, alpha=ease_out(min(1, tt / 0.4)),
                     dx=int((1 - ease_out(min(1, tt / 0.4))) * -70))
            if tt > 0.9:
                q = ease_out(min(1, (tt - 0.9) / 0.4))
                paste_at(img, r2, 90, 790, alpha=q, dx=int((1 - q) * -70))
            if tt > 1.9:
                paste_center(img, total_l, 1080, alpha=ease_out(min(1, (tt - 1.9) / 0.4)))
                cp = ease_out(min(1, max(0.0, (tt - 2.3) / 2.0)))
                txt = f"{int(600000 * cp):,} 円"
                tw = d.textlength(txt, font=cf)
                d.text(((W - tw) / 2, 1180), txt, font=cf, fill=T["brand_d"])
                if cp >= 1.0:
                    paste_center(img, text_layer("単胎の場合。双子ならさらに5万円", font(46), T["sub"]),
                                 1410, alpha=ease_out(min(1, (tt - 4.4) / 0.5)))
        elif t < 12.6:  # 会社員の上乗せ
            tt = t - 8.4
            paste_center(img, plus1, 520, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.5:
                q = ease_out(min(1, (tt - 0.5) / 0.4))
                paste_at(img, p1, 90, 780, alpha=q, dx=int((1 - q) * -70))
            if tt > 1.3:
                q = ease_out(min(1, (tt - 1.3) / 0.4))
                paste_at(img, p2, 90, 1010, alpha=q, dx=int((1 - q) * -70))
            if tt > 2.2:
                paste_center(img, note, 1260, alpha=ease_out(min(1, (tt - 2.2) / 0.5)))
        else:
            draw_cta(img, c, t - 12.6)
        return img

    return frame, 15.0


def render_jidoteate(T):
    """C案: 児童手当は18年でいくら。母数が最大。約14秒。"""
    hook1 = text_layer("児童手当って\n18年で いくら？", font(92), T["ink"])
    em = emoji_layer("🧮", 210)
    r1 = bar_layer("0〜2歳", "月 15,000円 × 36か月 = 54万円", T)
    r2 = bar_layer("3歳〜高校生", "月 10,000円 × 180か月 = 180万円", T)
    total_l = text_layer("ひとりあたり およそ", font(58), T["sub"])
    third1 = text_layer("第3子以降は", font(60), T["ink"])
    third2 = text_layer("年齢を問わず 月 3 万円", font(72), T["brand_d"])
    third3 = text_layer("所得制限もありません", font(52), T["sub"])
    warn = text_layer("ただし出生届とは別に\n「認定請求」の申請が必要です", font(58), T["ink"])
    c = cta_save(T, "申請を忘れないために", "保存 しておく")
    cf = font(175)

    def frame(t):
        img = Image.new("RGB", (W, H), T["bg"])
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 14], fill=T["brand"])
        d.rectangle([0, H - 14, W, H], fill=T["brand"])

        if t < 2.6:
            p = ease_out(min(1, t / 0.35))
            paste_center(img, em, 660, dy=int((1 - p) * 40))
            paste_center(img, hook1, 1010, dy=int((1 - p) * 55))
        elif t < 8.2:  # 内訳 → 総額カウントアップ
            tt = t - 2.6
            q = ease_out(min(1, tt / 0.4))
            paste_at(img, r1, 90, 560, alpha=q, dx=int((1 - q) * -70))
            if tt > 0.9:
                q2 = ease_out(min(1, (tt - 0.9) / 0.4))
                paste_at(img, r2, 90, 790, alpha=q2, dx=int((1 - q2) * -70))
            if tt > 1.9:
                paste_center(img, total_l, 1080, alpha=ease_out(min(1, (tt - 1.9) / 0.4)))
                cp = ease_out(min(1, max(0.0, (tt - 2.3) / 2.0)))
                txt = f"{int(2340000 * cp):,} 円"
                tw = d.textlength(txt, font=cf)
                d.text(((W - tw) / 2, 1180), txt, font=cf, fill=T["brand_d"])
                if cp >= 1.0:
                    paste_center(img, text_layer("※18歳の年度末まで受け取った場合の目安", font(44), T["sub"]),
                                 1410, alpha=ease_out(min(1, (tt - 4.4) / 0.5)))
        elif t < 11.4:  # 第3子
            tt = t - 8.2
            paste_center(img, third1, 700, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.4:
                p = min(1, (tt - 0.4) / 0.35)
                scale = 1.4 - 0.4 * ease_out(p)
                z = third2.resize((int(third2.width * scale), int(third2.height * scale)))
                paste_center(img, z, 950, alpha=p)
            if tt > 1.2:
                paste_center(img, third3, 1180, alpha=ease_out(min(1, (tt - 1.2) / 0.5)))
        elif t < 13.8:  # 落とし穴を独立したシーンにする
            tt = t - 11.4
            p = ease_out(min(1, tt / 0.5))
            paste_center(img, warn, 950, alpha=p, dy=int((1 - p) * 40))
        else:
            draw_cta(img, c, t - 13.8)
        return img

    return frame, 16.3


def encode(frame_fn, duration, outdir, caption=""):
    """1本ぶんを outdir/ にまとめて出す(video.mp4 / caption.txt)。
    平置きにすると本数が増えたときに探せなくなるので、必ず1本1フォルダにする。"""
    import imageio_ffmpeg
    os.makedirs(outdir, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="reel_")
    n = int(duration * FPS)
    for i in range(n):
        frame_fn(i / FPS).save(os.path.join(tmp, f"{i:04d}.png"))
    out = os.path.join(outdir, "video.mp4")
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ff, "-y", "-framerate", str(FPS), "-i", os.path.join(tmp, "%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart", out],
                   check=True, capture_output=True)
    shutil.rmtree(tmp, ignore_errors=True)
    if caption:
        with open(os.path.join(outdir, "caption.txt"), "w", encoding="utf-8") as f:
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


CAPTION_SHINSEI = """【申請しないと、ずっと0円のままのお金】

日本の給付金はほとんどが「申請主義」です。
対象でも、自分で手を挙げないと1円も入りません。

▶ 児童手当 … 出生届とは別に「認定請求」が必要
▶ 妊婦のための支援給付 … 妊娠時5万＋胎児の数×5万円
▶ 高額療養費 … 限度額適用認定証、または後から申請
▶ 医療費控除 … 年末調整では不可。確定申告で
▶ 018サポート(東京都) … 児童手当と違い自動では入りません

役所から「もらえますよ」と連絡は来ません。
知っている人だけが受け取っています。

わが家がどれに当てはまるかは、
プロフィールのリンクから30秒でチェックできます。

※制度の内容は変わることがあります。詳しくは各公式ページでご確認ください。

#給付金 #子育て #申請忘れ #新米ママ #プレママ #ワーママ #子育てママと繋がりたい #家計管理 #節約 #知って得する"""

CAPTION_SHUSSAN = """【出産でもらえるお金、ぜんぶでいくら？】

まず、働き方に関係なく受け取れるのがこの2つ。

▶ 妊婦のための支援給付 … 妊娠時5万円＋胎児の数×5万円
▶ 出産育児一時金 … 子ども1人につき50万円

単胎なら、あわせて60万円。双子ならさらに5万円増えます。

会社員・公務員なら、ここにさらに上乗せがあります。

▶ 出産手当金 … 標準報酬日額の2/3 × 最大98日
▶ 育児休業給付金 … 休業前賃金の67%(180日) → その後50%

育休は社会保険料も免除になるので、
手取りで見ると思ったより減りません。

自分がいくら受け取れるかは、
プロフィールのリンクから確認できます。

※2026年時点の金額です。条件は加入する健康保険で異なります。

#出産準備 #プレママ #妊娠中 #出産育児一時金 #育休 #給付金 #新米ママ #ワーママ #家計管理 #マタニティ"""

CAPTION_JIDOTEATE = """【児童手当、18年でいくらになると思いますか】

答えは およそ234万円 です。

▶ 0〜2歳 … 月15,000円 × 36か月 = 54万円
▶ 3歳〜高校生 … 月10,000円 × 180か月 = 180万円

2024年10月の拡充で高校生まで対象になり、所得制限もなくなりました。
第3子以降は年齢を問わず一律 月30,000円です。

ただし、ここが落とし穴。
出生届を出しただけでは振り込まれません。
市区町村への「認定請求」という別の申請が必要です。

引っ越したときも、転入先で15日以内に手続きが要ります。

受け取れる制度の一覧は、プロフィールのリンクから。

※18歳の年度末まで受け取った場合の目安です。詳しくはお住まいの市区町村へ。

#児童手当 #子育て #給付金 #新米ママ #プレママ #ワーママ #子育てママと繋がりたい #家計管理 #教育資金 #知って得する"""


def hbar_layer(label, value, maxv, T, w=900, h=118, unit="人"):
    """横棒グラフの1行。数字の大小を一目で見せたいときに使う。"""
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.text((0, 0), label, font=font(48), fill=T["ink"])
    bw = max(10, int((w - 260) * value / maxv))
    d.rounded_rectangle([0, 62, w - 260, 62 + 40], radius=20, fill=T["soft"])
    d.rounded_rectangle([0, 62, bw, 62 + 40], radius=20, fill=T["brand"])
    txt = f"{value:,}{unit}"
    d.text((w - 240, 54), txt, font=font(52), fill=T["brand_d"])
    return lay


def _fit_w(txt, size, floor, limit):
    """limit 幅に収まるフォントサイズを返す。溢れた文字が画面外に出るのを防ぐ。"""
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    while size > floor and probe.textlength(txt, font=font(size)) > limit:
        size -= 2
    return size


def cta_save(T, line1, line2):
    """終盤の共通CTA。実測でプロフィール遷移が0だったため、
    2段階の「プロフィール→リンク」ではなく1タップで済む『保存』を主役にする。"""
    return {
        "em": emoji_layer("🔖", 150),
        "l1": text_layer(line1, font(_fit_w(line1, 56, 34, W - 120)), T["sub"]),
        "l2": text_layer(line2, font(80), T["ink"]),
        "sub": text_layer("くわしくは プロフィールのリンクから", font(44), T["sub"]),
        "brand": text_layer("@こそだて給付ナビ", font(44), T["sub"]),
    }


def draw_cta(img, c, tt):
    p = ease_out(min(1, tt / 0.5))
    paste_center(img, c["em"], 620, alpha=p, dy=int((1 - p) * 40))
    paste_center(img, c["l1"], 830, alpha=p)
    paste_center(img, c["l2"], 960, alpha=ease_out(min(1, max(0.0, tt - 0.25) / 0.5)))
    paste_center(img, c["sub"], 1180, alpha=ease_out(min(1, max(0.0, tt - 0.6) / 0.5)))
    paste_center(img, c["brand"], 1450, alpha=p)


def render_ichisai(T):
    """D案: 保育園の「1歳の壁」。全国データが独自で、育休の判断に直結する=保存されやすい。"""
    em = emoji_layer("🍼", 200)
    hook = text_layer("保育園に入れないのは\n何歳だと思いますか", font(80), T["ink"])
    lead = text_layer("全国の待機児童 2,254人の内訳", font(56), T["sub"])
    BARS = [("0歳", 164), ("1歳", 1361), ("2歳", 516), ("3歳以上", 213)]
    bars = [hbar_layer(a, b, 1361, T) for a, b in BARS]
    k1 = text_layer("1歳児だけで", font(58), T["sub"])
    k2 = text_layer("全体の 6 割", font(140), T["brand_d"])
    k3 = text_layer("育休明けがいちばん狭き門です", font(52), T["ink"])
    n1 = text_layer("しかも", font(52), T["sub"])
    n2 = text_layer("88% の自治体は待機児童ゼロ", font(64), T["ink"])
    n3 = text_layer("「入りにくい」は地域と年齢で決まります", font(48), T["sub"])
    c = cta_save(T, "育休をいつまで取るかの判断に", "保存 しておく")

    def frame(t):
        img = Image.new("RGB", (W, H), T["bg"])
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 14], fill=T["brand"])
        d.rectangle([0, H - 14, W, H], fill=T["brand"])
        if t < 2.6:
            p = ease_out(min(1, t / 0.35))
            paste_center(img, em, 660, dy=int((1 - p) * 40))
            paste_center(img, hook, 1000, dy=int((1 - p) * 55))
        elif t < 8.0:
            tt = t - 2.6
            paste_center(img, lead, 420, alpha=ease_out(min(1, tt / 0.4)))
            for i, b in enumerate(bars):
                st = 0.4 + i * 0.75
                if tt < st:
                    break
                p = ease_out(min(1, (tt - st) / 0.4))
                paste_at(img, b, 90, 640 + i * 175, alpha=p, dx=int((1 - p) * -70))
            if tt > 3.6:  # 出典を添える(次のシーンの見出しと重ねない)
                paste_center(img, text_layer("こども家庭庁 令和7年4月1日時点", font(42), T["sub"]),
                             1400, alpha=ease_out(min(1, (tt - 3.6) / 0.4)))
        elif t < 11.0:
            tt = t - 8.0
            paste_center(img, k1, 640, alpha=ease_out(min(1, tt / 0.35)))
            if tt > 0.3:
                p = min(1, (tt - 0.3) / 0.35)
                scale = 1.4 - 0.4 * ease_out(p)
                z = k2.resize((int(k2.width * scale), int(k2.height * scale)))
                paste_center(img, z, 900, alpha=p)
            if tt > 1.0:
                paste_center(img, k3, 1150, alpha=ease_out(min(1, (tt - 1.0) / 0.5)))
        elif t < 13.6:
            tt = t - 11.0
            paste_center(img, n1, 660, alpha=ease_out(min(1, tt / 0.35)))
            paste_center(img, n2, 830, alpha=ease_out(min(1, max(0.0, tt - 0.25) / 0.4)))
            paste_center(img, n3, 1080, alpha=ease_out(min(1, max(0.0, tt - 0.7) / 0.5)))
        else:
            draw_cta(img, c, t - 13.6)
        return img

    return frame, 16.0


def render_tokyo23(T):
    """E案: 東京23区の出産でもらえるお金の差。地域比較は保存・シェアされやすい。"""
    em = emoji_layer("🏙️", 200)
    hook = text_layer("東京23区、出産で\nもらえる額が違います", font(80), T["ink"])
    lead = text_layer("区が独自に出しているお金", font(56), T["sub"])
    ITEMS = [
        ("港区", "出産費用助成 上限81万円"),
        ("千代田区", "出産費用助成 最大31万円"),
        ("文京区", "出産・子育て応援券 10万円分"),
        ("江戸川区", "乳児養育手当 月13,000円"),
    ]
    bars = [bar_layer(a, b, T) for a, b in ITEMS]
    w1 = text_layer("ただし、よくある誤解が", font(56), T["sub"])
    w2 = text_layer("「10万円のギフト」は\n区独自ではありません", font(72), T["ink"])
    w3 = text_layer("国の給付＋東京都の上乗せ。全区共通です", font(46), T["sub"])
    c = cta_save(T, "住んでいる区の分を確かめる前に", "保存 しておく")

    def frame(t):
        img = Image.new("RGB", (W, H), T["bg"])
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 14], fill=T["brand"])
        d.rectangle([0, H - 14, W, H], fill=T["brand"])
        if t < 2.6:
            p = ease_out(min(1, t / 0.35))
            paste_center(img, em, 660, dy=int((1 - p) * 40))
            paste_center(img, hook, 1000, dy=int((1 - p) * 55))
        elif t < 8.4:
            tt = t - 2.6
            paste_center(img, lead, 430, alpha=ease_out(min(1, tt / 0.4)))
            for i, b in enumerate(bars):
                st = 0.4 + i * 1.05
                if tt < st:
                    break
                p = ease_out(min(1, (tt - st) / 0.4))
                paste_at(img, b, 90, 660 + i * 210, alpha=p, dx=int((1 - p) * -70))
        elif t < 12.4:
            tt = t - 8.4
            paste_center(img, w1, 620, alpha=ease_out(min(1, tt / 0.4)))
            paste_center(img, w2, 880, alpha=ease_out(min(1, max(0.0, tt - 0.3) / 0.5)))
            paste_center(img, w3, 1180, alpha=ease_out(min(1, max(0.0, tt - 0.9) / 0.5)))
        else:
            draw_cta(img, c, t - 12.4)
        return img

    return frame, 15.0


def render_iryohi22(T):
    """F案: 子ども医療費が22歳まで無料の6自治体。意外性でシェアを狙う。"""
    em = emoji_layer("🏥", 200)
    hook = text_layer("子どもの医療費\n何歳まで無料？", font(88), T["ink"])
    a1 = text_layer("全国1,740市区町村のうち", font(54), T["sub"])
    a2 = text_layer("1,575 が 18歳年度末まで", font(72), T["ink"])
    a3 = text_layer("いまや9割が高校卒業まで無料です", font(48), T["sub"])
    b1 = text_layer("でも、さらに上がいます", font(58), T["sub"])
    b2 = text_layer("22歳の年度末まで", font(96), T["brand_d"])
    b3 = text_layer("全国で 6 自治体だけ", font(56), T["ink"])
    LIST = ["北海道 南富良野町", "千葉県 神崎町", "千葉県 多古町",
            "京都府 京丹後市", "愛媛県 上島町", "高知県 田野町"]
    names = text_layer("\n".join(LIST), font(56), T["ink"])
    c = cta_save(T, "自分の市区町村は何歳まで？", "保存 して確かめる")

    def frame(t):
        img = Image.new("RGB", (W, H), T["bg"])
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 14], fill=T["brand"])
        d.rectangle([0, H - 14, W, H], fill=T["brand"])
        if t < 2.6:
            p = ease_out(min(1, t / 0.35))
            paste_center(img, em, 660, dy=int((1 - p) * 40))
            paste_center(img, hook, 1000, dy=int((1 - p) * 55))
        elif t < 6.4:
            tt = t - 2.6
            paste_center(img, a1, 700, alpha=ease_out(min(1, tt / 0.4)))
            paste_center(img, a2, 900, alpha=ease_out(min(1, max(0.0, tt - 0.3) / 0.4)))
            paste_center(img, a3, 1120, alpha=ease_out(min(1, max(0.0, tt - 0.9) / 0.5)))
        elif t < 12.8:
            tt = t - 6.4
            paste_center(img, b1, 420, alpha=ease_out(min(1, tt / 0.35)))
            if tt > 0.3:
                p = min(1, (tt - 0.3) / 0.35)
                scale = 1.35 - 0.35 * ease_out(p)
                z = b2.resize((int(b2.width * scale), int(b2.height * scale)))
                paste_center(img, z, 600, alpha=p)
            if tt > 0.9:
                paste_center(img, b3, 760, alpha=ease_out(min(1, (tt - 0.9) / 0.4)))
            if tt > 1.4:
                paste_center(img, names, 1120, alpha=ease_out(min(1, (tt - 1.4) / 0.6)))
        else:
            draw_cta(img, c, t - 12.8)
        return img

    return frame, 15.5


def render_kokosagaku(T):
    """G案: 高校無償化の都道府県差。進路選択に直結するので保存されやすい。"""
    em = emoji_layer("🎓", 200)
    hook = text_layer("高校無償化\n住む県で差が出ます", font(84), T["ink"])
    lead = text_layer("国の支援に、県の上乗せが加わります", font(52), T["sub"])
    ROWS = [
        ("国の就学支援金", "公立 年11万8,800円／私立 上限45万7,200円"),
        ("大阪府", "2026年度から 年63万円超の授業料も対象"),
        ("東京都", "国と合わせて 年最大50万1,000円"),
        ("神奈川県", "2026年度から所得制限を撤廃する見通し"),
    ]
    bars = [bar_layer(a, b, T) for a, b in ROWS]
    w1 = text_layer("見落としやすいのが", font(56), T["sub"])
    w2 = text_layer("県の上乗せは\n「県内進学」が条件のことが多い", font(64), T["ink"])
    w3 = text_layer("越境通学だと国の分しか出ない場合があります", font(46), T["sub"])
    c = cta_save(T, "進学先を決める前に", "保存 しておく")

    def frame(t):
        img = Image.new("RGB", (W, H), T["bg"])
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 14], fill=T["brand"])
        d.rectangle([0, H - 14, W, H], fill=T["brand"])
        if t < 2.6:
            p = ease_out(min(1, t / 0.35))
            paste_center(img, em, 660, dy=int((1 - p) * 40))
            paste_center(img, hook, 1000, dy=int((1 - p) * 55))
        elif t < 9.0:
            tt = t - 2.6
            paste_center(img, lead, 430, alpha=ease_out(min(1, tt / 0.4)))
            for i, b in enumerate(bars):
                st = 0.4 + i * 1.2
                if tt < st:
                    break
                p = ease_out(min(1, (tt - st) / 0.4))
                paste_at(img, b, 90, 660 + i * 210, alpha=p, dx=int((1 - p) * -70))
        elif t < 12.6:
            tt = t - 9.0
            paste_center(img, w1, 600, alpha=ease_out(min(1, tt / 0.4)))
            paste_center(img, w2, 870, alpha=ease_out(min(1, max(0.0, tt - 0.3) / 0.5)))
            paste_center(img, w3, 1180, alpha=ease_out(min(1, max(0.0, tt - 0.9) / 0.5)))
        else:
            draw_cta(img, c, t - 12.6)
        return img

    return frame, 15.6


def render_kyushoku(T):
    """H案: 2026年4月からの給食費負担軽減。認知度が低く、手続き不要なのが効く。"""
    em = emoji_layer("🍚", 200)
    hook = text_layer("2026年4月から\n給食費が変わります", font(84), T["ink"])
    ROWS = [
        ("月 5,200円 を基準に支援", "全国平均の給食費に物価上昇を加味した額"),
        ("所得制限なし", "収入にかかわらず対象になります"),
        ("手続きは不要", "自治体を通じて支援されます"),
    ]
    bars = [bar_layer(a, b, T) for a, b in ROWS]
    n1 = text_layer("ただし対象は", font(56), T["sub"])
    n2 = text_layer("小学校 です", font(96), T["brand_d"])
    n3 = text_layer("中学校は国の制度の対象外。\n独自に無償化している自治体もあります", font(50), T["ink"])
    c = cta_save(T, "来年度の家計の見通しに", "保存 しておく")

    def frame(t):
        img = Image.new("RGB", (W, H), T["bg"])
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 14], fill=T["brand"])
        d.rectangle([0, H - 14, W, H], fill=T["brand"])
        if t < 2.6:
            p = ease_out(min(1, t / 0.35))
            paste_center(img, em, 660, dy=int((1 - p) * 40))
            paste_center(img, hook, 1000, dy=int((1 - p) * 55))
        elif t < 7.8:
            tt = t - 2.6
            for i, b in enumerate(bars):
                st = 0.3 + i * 1.2
                if tt < st:
                    break
                p = ease_out(min(1, (tt - st) / 0.4))
                paste_at(img, b, 90, 700 + i * 210, alpha=p, dx=int((1 - p) * -70))
        elif t < 11.4:
            tt = t - 7.8
            paste_center(img, n1, 600, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.3:
                p = min(1, (tt - 0.3) / 0.35)
                scale = 1.35 - 0.35 * ease_out(p)
                z = n2.resize((int(n2.width * scale), int(n2.height * scale)))
                paste_center(img, z, 800, alpha=p)
            if tt > 0.9:
                paste_center(img, n3, 1080, alpha=ease_out(min(1, (tt - 0.9) / 0.5)))
        else:
            draw_cta(img, c, t - 11.4)
        return img

    return frame, 14.4


def render_ikuji10(T):
    """I案: 育休の手取りが実質10割になる条件。育休層に刺さり保存されやすい。"""
    em = emoji_layer("👶", 200)
    hook = text_layer("育休の手取りが\n10割になる条件", font(84), T["ink"])
    b1 = bar_layer("育児休業給付金", "休業前賃金の67%(180日)→ その後50%", T)
    b2 = bar_layer("出生後休業支援給付金", "夫婦それぞれ14日以上で 最大28日 13%上乗せ", T)
    b3 = bar_layer("社会保険料の免除", "育休中は保険料がかからない", T)
    k1 = text_layer("これらが重なると", font(56), T["sub"])
    k2 = text_layer("実質 手取り10割", font(104), T["brand_d"])
    k3 = text_layer("相当になることがあります", font(52), T["ink"])
    n = text_layer("※2025年4月から。夫婦それぞれが取ることが条件です", font(44), T["sub"])
    c = cta_save(T, "夫婦で育休の取り方を決める前に", "保存 しておく")

    def frame(t):
        img = Image.new("RGB", (W, H), T["bg"])
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 14], fill=T["brand"])
        d.rectangle([0, H - 14, W, H], fill=T["brand"])
        if t < 2.6:
            p = ease_out(min(1, t / 0.35))
            paste_center(img, em, 660, dy=int((1 - p) * 40))
            paste_center(img, hook, 1000, dy=int((1 - p) * 55))
        elif t < 8.2:
            tt = t - 2.6
            for i, b in enumerate([b1, b2, b3]):
                st = 0.3 + i * 1.25
                if tt < st:
                    break
                p = ease_out(min(1, (tt - st) / 0.4))
                paste_at(img, b, 90, 700 + i * 210, alpha=p, dx=int((1 - p) * -70))
        elif t < 12.0:
            tt = t - 8.2
            paste_center(img, k1, 600, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.3:
                p = min(1, (tt - 0.3) / 0.35)
                scale = 1.35 - 0.35 * ease_out(p)
                z = k2.resize((int(k2.width * scale), int(k2.height * scale)))
                paste_center(img, z, 830, alpha=p)
            if tt > 0.9:
                paste_center(img, k3, 1030, alpha=ease_out(min(1, (tt - 0.9) / 0.4)))
            if tt > 1.5:
                paste_center(img, n, 1290, alpha=ease_out(min(1, (tt - 1.5) / 0.5)))
        else:
            draw_cta(img, c, t - 12.0)
        return img

    return frame, 15.0


def render_kigen(T):
    """J案: 申請期限の一覧。保存の王道テーマ。最後に「期限なし」を置いて落差をつける。"""
    em = emoji_layer("⏰", 200)
    hook = text_layer("1日過ぎると\n戻ってきません", font(92), T["ink"])
    lead = text_layer("見落としやすい期限", font(56), T["sub"])
    ROWS = [
        ("児童手当", "出生・転入の翌日から15日以内が原則"),
        ("出産育児一時金", "出産日の翌日から2年で時効"),
        ("高校の就学支援金", "学校が案内する期限内。自動では出ません"),
        ("多子世帯の大学無償化", "学校の指定期間内。自動減免ではありません"),
    ]
    bars = [bar_layer(a, b, T) for a, b in ROWS]
    g1 = text_layer("逆に、あきらめなくていいものも", font(54), T["sub"])
    g2 = text_layer("医療費控除は 5年さかのぼれる", font(66), T["ink"])
    g3 = text_layer("給食費の負担軽減にいたっては 申請そのものが不要", font(44), T["sub"])
    c = cta_save(T, "期限を忘れないために", "保存 しておく")

    def frame(t):
        img = Image.new("RGB", (W, H), T["bg"])
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 14], fill=T["brand"])
        d.rectangle([0, H - 14, W, H], fill=T["brand"])
        if t < 2.6:
            p = ease_out(min(1, t / 0.35))
            paste_center(img, em, 660, dy=int((1 - p) * 40))
            paste_center(img, hook, 1000, dy=int((1 - p) * 55))
        elif t < 9.2:
            tt = t - 2.6
            paste_center(img, lead, 430, alpha=ease_out(min(1, tt / 0.4)))
            for i, b in enumerate(bars):
                st = 0.4 + i * 1.25
                if tt < st:
                    break
                p = ease_out(min(1, (tt - st) / 0.4))
                paste_at(img, b, 90, 660 + i * 210, alpha=p, dx=int((1 - p) * -70))
        elif t < 12.8:
            tt = t - 9.2
            paste_center(img, g1, 640, alpha=ease_out(min(1, tt / 0.4)))
            paste_center(img, g2, 880, alpha=ease_out(min(1, max(0.0, tt - 0.3) / 0.5)))
            paste_center(img, g3, 1120, alpha=ease_out(min(1, max(0.0, tt - 0.9) / 0.5)))
        else:
            draw_cta(img, c, t - 12.8)
        return img

    return frame, 15.8


def render_kogaku(T):
    """K案: 高額療養費。帝王切開・切迫早産で実際に効く。
    これまでの「フック→箇条書き→CTA」だと中身が薄いので、
    前提 → 計算式 → モデルケース → 手続き → 落とし穴 の7シーン構成にした。約30秒。"""
    em = emoji_layer("🏥", 200)
    hook = text_layer("帝王切開になったら\n入院費はいくら？", font(84), T["ink"])

    s2a = text_layer("まず大前提", font(56), T["sub"])
    b_no = bar_layer("正常分娩", "保険がきかない＝高額療養費の対象外", T)
    b_yes = bar_layer("帝王切開・切迫早産・吸引分娩", "保険診療なので 高額療養費が使えます", T)
    s2b = text_layer("「出産は対象外」と思い込む人がとても多い", font(48), T["ink"])

    s3a = text_layer("1か月の自己負担には上限があります", font(56), T["sub"])
    s3b = text_layer("80,100円 ＋（医療費−267,000円）×1%", font(56), T["brand_d"])
    s3c = text_layer("年収およそ370〜770万円の場合", font(46), T["sub"])
    s3d = text_layer("超えた分は、あとから戻ってきます", font(52), T["ink"])

    s4a = text_layer("たとえば、切迫早産で1か月入院", font(56), T["sub"])
    st1 = bar_layer("医療費の総額", "100万円", T)
    st2 = bar_layer("窓口で払う3割", "30万円", T)
    st3 = bar_layer("この月の上限額", "約 87,430円", T)
    s4b = text_layer("戻ってくるのは", font(54), T["sub"])
    cf = font(150)

    s5a = text_layer("しかも、立て替えずに済みます", font(56), T["sub"])
    b_m1 = bar_layer("マイナ保険証を使う", "窓口の支払いが最初から上限まで", T)
    b_m2 = bar_layer("限度額適用認定証を用意する", "入院が決まったら健康保険へ申請", T)

    s6a = text_layer("見落としやすい3つ", font(58), T["sub"])
    b_w1 = bar_layer("計算は「月ごと」", "月をまたぐ入院は合算されません", T)
    b_w2 = bar_layer("時効は2年", "診療した月の翌月1日から2年", T)
    b_w3 = bar_layer("出産育児一時金とは別", "50万円とは別に受け取れます", T)

    c = cta_save(T, "入院が決まったときのために", "保存 しておく")

    def frame(t):
        img = Image.new("RGB", (W, H), T["bg"])
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 14], fill=T["brand"])
        d.rectangle([0, H - 14, W, H], fill=T["brand"])

        if t < 3.0:                                    # ① フック
            p = ease_out(min(1, t / 0.35))
            paste_center(img, em, 660, dy=int((1 - p) * 40))
            paste_center(img, hook, 1000, dy=int((1 - p) * 55))
        elif t < 9.0:                                  # ② 何が対象か
            tt = t - 3.0
            paste_center(img, s2a, 440, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.4:
                q = ease_out(min(1, (tt - 0.4) / 0.4))
                paste_at(img, b_no, 90, 700, alpha=q, dx=int((1 - q) * -70))
            if tt > 1.5:
                q = ease_out(min(1, (tt - 1.5) / 0.4))
                paste_at(img, b_yes, 90, 910, alpha=q, dx=int((1 - q) * -70))
            if tt > 2.8:
                paste_center(img, s2b, 1180, alpha=ease_out(min(1, (tt - 2.8) / 0.5)))
        elif t < 15.0:                                 # ③ 上限額の考え方
            tt = t - 9.0
            paste_center(img, s3a, 560, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.5:
                p = min(1, (tt - 0.5) / 0.35)
                sc = 1.25 - 0.25 * ease_out(p)
                z = s3b.resize((int(s3b.width * sc), int(s3b.height * sc)))
                paste_center(img, z, 800, alpha=p)
            if tt > 1.2:
                paste_center(img, s3c, 950, alpha=ease_out(min(1, (tt - 1.2) / 0.4)))
            if tt > 2.2:
                paste_center(img, s3d, 1180, alpha=ease_out(min(1, (tt - 2.2) / 0.5)))
        elif t < 24.0:                                 # ④ モデルケース
            tt = t - 15.0
            paste_center(img, s4a, 430, alpha=ease_out(min(1, tt / 0.4)))
            for i, b in enumerate([st1, st2, st3]):
                st = 0.4 + i * 1.1
                if tt < st:
                    break
                q = ease_out(min(1, (tt - st) / 0.4))
                paste_at(img, b, 90, 660 + i * 200, alpha=q, dx=int((1 - q) * -70))
            if tt > 4.0:
                paste_center(img, s4b, 1250, alpha=ease_out(min(1, (tt - 4.0) / 0.4)))
                cp = ease_out(min(1, max(0.0, (tt - 4.4) / 2.0)))
                txt = f"{int(212570 * cp):,} 円"
                tw = d.textlength(txt, font=cf)
                d.text(((W - tw) / 2, 1310), txt, font=cf, fill=T["brand_d"])
        elif t < 30.0:                                 # ⑤ 立て替えない方法
            tt = t - 24.0
            paste_center(img, s5a, 500, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.4:
                q = ease_out(min(1, (tt - 0.4) / 0.4))
                paste_at(img, b_m1, 90, 760, alpha=q, dx=int((1 - q) * -70))
            if tt > 1.6:
                q = ease_out(min(1, (tt - 1.6) / 0.4))
                paste_at(img, b_m2, 90, 970, alpha=q, dx=int((1 - q) * -70))
        elif t < 36.0:                                 # ⑥ 落とし穴
            tt = t - 30.0
            paste_center(img, s6a, 430, alpha=ease_out(min(1, tt / 0.4)))
            for i, b in enumerate([b_w1, b_w2, b_w3]):
                st = 0.4 + i * 1.15
                if tt < st:
                    break
                q = ease_out(min(1, (tt - st) / 0.4))
                paste_at(img, b, 90, 680 + i * 210, alpha=q, dx=int((1 - q) * -70))
        else:                                          # ⑦ CTA
            draw_cta(img, c, t - 36.0)
        return img

    return frame, 41.0


def render_iryohikojo(T):
    """L案: 医療費控除。出産した年は該当しやすい。確定申告シーズンに向けた仕込み。約30秒。"""
    em = emoji_layer("🧾", 200)
    hook = text_layer("出産した年は\n確定申告でお金が戻ります", font(78), T["ink"])

    s2 = text_layer("何が対象になるのか", font(56), T["sub"])
    b_ok1 = bar_layer("対象になるもの", "妊婦健診・分娩費・入院費", T)
    b_ok2 = bar_layer("意外と入れ忘れるもの", "通院の電車・バス代(記録があれば)", T)
    b_ng = bar_layer("対象にならないもの", "里帰りの帰省費用・自家用車のガソリン代", T)

    s3a = text_layer("いくらから使えるか", font(56), T["sub"])
    s3b = text_layer("年間 10 万円を超えた分", font(80), T["brand_d"])
    s3c = text_layer("総所得200万円未満なら 所得の5%", font(48), T["sub"])
    s3d = text_layer("生計が同じ家族の分は合算できます", font(52), T["ink"])

    s4 = text_layer("たとえば、こんな1年", font(56), T["sub"])
    m1 = bar_layer("出産費用 62万円", "出産育児一時金50万円を引いて 12万円", T)
    m2 = bar_layer("妊婦健診の自己負担", "3万円", T)
    m3 = bar_layer("家族の医療費", "5万円", T)
    s4b = text_layer("合計20万円 → 戻るのは", font(52), T["sub"])
    cf = font(140)

    s5 = text_layer("つまずきやすい2つ", font(58), T["sub"])
    w1 = bar_layer("年末調整ではできません", "会社員でも確定申告が必要です", T)
    w2 = bar_layer("一時金の引き方に注意", "その出産の費用からだけ引く。全体から引かない", T)

    s6 = text_layer("あきらめなくて大丈夫", font(58), T["sub"])
    g1 = bar_layer("5年さかのぼれます", "去年の分を忘れていても間に合います", T)
    g2 = bar_layer("共働きなら所得が高い方で", "税率が高いほど戻る額も大きくなります", T)

    c = cta_save(T, "確定申告の時期に見返せるように", "保存 しておく")

    def frame(t):
        img = Image.new("RGB", (W, H), T["bg"])
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 14], fill=T["brand"])
        d.rectangle([0, H - 14, W, H], fill=T["brand"])
        if t < 3.0:
            p = ease_out(min(1, t / 0.35))
            paste_center(img, em, 660, dy=int((1 - p) * 40))
            paste_center(img, hook, 1010, dy=int((1 - p) * 55))
        elif t < 9.6:
            tt = t - 3.0
            paste_center(img, s2, 430, alpha=ease_out(min(1, tt / 0.4)))
            for i, b in enumerate([b_ok1, b_ok2, b_ng]):
                st = 0.4 + i * 1.25
                if tt < st:
                    break
                q = ease_out(min(1, (tt - st) / 0.4))
                paste_at(img, b, 90, 680 + i * 210, alpha=q, dx=int((1 - q) * -70))
        elif t < 15.6:
            tt = t - 9.6
            paste_center(img, s3a, 560, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.4:
                pp = min(1, (tt - 0.4) / 0.35)
                sc = 1.3 - 0.3 * ease_out(pp)
                z = s3b.resize((int(s3b.width * sc), int(s3b.height * sc)))
                paste_center(img, z, 790, alpha=pp)
            if tt > 1.2:
                paste_center(img, s3c, 960, alpha=ease_out(min(1, (tt - 1.2) / 0.4)))
            if tt > 2.2:
                paste_center(img, s3d, 1190, alpha=ease_out(min(1, (tt - 2.2) / 0.5)))
        elif t < 24.6:
            tt = t - 15.6
            paste_center(img, s4, 430, alpha=ease_out(min(1, tt / 0.4)))
            for i, b in enumerate([m1, m2, m3]):
                st = 0.4 + i * 1.1
                if tt < st:
                    break
                q = ease_out(min(1, (tt - st) / 0.4))
                paste_at(img, b, 90, 660 + i * 200, alpha=q, dx=int((1 - q) * -70))
            if tt > 4.0:
                paste_center(img, s4b, 1250, alpha=ease_out(min(1, (tt - 4.0) / 0.4)))
                cp = ease_out(min(1, max(0.0, (tt - 4.4) / 2.0)))
                txt = f"約 {int(20000 * cp):,} 円"
                tw = d.textlength(txt, font=cf)
                d.text(((W - tw) / 2, 1320), txt, font=cf, fill=T["brand_d"])
        elif t < 30.6:
            tt = t - 24.6
            paste_center(img, s5, 480, alpha=ease_out(min(1, tt / 0.4)))
            for i, b in enumerate([w1, w2]):
                st = 0.4 + i * 1.3
                if tt < st:
                    break
                q = ease_out(min(1, (tt - st) / 0.4))
                paste_at(img, b, 90, 750 + i * 210, alpha=q, dx=int((1 - q) * -70))
        elif t < 36.6:
            tt = t - 30.6
            paste_center(img, s6, 480, alpha=ease_out(min(1, tt / 0.4)))
            for i, b in enumerate([g1, g2]):
                st = 0.4 + i * 1.3
                if tt < st:
                    break
                q = ease_out(min(1, (tt - st) / 0.4))
                paste_at(img, b, 90, 750 + i * 210, alpha=q, dx=int((1 - q) * -70))
        else:
            draw_cta(img, c, t - 36.6)
        return img

    return frame, 41.6


def render_kabe(T):
    """M案: 年収の壁。制度改正で壁が動いたことを整理する。7シーン・約30秒。"""
    em = emoji_layer("🧱", 200)
    hook = text_layer("103万の壁、まだ\n気にしていませんか", font(84), T["ink"])

    s2 = text_layer("2025年の改正で、なくなりました", font(56), T["sub"])
    b1 = bar_layer("基礎控除", "48万円 → 最大 95万円", T)
    b2 = bar_layer("給与所得控除の最低保障", "55万円 → 65万円", T)
    s2b = text_layer("足すと 160万円", font(88), T["brand_d"])
    s2c = text_layer("ここまで所得税はかかりません", font(50), T["ink"])

    s3 = text_layer("いまの壁は この4つ", font(58), T["sub"])
    w1 = bar_layer("106万円", "社会保険に加入。条件つき", T)
    w2 = bar_layer("123万円", "配偶者控除→配偶者特別控除に変わるだけ", T)
    w3 = bar_layer("160万円", "所得税がかかり、控除も減り始める", T)
    w4 = bar_layer("201万5,999円", "配偶者特別控除が終わる", T)

    s4 = text_layer("本当の崖は 社会保険です", font(62), T["ink"])
    m1 = bar_layer("年収105万円のとき", "手取り 105万円", T)
    m2 = bar_layer("年収106万円のとき", "手取り 90.1万円", T)
    s4b = text_layer("1万円増やしただけで", font(52), T["sub"])
    cf = font(140)
    s4c = text_layer("元に戻るのは 年収122万円あたり", font(50), T["ink"])

    s5a = text_layer("よくある誤解", font(56), T["sub"])
    s5b = text_layer("123万円では\n手取りは減りません", font(76), T["ink"])
    s5c = text_layer("控除の名前が変わるだけ。金額は満額のままです", font(46), T["sub"])

    s6 = text_layer("しかも106万の壁は消えていきます", font(54), T["sub"])
    y1 = bar_layer("2027年10月", "従業員36人以上の勤務先に拡大", T)
    y2 = bar_layer("2029年10月 → 2032年10月", "21人以上 → 11人以上", T)
    y3 = bar_layer("2035年10月", "10人以下も対象に。規模の条件が消える", T)

    c = cta_save(T, "働き方を決める前に", "保存 しておく")

    def frame(t):
        img = Image.new("RGB", (W, H), T["bg"])
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 14], fill=T["brand"])
        d.rectangle([0, H - 14, W, H], fill=T["brand"])
        if t < 3.0:
            p = ease_out(min(1, t / 0.35))
            paste_center(img, em, 660, dy=int((1 - p) * 40))
            paste_center(img, hook, 1010, dy=int((1 - p) * 55))
        elif t < 9.4:
            tt = t - 3.0
            paste_center(img, s2, 430, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.4:
                q = ease_out(min(1, (tt - 0.4) / 0.4))
                paste_at(img, b1, 90, 660, alpha=q, dx=int((1 - q) * -70))
            if tt > 1.4:
                q = ease_out(min(1, (tt - 1.4) / 0.4))
                paste_at(img, b2, 90, 860, alpha=q, dx=int((1 - q) * -70))
            if tt > 2.6:
                pp = min(1, (tt - 2.6) / 0.35)
                sc = 1.3 - 0.3 * ease_out(pp)
                z = s2b.resize((int(s2b.width * sc), int(s2b.height * sc)))
                paste_center(img, z, 1120, alpha=pp)
            if tt > 3.4:
                paste_center(img, s2c, 1310, alpha=ease_out(min(1, (tt - 3.4) / 0.5)))
        elif t < 16.0:
            tt = t - 9.4
            paste_center(img, s3, 400, alpha=ease_out(min(1, tt / 0.4)))
            for i, b in enumerate([w1, w2, w3, w4]):
                st = 0.4 + i * 1.25
                if tt < st:
                    break
                q = ease_out(min(1, (tt - st) / 0.4))
                paste_at(img, b, 90, 640 + i * 205, alpha=q, dx=int((1 - q) * -70))
        elif t < 24.5:
            tt = t - 16.0
            paste_center(img, s4, 420, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.5:
                q = ease_out(min(1, (tt - 0.5) / 0.4))
                paste_at(img, m1, 90, 680, alpha=q, dx=int((1 - q) * -70))
            if tt > 1.5:
                q = ease_out(min(1, (tt - 1.5) / 0.4))
                paste_at(img, m2, 90, 880, alpha=q, dx=int((1 - q) * -70))
            if tt > 2.8:
                paste_center(img, s4b, 1080, alpha=ease_out(min(1, (tt - 2.8) / 0.4)))
                cp = ease_out(min(1, max(0.0, (tt - 3.2) / 1.6)))
                txt = "-" + f"{int(149000 * cp):,}" + " 円"
                tw = d.textlength(txt, font=cf)
                d.text(((W - tw) / 2, 1150), txt, font=cf, fill=T["brand_d"])
                if cp >= 1.0:
                    paste_center(img, s4c, 1390, alpha=ease_out(min(1, (tt - 5.2) / 0.5)))
        elif t < 30.5:
            tt = t - 24.5
            paste_center(img, s5a, 600, alpha=ease_out(min(1, tt / 0.4)))
            paste_center(img, s5b, 860, alpha=ease_out(min(1, max(0.0, tt - 0.3) / 0.5)))
            paste_center(img, s5c, 1150, alpha=ease_out(min(1, max(0.0, tt - 0.9) / 0.5)))
        elif t < 36.5:
            tt = t - 30.5
            paste_center(img, s6, 420, alpha=ease_out(min(1, tt / 0.4)))
            for i, b in enumerate([y1, y2, y3]):
                st = 0.4 + i * 1.2
                if tt < st:
                    break
                q = ease_out(min(1, (tt - st) / 0.4))
                paste_at(img, b, 90, 680 + i * 210, alpha=q, dx=int((1 - q) * -70))
        else:
            draw_cta(img, c, t - 36.5)
        return img

    return frame, 41.5


def render_ikukyu(T):
    """N案: 育休をいつ取ると得か。社会保険料免除の条件は日本年金機構の資料どおり。約30秒。"""
    em = emoji_layer("🗓️", 200)
    hook = text_layer("育休は「いつ取るか」で\n手取りが変わります", font(78), T["ink"])

    s2 = text_layer("休んでいる間は 社会保険料が免除されます", font(52), T["sub"])
    r1 = bar_layer("ルート①", "育休の期間に その月の末日が入っている", T)
    r2 = bar_layer("ルート②", "開始した月に 14日以上 取っている", T)
    s2b = text_layer("どちらかを満たせば その月はまるごと免除", font(50), T["ink"])

    s3a = text_layer("ここが一番効きます", font(56), T["sub"])
    s3b = text_layer("14日には\n土日も祝日も含まれる", font(76), T["brand_d"])
    s3c = text_layer("日本年金機構の資料に明記されています", font(46), T["sub"])
    s3d = text_layer("※就業した日は除きます", font(44), T["sub"])

    s4 = text_layer("たとえば 年末年始をはさむと", font(56), T["sub"])
    m1 = bar_layer("年末年始の休み", "6日（もともと給与は発生しない）", T)
    m2 = bar_layer("その前後に足す", "8日（ここが実際の欠勤）", T)
    m3 = bar_layer("合計", "14日 → 条件クリア", T)
    s4b = text_layer("免除される社会保険料は", font(52), T["sub"])
    cf = font(140)
    s4c = text_layer("※月給30万円の場合の目安（本人負担分）", font(42), T["sub"])

    s5a = text_layer("ただし 賞与は別条件です", font(58), T["ink"])
    w1 = bar_layer("賞与の保険料", "賞与月の末日を含む 連続1か月超 が必要", T)
    w2 = bar_layer("2022年10月から厳格化", "月末に1日だけ、という方法はもう使えません", T)

    s6a = text_layer("さらに 夫婦それぞれ14日以上で", font(54), T["sub"])
    s6b = text_layer("給付が 13% 上乗せ", font(80), T["brand_d"])
    s6c = text_layer("出生後休業支援給付金（2025年4月〜）", font(46), T["sub"])

    c = cta_save(T, "育休の時期を決める前に", "保存 しておく")

    def frame(t):
        img = Image.new("RGB", (W, H), T["bg"])
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 14], fill=T["brand"])
        d.rectangle([0, H - 14, W, H], fill=T["brand"])
        if t < 3.0:
            p = ease_out(min(1, t / 0.35))
            paste_center(img, em, 660, dy=int((1 - p) * 40))
            paste_center(img, hook, 1010, dy=int((1 - p) * 55))
        elif t < 9.4:
            tt = t - 3.0
            paste_center(img, s2, 430, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.5:
                q = ease_out(min(1, (tt - 0.5) / 0.4))
                paste_at(img, r1, 90, 690, alpha=q, dx=int((1 - q) * -70))
            if tt > 1.6:
                q = ease_out(min(1, (tt - 1.6) / 0.4))
                paste_at(img, r2, 90, 900, alpha=q, dx=int((1 - q) * -70))
            if tt > 2.8:
                paste_center(img, s2b, 1160, alpha=ease_out(min(1, (tt - 2.8) / 0.5)))
        elif t < 15.6:
            tt = t - 9.4
            paste_center(img, s3a, 560, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.4:
                pp = min(1, (tt - 0.4) / 0.35)
                sc = 1.25 - 0.25 * ease_out(pp)
                z = s3b.resize((int(s3b.width * sc), int(s3b.height * sc)))
                paste_center(img, z, 830, alpha=pp)
            if tt > 1.3:
                paste_center(img, s3c, 1080, alpha=ease_out(min(1, (tt - 1.3) / 0.4)))
            if tt > 2.1:
                paste_center(img, s3d, 1230, alpha=ease_out(min(1, (tt - 2.1) / 0.5)))
        elif t < 24.4:
            tt = t - 15.6
            paste_center(img, s4, 430, alpha=ease_out(min(1, tt / 0.4)))
            for i, b in enumerate([m1, m2, m3]):
                st = 0.4 + i * 1.1
                if tt < st:
                    break
                q = ease_out(min(1, (tt - st) / 0.4))
                paste_at(img, b, 90, 660 + i * 200, alpha=q, dx=int((1 - q) * -70))
            if tt > 4.0:
                paste_center(img, s4b, 1230, alpha=ease_out(min(1, (tt - 4.0) / 0.4)))
                cp = ease_out(min(1, max(0.0, (tt - 4.4) / 1.8)))
                txt = f"約 {int(42000 * cp):,} 円"
                tw = d.textlength(txt, font=cf)
                d.text(((W - tw) / 2, 1290), txt, font=cf, fill=T["brand_d"])
                if cp >= 1.0:
                    paste_center(img, s4c, 1450, alpha=ease_out(min(1, (tt - 6.4) / 0.5)))
        elif t < 30.4:
            tt = t - 24.4
            paste_center(img, s5a, 520, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.5:
                q = ease_out(min(1, (tt - 0.5) / 0.4))
                paste_at(img, w1, 90, 790, alpha=q, dx=int((1 - q) * -70))
            if tt > 1.7:
                q = ease_out(min(1, (tt - 1.7) / 0.4))
                paste_at(img, w2, 90, 1000, alpha=q, dx=int((1 - q) * -70))
        elif t < 36.4:
            tt = t - 30.4
            paste_center(img, s6a, 640, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.4:
                pp = min(1, (tt - 0.4) / 0.35)
                sc = 1.3 - 0.3 * ease_out(pp)
                z = s6b.resize((int(s6b.width * sc), int(s6b.height * sc)))
                paste_center(img, z, 880, alpha=pp)
            if tt > 1.2:
                paste_center(img, s6c, 1120, alpha=ease_out(min(1, (tt - 1.2) / 0.5)))
        else:
            draw_cta(img, c, t - 36.4)
        return img

    return frame, 41.4


def render_furusato(T):
    """O案(作り直し): 出産した年にふるさと納税の控除が消える話。
    旧版はしくみ・上限額・育休・医療費控除・期限を並べただけで筋がなかった。
    いちばん驚きがあり損失も大きい「ワンストップが無効になる」1本に絞る。約30秒。"""
    em = emoji_layer("🎁", 200)
    hook = text_layer("出産した年の\nふるさと納税は要注意", font(82), T["ink"])
    hook2 = text_layer("控除が丸ごと消えることがあります", font(52), T["sub"])

    s2a = text_layer("原因はワンストップ特例です", font(56), T["sub"])
    s2b = text_layer("これは\n「確定申告をしない人」の制度", font(66), T["ink"])
    s2c = text_layer("だから 確定申告をすると 全部無効になります", font(50), T["brand_d"])

    s3 = text_layer("出産した年に起きること", font(56), T["sub"])
    b1 = bar_layer("医療費が10万円を超える", "出産した年は超えやすい", T)
    b2 = bar_layer("医療費控除を申告する", "これは確定申告が必要", T)
    b3 = bar_layer("提出済みのワンストップが", "すべて無効になる", T)

    s4a = text_layer("たとえば 5万円寄付した場合", font(56), T["sub"])
    s4b = text_layer("本来の自己負担は 2,000円", font(58), T["ink"])
    s4c = text_layer("でも 無効になると", font(52), T["sub"])
    cf = font(150)
    s4d = text_layer("がそのまま自己負担に", font(50), T["ink"])

    s5a = text_layer("でも 防ぐのは簡単です", font(58), T["ink"])
    s5b = text_layer("確定申告のとき\n寄付金控除も一緒に申告する", font(64), T["brand_d"])
    s5c = text_layer("それだけです。寄付金受領証明書は捨てないで", font(46), T["sub"])

    s6a = text_layer("同じことが起きる年", font(56), T["sub"])
    w1 = bar_layer("住宅ローン控除の1年目", "この年も確定申告が必要です", T)
    w2 = bar_layer("寄付先が6自治体以上", "ワンストップは5自治体まで", T)

    c = cta_save(T, "寄付する前に", "保存 しておく")

    def frame(t):
        img = Image.new("RGB", (W, H), T["bg"])
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 14], fill=T["brand"])
        d.rectangle([0, H - 14, W, H], fill=T["brand"])
        if t < 3.2:
            p = ease_out(min(1, t / 0.35))
            paste_center(img, em, 660, dy=int((1 - p) * 40))
            paste_center(img, hook, 1000, dy=int((1 - p) * 55))
            if t > 1.4:
                paste_center(img, hook2, 1250, alpha=ease_out(min(1, (t - 1.4) / 0.5)))
        elif t < 9.4:
            tt = t - 3.2
            paste_center(img, s2a, 560, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.4:
                pp = min(1, (tt - 0.4) / 0.35)
                sc = 1.22 - 0.22 * ease_out(pp)
                z = s2b.resize((int(s2b.width * sc), int(s2b.height * sc)))
                paste_center(img, z, 830, alpha=pp)
            if tt > 1.6:
                paste_center(img, s2c, 1120, alpha=ease_out(min(1, (tt - 1.6) / 0.5)))
        elif t < 17.0:
            tt = t - 9.4
            paste_center(img, s3, 430, alpha=ease_out(min(1, tt / 0.4)))
            for i, b in enumerate([b1, b2, b3]):
                st = 0.4 + i * 1.25
                if tt < st:
                    break
                q = ease_out(min(1, (tt - st) / 0.4))
                paste_at(img, b, 90, 700 + i * 210, alpha=q, dx=int((1 - q) * -70))
        elif t < 25.0:
            tt = t - 17.0
            paste_center(img, s4a, 460, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.5:
                paste_center(img, s4b, 690, alpha=ease_out(min(1, (tt - 0.5) / 0.4)))
            if tt > 1.4:
                paste_center(img, s4c, 900, alpha=ease_out(min(1, (tt - 1.4) / 0.4)))
                cp = ease_out(min(1, max(0.0, (tt - 1.8) / 1.8)))
                txt = f"{int(48000 * cp):,} 円"
                tw = d.textlength(txt, font=cf)
                d.text(((W - tw) / 2, 980), txt, font=cf, fill=T["brand_d"])
                if cp >= 1.0:
                    paste_center(img, s4d, 1240, alpha=ease_out(min(1, (tt - 3.8) / 0.5)))
        elif t < 31.4:
            tt = t - 25.0
            paste_center(img, s5a, 580, alpha=ease_out(min(1, tt / 0.4)))
            paste_center(img, s5b, 860, alpha=ease_out(min(1, max(0.0, tt - 0.4) / 0.5)))
            if tt > 1.2:
                paste_center(img, s5c, 1160, alpha=ease_out(min(1, (tt - 1.2) / 0.5)))
        elif t < 37.6:
            tt = t - 31.4
            paste_center(img, s6a, 500, alpha=ease_out(min(1, tt / 0.4)))
            for i, b in enumerate([w1, w2]):
                st = 0.4 + i * 1.3
                if tt < st:
                    break
                q = ease_out(min(1, (tt - st) / 0.4))
                paste_at(img, b, 90, 780 + i * 210, alpha=q, dx=int((1 - q) * -70))
        else:
            draw_cta(img, c, t - 37.6)
        return img

    return frame, 42.6


def render_shotokuseigen(T):
    """P案: 子ども医療費の所得制限。全1,740市区町村のデータからしか作れない。約30秒。"""
    em = emoji_layer("🏥", 200)
    hook = text_layer("「うちは所得が高いから\n対象外」と思っていませんか", font(68), T["ink"])

    s2a = text_layer("全国1,740市区町村を調べました", font(54), T["sub"])
    s2b = text_layer("子どもの医療費助成で\n所得制限がある自治体は", font(62), T["ink"])
    cf = font(150)
    s2c = text_layer("市区町村だけ", font(56), T["ink"])

    s3a = text_layer("割合にすると", font(56), T["sub"])
    s3b = text_layer("2.8 %", font(150), T["brand_d"])
    s3c = text_layer("97%以上に 所得制限はありません", font(52), T["ink"])

    s4 = text_layer("内訳はこうなっています", font(56), T["sub"])
    b1 = bar_layer("所得制限も自己負担もなし", "1,301市区町村（全体の75%）", T)
    b2 = bar_layer("一部負担あり", "421市区町村（1回数百円など）", T)
    b3 = bar_layer("所得制限あり", "49市区町村（全体の2.8%）", T)

    s5a = text_layer("対象年齢も広がっています", font(56), T["sub"])
    s5b = text_layer("1,575市区町村が\n18歳の年度末まで", font(68), T["brand_d"])
    s5c = text_layer("全体の91%。9割が高校卒業まで無料です", font(48), T["sub"])

    s6a = text_layer("諦める前に確認してください", font(58), T["ink"])
    s6b = text_layer("所得で外れるのは 50に1つの自治体だけ", font(50), T["sub"])
    s6c = text_layer("※こども家庭庁 令和7年4月1日時点", font(42), T["sub"])

    c = cta_save(T, "自分の市区町村を調べる前に", "保存 しておく")

    def frame(t):
        img = Image.new("RGB", (W, H), T["bg"])
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 14], fill=T["brand"])
        d.rectangle([0, H - 14, W, H], fill=T["brand"])
        if t < 3.0:
            p = ease_out(min(1, t / 0.35))
            paste_center(img, em, 660, dy=int((1 - p) * 40))
            paste_center(img, hook, 1020, dy=int((1 - p) * 55))
        elif t < 9.6:
            tt = t - 3.0
            paste_center(img, s2a, 500, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.5:
                paste_center(img, s2b, 760, alpha=ease_out(min(1, (tt - 0.5) / 0.4)))
            if tt > 1.4:
                cp = ease_out(min(1, (tt - 1.4) / 1.6))
                txt = f"{int(49 * cp)}"
                tw = d.textlength(txt, font=cf)
                d.text(((W - tw) / 2, 990), txt, font=cf, fill=T["brand_d"])
                if cp >= 1.0:
                    paste_center(img, s2c, 1230, alpha=ease_out(min(1, (tt - 3.2) / 0.5)))
        elif t < 15.4:
            tt = t - 9.6
            paste_center(img, s3a, 620, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.4:
                pp = min(1, (tt - 0.4) / 0.35)
                sc = 1.4 - 0.4 * ease_out(pp)
                z = s3b.resize((int(s3b.width * sc), int(s3b.height * sc)))
                paste_center(img, z, 850, alpha=pp)
            if tt > 1.2:
                paste_center(img, s3c, 1120, alpha=ease_out(min(1, (tt - 1.2) / 0.5)))
        elif t < 23.0:
            tt = t - 15.4
            paste_center(img, s4, 430, alpha=ease_out(min(1, tt / 0.4)))
            for i, b in enumerate([b1, b2, b3]):
                st = 0.4 + i * 1.2
                if tt < st:
                    break
                q = ease_out(min(1, (tt - st) / 0.4))
                paste_at(img, b, 90, 700 + i * 210, alpha=q, dx=int((1 - q) * -70))
        elif t < 29.6:
            tt = t - 23.0
            paste_center(img, s5a, 580, alpha=ease_out(min(1, tt / 0.4)))
            paste_center(img, s5b, 860, alpha=ease_out(min(1, max(0.0, tt - 0.4) / 0.5)))
            if tt > 1.3:
                paste_center(img, s5c, 1140, alpha=ease_out(min(1, (tt - 1.3) / 0.5)))
        elif t < 36.0:
            tt = t - 29.6
            paste_center(img, s6a, 640, alpha=ease_out(min(1, tt / 0.4)))
            paste_center(img, s6b, 880, alpha=ease_out(min(1, max(0.0, tt - 0.4) / 0.5)))
            if tt > 1.3:
                paste_center(img, s6c, 1120, alpha=ease_out(min(1, (tt - 1.3) / 0.5)))
        else:
            draw_cta(img, c, t - 36.0)
        return img

    return frame, 41.0


def render_fuyokojo(T):
    """Q案: 16歳未満に扶養控除はない。誤解が多く、年末調整とふるさと納税の両方に効く。約30秒。"""
    em = emoji_layer("📋", 200)
    hook = text_layer("子どもが何人いても\n扶養控除は増えません", font(76), T["ink"])

    s2a = text_layer("扶養控除の対象になるのは", font(56), T["sub"])
    s2b = text_layer("16歳以上の子どもだけ", font(80), T["brand_d"])
    s2c = text_layer("児童手当の拡充と引き換えに 対象から外れました", font(48), T["sub"])

    s3 = text_layer("だから こうなります", font(58), T["sub"])
    b1 = bar_layer("未就学児・小学生が何人いても", "所得税の控除は増えません", T)
    b2 = bar_layer("ふるさと納税の上限額も", "16歳未満の子では下がりません", T)
    b3 = bar_layer("16〜18歳の子がいると", "扶養控除が効くので 上限額は下がります", T)

    s4a = text_layer("よくある損のしかた", font(56), T["sub"])
    s4b = text_layer("「子どもが3人いるから\n上限が低いはず」", font(68), T["ink"])
    s4c = text_layer("と思い込んで、少なめに寄付してしまう", font(48), T["sub"])

    s5a = text_layer("でも 書かないと損をする欄があります", font(52), T["ink"])
    w1 = bar_layer("扶養控除等申告書の", "「住民税に関する事項」の欄", T)
    w2 = bar_layer("16歳未満の子はここに書く", "住民税の非課税判定に使われます", T)

    s6a = text_layer("まとめると", font(56), T["sub"])
    s6b = text_layer("所得税では効かない\n住民税では効く", font(72), T["brand_d"])
    s6c = text_layer("「対象外だから空欄」が いちばん多い間違いです", font(46), T["ink"])

    c = cta_save(T, "年末調整の書類を書く前に", "保存 しておく")

    def frame(t):
        img = Image.new("RGB", (W, H), T["bg"])
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 14], fill=T["brand"])
        d.rectangle([0, H - 14, W, H], fill=T["brand"])
        if t < 3.0:
            p = ease_out(min(1, t / 0.35))
            paste_center(img, em, 660, dy=int((1 - p) * 40))
            paste_center(img, hook, 1010, dy=int((1 - p) * 55))
        elif t < 9.0:
            tt = t - 3.0
            paste_center(img, s2a, 620, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.4:
                pp = min(1, (tt - 0.4) / 0.35)
                sc = 1.28 - 0.28 * ease_out(pp)
                z = s2b.resize((int(s2b.width * sc), int(s2b.height * sc)))
                paste_center(img, z, 860, alpha=pp)
            if tt > 1.3:
                paste_center(img, s2c, 1120, alpha=ease_out(min(1, (tt - 1.3) / 0.5)))
        elif t < 16.6:
            tt = t - 9.0
            paste_center(img, s3, 430, alpha=ease_out(min(1, tt / 0.4)))
            for i, b in enumerate([b1, b2, b3]):
                st = 0.4 + i * 1.2
                if tt < st:
                    break
                q = ease_out(min(1, (tt - st) / 0.4))
                paste_at(img, b, 90, 700 + i * 210, alpha=q, dx=int((1 - q) * -70))
        elif t < 23.0:
            tt = t - 16.6
            paste_center(img, s4a, 580, alpha=ease_out(min(1, tt / 0.4)))
            paste_center(img, s4b, 860, alpha=ease_out(min(1, max(0.0, tt - 0.4) / 0.5)))
            if tt > 1.3:
                paste_center(img, s4c, 1140, alpha=ease_out(min(1, (tt - 1.3) / 0.5)))
        elif t < 30.0:
            tt = t - 23.0
            paste_center(img, s5a, 480, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.5:
                q = ease_out(min(1, (tt - 0.5) / 0.4))
                paste_at(img, w1, 90, 760, alpha=q, dx=int((1 - q) * -70))
            if tt > 1.7:
                q = ease_out(min(1, (tt - 1.7) / 0.4))
                paste_at(img, w2, 90, 970, alpha=q, dx=int((1 - q) * -70))
        elif t < 36.4:
            tt = t - 30.0
            paste_center(img, s6a, 600, alpha=ease_out(min(1, tt / 0.4)))
            paste_center(img, s6b, 860, alpha=ease_out(min(1, max(0.0, tt - 0.4) / 0.5)))
            if tt > 1.3:
                paste_center(img, s6c, 1150, alpha=ease_out(min(1, (tt - 1.3) / 0.5)))
        else:
            draw_cta(img, c, t - 36.4)
        return img

    return frame, 41.4


def render_hitorioya(T):
    """R案: ひとり親の給付と控除。層は狭いが刺さりが深い。約30秒。"""
    em = emoji_layer("🌱", 200)
    hook = text_layer("ひとり親が受け取れる\nお金を整理しました", font(76), T["ink"])

    s2 = text_layer("まず 児童扶養手当", font(58), T["sub"])
    b1 = bar_layer("1人目（全部支給）", "月額 約48,050円", T)
    b2 = bar_layer("2人目以降の加算（全部支給）", "月額 約11,350円", T)
    s2b = text_layer("子ども2人なら 月およそ", font(52), T["sub"])
    cf = font(140)

    s3a = text_layer("よくある取りこぼし", font(56), T["sub"])
    s3b = text_layer("「所得制限で無理」と\n決めつけて申請しない", font(68), T["ink"])
    s3c = text_layer("全部支給でなくても 一部支給に該当することがあります", font(46), T["sub"])

    s4 = text_layer("あわせて申請できるもの", font(56), T["sub"])
    m1 = bar_layer("ひとり親家庭等医療費助成", "通称マル親。医療費の自己負担分を助成", T)
    m2 = bar_layer("就学援助（小・中学生）", "学用品費・給食費・修学旅行費など", T)

    s5a = text_layer("税金でも35万円ひけます", font(58), T["ink"])
    t1 = bar_layer("ひとり親控除 35万円", "婚姻歴を問いません。未婚でも対象です", T)
    t2 = bar_layer("本人の合計所得500万円以下", "年末調整でも申告できます", T)

    s6a = text_layer("忘れてはいけないこと", font(56), T["sub"])
    s6b = text_layer("毎年の現況届", font(84), T["brand_d"])
    s6c = text_layer("出し忘れると 支給が止まります", font(52), T["ink"])

    c = cta_save(T, "申請の前に確かめられるように", "保存 しておく")

    def frame(t):
        img = Image.new("RGB", (W, H), T["bg"])
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 14], fill=T["brand"])
        d.rectangle([0, H - 14, W, H], fill=T["brand"])
        if t < 3.0:
            p = ease_out(min(1, t / 0.35))
            paste_center(img, em, 660, dy=int((1 - p) * 40))
            paste_center(img, hook, 1010, dy=int((1 - p) * 55))
        elif t < 10.4:
            tt = t - 3.0
            paste_center(img, s2, 430, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.4:
                q = ease_out(min(1, (tt - 0.4) / 0.4))
                paste_at(img, b1, 90, 680, alpha=q, dx=int((1 - q) * -70))
            if tt > 1.5:
                q = ease_out(min(1, (tt - 1.5) / 0.4))
                paste_at(img, b2, 90, 890, alpha=q, dx=int((1 - q) * -70))
            if tt > 2.7:
                paste_center(img, s2b, 1110, alpha=ease_out(min(1, (tt - 2.7) / 0.4)))
                cp = ease_out(min(1, max(0.0, (tt - 3.1) / 1.8)))
                txt = f"{int(59400 * cp):,} 円"
                tw = d.textlength(txt, font=cf)
                d.text(((W - tw) / 2, 1180), txt, font=cf, fill=T["brand_d"])
        elif t < 17.0:
            tt = t - 10.4
            paste_center(img, s3a, 580, alpha=ease_out(min(1, tt / 0.4)))
            paste_center(img, s3b, 860, alpha=ease_out(min(1, max(0.0, tt - 0.4) / 0.5)))
            if tt > 1.3:
                paste_center(img, s3c, 1150, alpha=ease_out(min(1, (tt - 1.3) / 0.5)))
        elif t < 23.6:
            tt = t - 17.0
            paste_center(img, s4, 500, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.5:
                q = ease_out(min(1, (tt - 0.5) / 0.4))
                paste_at(img, m1, 90, 760, alpha=q, dx=int((1 - q) * -70))
            if tt > 1.7:
                q = ease_out(min(1, (tt - 1.7) / 0.4))
                paste_at(img, m2, 90, 970, alpha=q, dx=int((1 - q) * -70))
        elif t < 30.2:
            tt = t - 23.6
            paste_center(img, s5a, 500, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.5:
                q = ease_out(min(1, (tt - 0.5) / 0.4))
                paste_at(img, t1, 90, 760, alpha=q, dx=int((1 - q) * -70))
            if tt > 1.7:
                q = ease_out(min(1, (tt - 1.7) / 0.4))
                paste_at(img, t2, 90, 970, alpha=q, dx=int((1 - q) * -70))
        elif t < 36.4:
            tt = t - 30.2
            paste_center(img, s6a, 620, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.4:
                pp = min(1, (tt - 0.4) / 0.35)
                sc = 1.3 - 0.3 * ease_out(pp)
                z = s6b.resize((int(s6b.width * sc), int(s6b.height * sc)))
                paste_center(img, z, 880, alpha=pp)
            if tt > 1.3:
                paste_center(img, s6c, 1130, alpha=ease_out(min(1, (tt - 1.3) / 0.5)))
        else:
            draw_cta(img, c, t - 36.4)
        return img

    return frame, 41.4


# --- カバー画像 -------------------------------------------------------------
# リールは全要素がフェードインするので1フレーム目がほぼ空白。Instagramに自動選択
# させるとプロフィールが白紙で並ぶため、カバーは必ず別途アップロードする。
#
# ⚠️切り抜きの制約: リールのカバーはプロフィールのグリッドで中央から切られる。
#   3:4で切ると y240〜1680、1:1で切ると y420〜1500 しか残らない。
#   → 文字はすべて **y500〜1400** に収める(どちらで切られても読める)。
COVER_SAFE = (500, 1400)


def render_kogaku2026(T):
    """T案(修正): 高額療養費の上限が2026年8月から上がった話。
    初版は「87,430円→92,940円」を大きく出し、前提の所得区分を42pxで最後に小さく添えていた。
    上限は区分で4.4倍ちがうため、これは誤解を招く。前提を数字より先に出し、
    区分ごとの幅を見せる場面を独立させた。約36秒。"""
    em = emoji_layer("🏥", 200)
    hook = text_layer("入院したときの上限額が\n今月から上がりました", font(78), T["ink"])
    hook2 = text_layer("2026年8月の診療分から", font(52), T["sub"])

    s2a = text_layer("高額療養費という制度です", font(56), T["sub"])
    s2b = text_layer("1か月の医療費が\n上限を超えたら戻ってくる", font(66), T["ink"])
    s2c = text_layer("その上限が 引き上げられました", font(50), T["brand_d"])

    s3 = text_layer("まず 前提から", font(56), T["sub"])
    b0 = bar_layer("標準報酬月額 28〜50万円の人", "上限は所得で変わります。これは真ん中の区分", T)
    b1 = bar_layer("医療費が100万円かかった月", "窓口ではいったん30万円払います", T)
    b2 = bar_layer("これまでの上限 87,430円", "超えた分は戻ってきました", T)
    b3 = bar_layer("今月からの上限 92,940円", "戻る額が その分だけ減ります", T)

    s4a = text_layer("差額はいくらか", font(56), T["sub"])
    cf = font(150)
    s4b = text_layer("1回の入院で 増える負担です", font(50), T["ink"])

    s5a = text_layer("上限額は 所得で変わります", font(58), T["ink"])
    w1 = bar_layer("標準報酬月額 26万円以下", "上限 61,500円(定額)", T)
    w2 = bar_layer("標準報酬月額 28〜50万円", "上限 92,940円 ← さっきの例", T)
    w3 = bar_layer("標準報酬月額 83万円以上", "上限 271,290円", T)
    s5b = text_layer("医療費100万円の月の場合。自分の区分は\n給与明細か加入先の健康保険で確認できます", font(40), T["sub"])

    s6a = text_layer("増えただけではありません", font(54), T["ink"])
    s6b = text_layer("「年間上限」が\n新しくできました", font(66), T["brand_d"])
    s6c = text_layer("8月から翌年7月の合計が上限に達したら\nその年はもう払わなくていい", font(44), T["sub"])

    s7a = text_layer("知っておくと損しないこと", font(56), T["sub"])
    v1 = bar_layer("マイナ保険証を窓口で出す", "支払いが最初から上限額までになります", T)
    v2 = bar_layer("あとから申請すると3か月以上", "その間は立て替えたままです", T)

    c = cta_save(T, "入院が決まる前に", "保存 しておく")

    def frame(t):
        img = Image.new("RGB", (W, H), T["bg"])
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 14], fill=T["brand"])
        d.rectangle([0, H - 14, W, H], fill=T["brand"])
        if t < 3.2:
            p = ease_out(min(1, t / 0.35))
            paste_center(img, em, 660, dy=int((1 - p) * 40))
            paste_center(img, hook, 1000, dy=int((1 - p) * 55))
            if t > 1.4:
                paste_center(img, hook2, 1260, alpha=ease_out(min(1, (t - 1.4) / 0.5)))
        elif t < 9.4:
            tt = t - 3.2
            paste_center(img, s2a, 560, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.4:
                pp = min(1, (tt - 0.4) / 0.35)
                sc = 1.22 - 0.22 * ease_out(pp)
                z = s2b.resize((int(s2b.width * sc), int(s2b.height * sc)))
                paste_center(img, z, 840, alpha=pp)
            if tt > 1.6:
                paste_center(img, s2c, 1140, alpha=ease_out(min(1, (tt - 1.6) / 0.5)))
        elif t < 18.0:
            tt = t - 9.4
            paste_center(img, s3, 400, alpha=ease_out(min(1, tt / 0.4)))
            for i, b in enumerate([b0, b1, b2, b3]):
                st = 0.4 + i * 1.25
                if tt < st:
                    break
                q = ease_out(min(1, (tt - st) / 0.4))
                paste_at(img, b, 90, 660 + i * 210, alpha=q, dx=int((1 - q) * -70))
        elif t < 24.0:
            tt = t - 18.0
            paste_center(img, s4a, 560, alpha=ease_out(min(1, tt / 0.4)))
            cp = ease_out(min(1, max(0.0, (tt - 0.6) / 1.6)))
            txt = f"＋{int(5510 * cp):,} 円"
            tw = d.textlength(txt, font=cf)
            d.text(((W - tw) / 2, 850), txt, font=cf, fill=T["brand_d"])
            if cp >= 1.0:
                paste_center(img, s4b, 1150, alpha=ease_out(min(1, (tt - 2.4) / 0.5)))
        elif t < 31.5:
            tt = t - 24.0
            paste_center(img, s5a, 460, alpha=ease_out(min(1, tt / 0.4)))
            for i, b in enumerate([w1, w2, w3]):
                st = 0.4 + i * 1.25
                if tt < st:
                    break
                q = ease_out(min(1, (tt - st) / 0.4))
                paste_at(img, b, 90, 720 + i * 210, alpha=q, dx=int((1 - q) * -70))
            if tt > 4.4:
                paste_center(img, s5b, 1420, alpha=ease_out(min(1, (tt - 4.4) / 0.5)))
        elif t < 38.0:
            tt = t - 31.5
            paste_center(img, s6a, 560, alpha=ease_out(min(1, tt / 0.4)))
            paste_center(img, s6b, 850, alpha=ease_out(min(1, max(0.0, tt - 0.4) / 0.5)))
            if tt > 1.2:
                paste_center(img, s6c, 1180, alpha=ease_out(min(1, (tt - 1.2) / 0.5)))
        elif t < 44.5:
            tt = t - 38.0
            paste_center(img, s7a, 500, alpha=ease_out(min(1, tt / 0.4)))
            for i, b in enumerate([v1, v2]):
                st = 0.4 + i * 1.3
                if tt < st:
                    break
                q = ease_out(min(1, (tt - st) / 0.4))
                paste_at(img, b, 90, 780 + i * 210, alpha=q, dx=int((1 - q) * -70))
        else:
            draw_cta(img, c, t - 44.5)
        return img

    return frame, 49.5


def render_kokofurikomi(T):
    """U案: 高校無償化のお金は本人の口座に振り込まれない(学校が代理受領する)。
    サジェストで「高校無償化 いつ振り込まれる」が上位に出ており、誤解が明確にある。約30秒。"""
    em = emoji_layer("🎓", 200)
    hook = text_layer("高校無償化のお金は\nあなたの口座に入りません", font(76), T["ink"])
    hook2 = text_layer("でも 損はしていません", font(52), T["sub"])

    s2a = text_layer("就学支援金という制度です", font(56), T["sub"])
    s2b = text_layer("学校が あなたの代わりに\n受け取ります", font(66), T["ink"])
    s2c = text_layer("そのぶん 授業料の請求が減ります", font(50), T["brand_d"])

    s3 = text_layer("だから こう見えます", font(56), T["sub"])
    b1 = bar_layer("通帳には何も入りません", "振込を待っても永遠に来ません", T)
    b2 = bar_layer("授業料の請求が減る", "または請求そのものが来ない", T)
    b3 = bar_layer("お金が動いて見えない", "これで正常です", T)

    s4a = text_layer("ただし 落とし穴があります", font(56), T["sub"])
    s4b = text_layer("申請しないと\n支給されません", font(74), T["brand_d"])
    s4c = text_layer("自動では始まりません", font(50), T["ink"])

    s5a = text_layer("やることは2つだけ", font(58), T["ink"])
    w1 = bar_layer("入学したら 学校の案内を出す", "オンライン申請が中心です", T)
    w2 = bar_layer("年に1回 継続の手続き", "出し忘れると 支給が止まります", T)

    s6a = text_layer("対象になる人", font(56), T["sub"])
    s6b = text_layer("所得制限は ありません", font(72), T["ink"])
    s6c = text_layer("2026年度から全世帯が対象です。\n私立の上限額は都道府県の上乗せで変わります", font(44), T["sub"])

    c = cta_save(T, "入学の前に", "保存 しておく")

    def frame(t):
        img = Image.new("RGB", (W, H), T["bg"])
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 14], fill=T["brand"])
        d.rectangle([0, H - 14, W, H], fill=T["brand"])
        if t < 3.2:
            p = ease_out(min(1, t / 0.35))
            paste_center(img, em, 660, dy=int((1 - p) * 40))
            paste_center(img, hook, 1000, dy=int((1 - p) * 55))
            if t > 1.4:
                paste_center(img, hook2, 1260, alpha=ease_out(min(1, (t - 1.4) / 0.5)))
        elif t < 9.4:
            tt = t - 3.2
            paste_center(img, s2a, 560, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.4:
                pp = min(1, (tt - 0.4) / 0.35)
                sc = 1.22 - 0.22 * ease_out(pp)
                z = s2b.resize((int(s2b.width * sc), int(s2b.height * sc)))
                paste_center(img, z, 840, alpha=pp)
            if tt > 1.6:
                paste_center(img, s2c, 1140, alpha=ease_out(min(1, (tt - 1.6) / 0.5)))
        elif t < 17.0:
            tt = t - 9.4
            paste_center(img, s3, 430, alpha=ease_out(min(1, tt / 0.4)))
            for i, b in enumerate([b1, b2, b3]):
                st = 0.4 + i * 1.25
                if tt < st:
                    break
                q = ease_out(min(1, (tt - st) / 0.4))
                paste_at(img, b, 90, 700 + i * 210, alpha=q, dx=int((1 - q) * -70))
        elif t < 24.0:
            tt = t - 17.0
            paste_center(img, s4a, 560, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.5:
                pp = min(1, (tt - 0.5) / 0.35)
                sc = 1.25 - 0.25 * ease_out(pp)
                z = s4b.resize((int(s4b.width * sc), int(s4b.height * sc)))
                paste_center(img, z, 880, alpha=pp)
            if tt > 1.8:
                paste_center(img, s4c, 1180, alpha=ease_out(min(1, (tt - 1.8) / 0.5)))
        elif t < 31.4:
            tt = t - 24.0
            paste_center(img, s5a, 500, alpha=ease_out(min(1, tt / 0.4)))
            for i, b in enumerate([w1, w2]):
                st = 0.4 + i * 1.3
                if tt < st:
                    break
                q = ease_out(min(1, (tt - st) / 0.4))
                paste_at(img, b, 90, 780 + i * 210, alpha=q, dx=int((1 - q) * -70))
        elif t < 37.6:
            tt = t - 31.4
            paste_center(img, s6a, 560, alpha=ease_out(min(1, tt / 0.4)))
            paste_center(img, s6b, 830, alpha=ease_out(min(1, max(0.0, tt - 0.4) / 0.5)))
            if tt > 1.2:
                paste_center(img, s6c, 1150, alpha=ease_out(min(1, (tt - 1.2) / 0.5)))
        else:
            draw_cta(img, c, t - 37.6)
        return img

    return frame, 42.6


def render_jidoshikyubi(T):
    """V案: 児童手当は毎月は振り込まれない(偶数月に2か月分)。
    「児童手当 支給日」はサジェストで最上位級のワードなのに、どの解説にも書いていない。約30秒。"""
    em = emoji_layer("🗓️", 200)
    hook = text_layer("児童手当は\n毎月は振り込まれません", font(80), T["ink"])
    hook2 = text_layer("入金がないと不安になる人が多い話です", font(48), T["sub"])

    s2a = text_layer("正しくは こうです", font(56), T["sub"])
    s2b = text_layer("年6回 偶数月に\n2か月分ずつ", font(70), T["ink"])
    s2c = text_layer("2・4・6・8・10・12月", font(56), T["brand_d"])

    s3 = text_layer("たとえば こうなります", font(56), T["sub"])
    b1 = bar_layer("2月に 12月分と1月分", "2か月分がまとめて入ります", T)
    b2 = bar_layer("4月に 2月分と3月分", "以降も同じリズムで続きます", T)
    b3 = bar_layer("月内の何日かは自治体しだい", "10日・15日など ばらつきます", T)

    s4a = text_layer("1回に入る額は(0〜2歳)", font(56), T["sub"])
    cf = font(150)
    s4b = text_layer("月15,000円 × 2か月分", font(54), T["ink"])
    s4c = text_layer("3歳〜高校生は月10,000円、第3子以降は月30,000円", font(40), T["sub"])

    s5a = text_layer("2024年10月から変わりました", font(54), T["ink"])
    w1 = bar_layer("高校生年代まで対象に", "以前は中学生まででした", T)
    w2 = bar_layer("所得制限が撤廃", "年収に関係なく受け取れます", T)

    s6a = text_layer("ここだけは 気をつけて", font(56), T["sub"])
    s6b = text_layer("引っ越し・出産は\n15日以内に手続き", font(68), T["brand_d"])
    s6c = text_layer("遅れた分は さかのぼって受け取れません", font(46), T["sub"])

    c = cta_save(T, "次の支給月の前に", "保存 しておく")

    def frame(t):
        img = Image.new("RGB", (W, H), T["bg"])
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 14], fill=T["brand"])
        d.rectangle([0, H - 14, W, H], fill=T["brand"])
        if t < 3.2:
            p = ease_out(min(1, t / 0.35))
            paste_center(img, em, 660, dy=int((1 - p) * 40))
            paste_center(img, hook, 1000, dy=int((1 - p) * 55))
            if t > 1.4:
                paste_center(img, hook2, 1260, alpha=ease_out(min(1, (t - 1.4) / 0.5)))
        elif t < 9.4:
            tt = t - 3.2
            paste_center(img, s2a, 560, alpha=ease_out(min(1, tt / 0.4)))
            if tt > 0.4:
                pp = min(1, (tt - 0.4) / 0.35)
                sc = 1.22 - 0.22 * ease_out(pp)
                z = s2b.resize((int(s2b.width * sc), int(s2b.height * sc)))
                paste_center(img, z, 850, alpha=pp)
            if tt > 1.6:
                paste_center(img, s2c, 1160, alpha=ease_out(min(1, (tt - 1.6) / 0.5)))
        elif t < 17.0:
            tt = t - 9.4
            paste_center(img, s3, 430, alpha=ease_out(min(1, tt / 0.4)))
            for i, b in enumerate([b1, b2, b3]):
                st = 0.4 + i * 1.25
                if tt < st:
                    break
                q = ease_out(min(1, (tt - st) / 0.4))
                paste_at(img, b, 90, 700 + i * 210, alpha=q, dx=int((1 - q) * -70))
        elif t < 25.0:
            tt = t - 17.0
            paste_center(img, s4a, 520, alpha=ease_out(min(1, tt / 0.4)))
            cp = ease_out(min(1, max(0.0, (tt - 0.6) / 1.8)))
            txt = f"{int(30000 * cp):,} 円"
            tw = d.textlength(txt, font=cf)
            d.text(((W - tw) / 2, 830), txt, font=cf, fill=T["brand_d"])
            if cp >= 1.0:
                paste_center(img, s4b, 1120, alpha=ease_out(min(1, (tt - 2.6) / 0.5)))
                paste_center(img, s4c, 1260, alpha=ease_out(min(1, (tt - 3.0) / 0.5)))
        elif t < 31.4:
            tt = t - 25.0
            paste_center(img, s5a, 500, alpha=ease_out(min(1, tt / 0.4)))
            for i, b in enumerate([w1, w2]):
                st = 0.4 + i * 1.3
                if tt < st:
                    break
                q = ease_out(min(1, (tt - st) / 0.4))
                paste_at(img, b, 90, 780 + i * 210, alpha=q, dx=int((1 - q) * -70))
        elif t < 37.6:
            tt = t - 31.4
            paste_center(img, s6a, 560, alpha=ease_out(min(1, tt / 0.4)))
            paste_center(img, s6b, 850, alpha=ease_out(min(1, max(0.0, tt - 0.4) / 0.5)))
            if tt > 1.2:
                paste_center(img, s6c, 1180, alpha=ease_out(min(1, (tt - 1.2) / 0.5)))
        else:
            draw_cta(img, c, t - 37.6)
        return img

    return frame, 42.6


def row_layer(no, text, note, T, w=920, h=140):
    """一覧用の1行。番号バッジ＋見出し＋損失額。"""
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([0, 0, w, h], radius=24, fill=T["soft"])
    d.rounded_rectangle([0, 0, 86, h], radius=24, fill=T["brand"])
    d.rectangle([62, 0, 86, h], fill=T["brand"])
    nf = font(54)
    nw = d.textlength(str(no), font=nf)
    d.text(((86 - nw) / 2, (h - 66) / 2), str(no), font=nf, fill="#FFFFFF")
    d.text((112, 22), text, font=font(50), fill=T["ink"])
    d.text((112, 84), note, font=font(36), fill=T["brand_d"])
    return lay


# 「あ、そうなんだ」で終わる知識は入れない。
# 期限があり、動かなければ確実に金額が消えるものだけに絞る。
MATOME_ITEMS = [
    ("児童手当は15日以内", "1日遅れると1か月分が消えます",
     "出生届を出したあと", "月1〜3万円",
     "遅れた月の分はさかのぼれません。\n里帰り中でも住所地の市区町村へ"),
    ("ワンストップが無効になる", "控除がまるごと消えます",
     "医療費控除を申告した年", "48,000円",
     "5万円寄付した場合の自己負担。\n確定申告で寄付金控除も一緒に出せば防げます"),
    ("出産した年の医療費控除", "申告しないと1円も戻りません",
     "5年で時効", "数万円",
     "会社の年末調整ではできません。\n過去5年分は今からでも申告できます"),
    ("高校無償化は自動ではない", "申請しないと支給されません",
     "所得制限が無くなっても", "年45.7万円",
     "私立の上限額。学校からの案内を必ず出す。\n毎年の継続手続きも必要です"),
    ("認可外は「認定」が要る", "認定が無いと無償化されません",
     "預かり保育・ベビーシッターも", "月3.7万円",
     "市区町村の「保育の必要性の認定」が必要。\n申請しないと1円も出ません"),
    ("高額療養費は2年で時効", "過ぎた分は取り戻せません",
     "入院・帝王切開した方", "数万〜数十万円",
     "マイナ保険証を窓口で出せば、\nそもそも立て替えずに済みます"),
]


def render_matome(T):
    """W案(作り直し): 動かないと金が消える6つ。
    初版は8項目のうち半分が「あ、そうなんだ」で終わる知識で、行動につながらなかった。
    期限があり損失額が言えるものだけに絞り、一覧を先に出してから各項目を掘る。約31秒。"""
    em = emoji_layer("⚠️", 190)
    hook = text_layer("動かないと\nお金が消えます", font(90), T["ink"])
    hook2 = text_layer("期限があるもの 6つ", font(58), T["sub"])

    rows = [row_layer(i + 1, it[0], it[1], T) for i, it in enumerate(MATOME_ITEMS)]
    title = text_layer("放置すると消えるお金 6", font(56), T["ink"])
    foot = text_layer("こそだて給付ナビ", font(38), T["sub"])

    # 詳細シーンの部品
    det = []
    for i, (head, _sub, when, amount, how) in enumerate(MATOME_ITEMS):
        det.append({
            "no": text_layer(f"{i + 1}", font(120), T["brand"]),
            "head": text_layer(head, font(74), T["ink"]),
            "when": text_layer(when, font(46), T["sub"]),
            "amt": text_layer(amount, font(104), T["brand_d"]),
            "lost": text_layer("が受け取れなくなります", font(44), T["ink"]),
            "how": text_layer(how, font(44), T["sub"]),
        })

    c = cta_save(T, "必要になる前に", "保存 しておく")

    Y0, DY = 520, 155

    def draw_list(img, shown):
        paste_center(img, title, 390)
        for i in range(shown):
            paste_at(img, rows[i], 80, Y0 + i * DY)
        paste_center(img, foot, 1490)

    def frame(t):
        img = Image.new("RGB", (W, H), T["bg"])
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 14], fill=T["brand"])
        d.rectangle([0, H - 14, W, H], fill=T["brand"])
        if t < 3.4:
            p = ease_out(min(1, t / 0.3))
            paste_center(img, em, 640, dy=int((1 - p) * 40))
            paste_center(img, hook, 1000, dy=int((1 - p) * 55))
            if t > 1.5:
                paste_center(img, hook2, 1300, alpha=ease_out(min(1, (t - 1.5) / 0.4)))
        elif t < 9.6:
            # 一覧をバーンと出す。0.22秒間隔で一気に積み、あとは静止で全体を見せる。
            tt = t - 3.4
            draw_list(img, min(len(rows), int(tt / 0.22) + 1))
        elif t < 31.2:
            i = min(len(det) - 1, int((t - 9.6) / 3.6))
            tt = (t - 9.6) - i * 3.6
            x = det[i]
            paste_center(img, x["no"], 400, alpha=ease_out(min(1, tt / 0.25)))
            paste_center(img, x["head"], 600, alpha=ease_out(min(1, tt / 0.3)))
            if tt > 0.4:
                paste_center(img, x["when"], 760, alpha=ease_out(min(1, (tt - 0.4) / 0.3)))
            if tt > 0.8:
                pp = min(1, (tt - 0.8) / 0.3)
                sc = 1.3 - 0.3 * ease_out(pp)
                z = x["amt"].resize((int(x["amt"].width * sc), int(x["amt"].height * sc)))
                paste_center(img, z, 950, alpha=pp)
            if tt > 1.4:
                paste_center(img, x["lost"], 1090, alpha=ease_out(min(1, (tt - 1.4) / 0.3)))
            if tt > 1.9:
                paste_center(img, x["how"], 1290, alpha=ease_out(min(1, (tt - 1.9) / 0.4)))
        elif t < 36.4:
            # 保存用にもう一度、全6項目を静止で出す
            draw_list(img, len(rows))
        else:
            draw_cta(img, c, t - 36.4)
        return img

    return frame, 41.4


# 早見表の仕様。ここに1件足せばリールが1本増える。
# 数字はすべて data/programs.json 側で一次情報を確認済みのもの。
HAYAMI = {
    "kabe-hayami": {
        "badge": "2026年版",
        "hook": ("103万の壁を", "まだ気にしていませんか",
                 "その壁は、もうありません", "いまの壁は 4つです"),
        "title": ("年収の壁", "ぜんぶ一覧", "103万の壁は、もうありません"),
        "cta": ("働き方を決める前に", "保存 しておく"),
        "rows": [
            ("106万円", "社会保険に入る", "勤務先の規模など条件つき", "手取りが減る", True),
            ("123万円", "名前が変わるだけ", "配偶者控除→配偶者特別控除", "手取りは減らない", False),
            ("130万円", "社会保険に入る", "106万の条件に当たらない人", "手取りが減る", True),
            ("160万円", "所得税がかかる", "ここから控除も減り始める", "少しずつ減る", True),
        ],
        "details": [
            ("106万円", "社会保険に入ります",
             "週20時間以上・月8.8万円以上などの条件を満たすと、\n勤務先の社会保険に加入します",
             "手取りは減りますが、将来の年金は増え、\n傷病手当金も使えるようになります", True),
            ("123万円", "実は、何も減りません",
             "配偶者控除から配偶者特別控除に切り替わるだけで、\n控除額は満額のまま引き継がれます",
             "ここで働くのをやめるのが、いちばんもったいない", False),
            ("130万円", "106万に当てはまらない人の壁",
             "勤務先の規模などで106万の条件に当たらない場合、\nここで社会保険の扶養から外れます",
             "こちらは条件がなく、超えれば加入になります", True),
            ("160万円", "ここで初めて所得税",
             "基礎控除と給与所得控除の引き上げで、\n所得税がかかり始めるのは160万円からです",
             "配偶者特別控除が減り始めるのも、ここから", True),
        ],
    },
    "shussan-hayami": {
        "badge": "2026年版",
        "hook": ("出産でもらえるお金", "ぜんぶ足すと",
                 "知らないと申請しそびれます", "主なものは 4つです"),
        "title": ("出産のお金", "ぜんぶ一覧", "申請しないと受け取れません"),
        "cta": ("産休に入る前に", "保存 しておく"),
        "rows": [
            ("50万円", "出産育児一時金", "健康保険から・子ども1人につき", "全員が対象", False),
            ("給料の2/3", "出産手当金", "会社員が産休を取ったとき", "最大98日分", False),
            ("賃金の67%", "育児休業給付金", "雇用保険から・最初の180日", "その後50%", False),
            ("10万円", "妊婦のための支援給付", "妊娠時5万円＋出生時5万円", "自治体から", False),
        ],
        "details": [
            ("50万円", "出産育児一時金",
             "加入している健康保険から、子ども1人につき50万円。\n直接支払制度を使えば病院に直接支払われます",
             "時効は出産日の翌日から2年です", False),
            ("給料の2/3", "出産手当金",
             "会社員が産休を取ったときに、健康保険から。\n産前42日＋産後56日の最大98日分が対象です",
             "産休が終わってからまとめて申請します", False),
            ("賃金の67%", "育児休業給付金",
             "育休中に雇用保険から。最初の180日は67%、\nその後は50%になります",
             "2か月分ずつの申請なので、初回の入金は先です", True),
            ("10万円", "妊婦のための支援給付",
             "妊娠を届け出たときに5万円、\n出産後にこども1人につき5万円",
             "受け取り方は市区町村によって違います", False),
        ],
    },
    "gakuhi-hayami": {
        "badge": "2026年度",
        "hook": ("高校と大学の学費", "いくら支援されるか",
                 "申請しないと1円も出ません", "主なものは 4つです"),
        "title": ("学費の支援", "ぜんぶ一覧", "所得制限は撤廃されました"),
        "cta": ("進学を決める前に", "保存 しておく"),
        "rows": [
            ("11.9万円", "公立高校の授業料", "就学支援金・実質無償になります", "申請が必要", True),
            ("45.7万円", "私立高校の授業料", "就学支援金の年間上限", "所得制限なし", False),
            ("70万円", "私立大学の授業料", "子ども3人以上の多子世帯", "入学金26万も", False),
            ("返済不要", "給付型奨学金", "修学支援新制度・世帯収入で判定", "高3春に予約", True),
        ],
        "details": [
            ("11.9万円", "公立高校は実質無償",
             "高等学校等就学支援金から年11万8,800円。\n授業料相当額なので、実質的に無償になります",
             "自動では始まりません。学校の案内を必ず出す", True),
            ("45.7万円", "私立高校の上限額",
             "2026年度から所得制限が撤廃され、\n私立の加算額も引き上げられました",
             "お金は口座に入らず、授業料と相殺されます", False),
            ("70万円", "多子世帯なら大学も",
             "扶養する子どもが3人以上なら、所得制限なしで\n私立大の授業料70万円・入学金26万円まで減免",
             "上の子が就職して扶養を外れると対象外に", False),
            ("返済不要", "給付型奨学金",
             "高等教育の修学支援新制度。授業料等の減免と\n返さなくていい奨学金がセットです",
             "高3の春の「予約採用」が入口になります", True),
        ],
    },
    "kigen-hayami": {
        "badge": "時効あり",
        "hook": ("申請の期限を", "過ぎていませんか",
                 "1日でも遅れると戻りません", "特に危ないのは 4つ"),
        "title": ("申請の期限", "ぜんぶ一覧", "過ぎると取り戻せません"),
        "cta": ("忘れてしまう前に", "保存 しておく"),
        "rows": [
            ("15日", "児童手当", "出生・転入した日の翌日から", "遅れた月は消える", True),
            ("2年", "高額療養費", "診療した月の翌月1日から", "入院した分", True),
            ("2年", "出産のお金", "出産育児一時金・出産手当金", "健康保険の給付", True),
            ("5年", "医療費控除", "さかのぼって申告できます", "今からでも間に合う", False),
        ],
        "details": [
            ("15日", "児童手当がいちばん危ない",
             "出生・転入した日の翌日から15日以内。\n遅れた月の分はさかのぼって受け取れません",
             "里帰り中でも、申請先は住所地の市区町村です", True),
            ("2年", "高額療養費",
             "診療した月の翌月1日から2年で時効。\n入院や帝王切開で高額を払った分が対象です",
             "マイナ保険証を出せば、そもそも立て替え不要", True),
            ("2年", "出産のお金も2年",
             "出産育児一時金は出産日の翌日から、\n出産手当金は産休開始の翌日から2年です",
             "直接支払制度を使わなかった分は要申請", True),
            ("5年", "医療費控除は5年戻れる",
             "唯一、過去にさかのぼれるものです。\n出産した年の分をまだ申告していないなら間に合います",
             "会社の年末調整ではできません。確定申告です", False),
        ],
    },
}


# --- 早見表スタイル -------------------------------------------------------
# 従来のカバー(絵文字1つ+2行)は余白が多く、サムネイルの時点で
# 「読む価値がある」と伝わらなかった。参考にした3アカウント
# (moneylabo_cat / sugar_mane7 / fp.daisuke)はいずれも表紙が早見表として
# 成立している。1本ごとに書かず、仕様(HAYAMI)を足すだけで増やせる形にする。
PAPER = "#FBF8F4"
P_INK = "#23262E"
P_SUB = "#6B7280"
P_WARM = "#F4643B"
P_COOL = "#2F6C7A"
P_LINE = "#E7DED3"


def paper_bg(img):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, H], fill=PAPER)
    band = Image.new("RGB", (W, 520), "#F3E7DC")
    img.paste(band.filter(ImageFilter.GaussianBlur(60)), (0, -160))
    band2 = Image.new("RGB", (W, 420), "#EFE6DE")
    img.paste(band2.filter(ImageFilter.GaussianBlur(60)), (0, H - 300))
    d.rectangle([0, 0, W, 18], fill=P_WARM)
    d.rectangle([0, H - 18, W, H], fill=P_WARM)


def pill(d, x, y, text, fill):
    f = font(40)
    tw = d.textlength(text, font=f)
    d.rounded_rectangle([x, y, x + tw + 44, y + 66], radius=33, fill=fill)
    d.text((x + 22, y + 8), text, font=f, fill="#FFFFFF")
    return tw + 44


def hayami_row(no, key, what, cond, effect, warm):
    """1行 = 見出しの数字 + 制度名 + 条件 + 効き方。表紙のまま早見表になる密度にする。"""
    lay = Image.new("RGBA", (960, 178), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([0, 0, 960, 178], radius=22, fill="#FFFFFF")
    d.rounded_rectangle([0, 0, 960, 178], radius=22, outline=P_LINE, width=2)
    tint = "#FFF3EC" if warm else "#EEF4F6"
    col = P_WARM if warm else P_COOL
    d.rounded_rectangle([0, 0, 288, 178], radius=22, fill=tint)
    d.rectangle([266, 0, 288, 178], fill=tint)
    # 数字は文字数で自動縮小(「45.7万円」も「返済不要」も同じ枠に収める)
    size = 66
    while size > 34 and d.textlength(key, font=font(size)) > 250:
        size -= 4
    kf = font(size)
    kw = d.textlength(key, font=kf)
    d.text(((288 - kw) / 2, 34 + (66 - size) // 2), key, font=kf, fill=col)
    d.text((22, 118), f"{no}つ目", font=font(30), fill=P_SUB)
    d.text((320, 24), what, font=font(50), fill=P_INK)
    d.text((320, 86), cond, font=font(31), fill=P_SUB)
    ef = font(33)
    ew = d.textlength(effect, font=ef)
    d.rounded_rectangle([938 - ew - 32, 118, 938, 166], radius=24, fill=tint)
    d.text((938 - ew - 16, 126), effect, font=ef, fill=col)
    return lay


P_ID = "#3A4A52"          # 肩書きピルの地色。毎回同じ位置・同じ色で出す
ID_TEXT = "出典は国の公式資料"


def brand_pills(d, badge=None):
    """全リール共通の頭。肩書き→保存版→(文脈)の順で必ず同じ並びにする。"""
    x = 74
    x += pill(d, x, 150, ID_TEXT, P_ID) + 14
    x += pill(d, x, 150, "保存版", P_WARM) + 14
    # 文脈バッジは長いと画面からはみ出すので、収まるときだけ出す
    if badge and x + d.textlength(badge, font=font(40)) + 44 < W - 74:
        pill(d, x, 150, badge, "#5B8A94")


def _hayami_list(img, spec, rows, shown):
    d = ImageDraw.Draw(img)
    brand_pills(d, spec.get("badge"))
    paste_center(img, spec["_t1"], 340)
    paste_center(img, spec["_t2"], 476)
    paste_center(img, spec["_t3"], 586)
    for i in range(shown):
        paste_at(img, rows[i], 60, 736 + i * 196)
    paste_center(img, spec["_foot"], 1520)


def _hayami_prepare(spec):
    """テキストレイヤは1度だけ作る(フレームごとに作ると極端に遅くなる)。"""
    if "_t1" in spec:
        return spec
    spec["_t1"] = text_layer(spec["title"][0], font(128), P_INK)
    spec["_t2"] = text_layer(spec["title"][1], font(96), P_WARM)
    spec["_t3"] = text_layer(spec["title"][2], font(46), P_SUB)
    spec["_foot"] = text_layer("こそだて給付ナビ", font(40), P_SUB)
    spec["_rows"] = [hayami_row(i + 1, *r) for i, r in enumerate(spec["rows"])]
    spec["_hook"] = [
        text_layer(spec["hook"][0], font(88), P_INK),
        text_layer(spec["hook"][1], font(80), P_WARM),
        text_layer(spec["hook"][2], font(50), P_SUB),
        text_layer(spec["hook"][3], font(56), P_INK),
    ]
    det = []
    for key, head, body, note, warm in spec["details"]:
        col = P_WARM if warm else P_COOL
        det.append({
            "key": text_layer(key, font(112), col),
            "head": text_layer(head, font(70), P_INK),
            "body": text_layer(body, font(44), P_SUB),
            "note": text_layer(note, font(46), col),
        })
    spec["_det"] = det
    return spec


def hayami(name):
    """仕様名から描画関数を作る。REELS には hayami("...") を入れる。"""
    def render(T):
        spec = _hayami_prepare(HAYAMI[name])
        rows, det, hk = spec["_rows"], spec["_det"], spec["_hook"]
        n = len(det)
        t_list = 12.0
        t_det = t_list + n * 5.5
        t_list2 = t_det + 6.0
        dur = t_list2 + 5.0
        c = cta_save(T, spec["cta"][0], spec["cta"][1])

        def frame(t):
            img = Image.new("RGB", (W, H), PAPER)
            paper_bg(img)
            brand_pills(ImageDraw.Draw(img), spec.get("badge"))
            if t < 4.0:
                p = ease_out(min(1, t / 0.3))
                paste_center(img, hk[0], 720, dy=int((1 - p) * 50))
                paste_center(img, hk[1], 850, dy=int((1 - p) * 50))
                if t > 1.4:
                    paste_center(img, hk[2], 1030, alpha=ease_out(min(1, (t - 1.4) / 0.4)))
                if t > 2.4:
                    paste_center(img, hk[3], 1180, alpha=ease_out(min(1, (t - 2.4) / 0.4)))
            elif t < t_list:
                _hayami_list(img, spec, rows, min(n, int((t - 4.0) / 0.5) + 1))
            elif t < t_det:
                i = min(n - 1, int((t - t_list) / 5.5))
                tt = (t - t_list) - i * 5.5
                x = det[i]
                paste_center(img, x["key"], 430, alpha=ease_out(min(1, tt / 0.25)))
                paste_center(img, x["head"], 610, alpha=ease_out(min(1, tt / 0.3)))
                if tt > 0.6:
                    paste_center(img, x["body"], 830, alpha=ease_out(min(1, (tt - 0.6) / 0.4)))
                if tt > 2.0:
                    paste_center(img, x["note"], 1100, alpha=ease_out(min(1, (tt - 2.0) / 0.4)))
            elif t < t_list2:
                _hayami_list(img, spec, rows, n)
            else:
                draw_cta(img, c, t - t_list2)
            return img

        return frame, dur
    return render


def cover_hayami(name):
    def build(T):
        spec = _hayami_prepare(HAYAMI[name])
        img = Image.new("RGB", (W, H), PAPER)
        paper_bg(img)
        _hayami_list(img, spec, spec["_rows"], len(spec["_rows"]))
        return img
    return build

CAPTION_SHUSSAN_H = """【出産のお金 ぜんぶ一覧】

📌 産休に入る前に、この1枚を保存しておいてください。

出産でもらえるお金は、どれも【申請しないと受け取れません】。主なものを4つにまとめました。

━━━━━━━━━━
①【50万円】出産育児一時金
加入している健康保険から、子ども1人につき50万円。
直接支払制度を使えば病院に直接支払われるので、窓口でまとまったお金を用意せずに済みます。出産費用が50万円を下回ったときは、差額を申請すれば受け取れます。
時効は出産日の翌日から2年です。

②【給料の2/3】出産手当金
会社員が産休を取ったときに、健康保険から。
産前42日＋産後56日の最大98日分が対象です。産休が終わってからまとめて申請するのが一般的なので、産休に入ってすぐ入るわけではありません。
時効は産休開始の翌日から2年。

③【賃金の67%】育児休業給付金
育休中に雇用保険から。最初の180日は67%、その後は50%になります。
両親がそれぞれ14日以上取ると、最大28日間13%が上乗せされます(出生後休業支援給付金)。社会保険料の免除と合わせると、実質手取り10割相当になることもあります。
ただし【2か月分ずつの申請】なので、育休に入ってしばらく入金がない期間があります。ここは生活費の見通しに直結するので気をつけてください。

④【10万円】妊婦のための支援給付
妊娠を届け出たときに5万円、出産後にこども1人につき5万円。
双子なら出生時が10万円になります。受け取り方(現金かクーポンか)は市区町村によって違います。
━━━━━━━━━━

【見落としやすいこと】
出産した年は医療費が10万円を超えやすいので、医療費控除も使えます。こちらは確定申告が必要で、5年さかのぼれます。

─────────
※金額・条件は加入している健康保険や自治体により異なります。
出典:こども家庭庁／厚生労働省。申請前に勤務先・健康保険・市区町村でご確認ください。

#出産準備 #プレママ #妊娠中 #臨月 #産休 #育休 #出産育児一時金 #出産手当金 #育児休業給付金 #新生児 #初マタ #お金の勉強 #家計管理 #子育て
"""

CAPTION_GAKUHI_H = """【学費の支援 ぜんぶ一覧・2026年度】

📌 進学を決める前に、保存しておいてください。

高校も大学も、支援は【申請しないと1円も出ません】。所得制限は撤廃されましたが、自動では始まらないのがいちばんの落とし穴です。

━━━━━━━━━━
①【11.9万円】公立高校の授業料
高等学校等就学支援金から年11万8,800円。授業料相当額なので、実質的に無償になります。
ただし自動では始まりません。入学時の4月に学校を通じて申請し、その後も毎年の継続手続きが必要です。オンライン申請システム「e-Shien」から手続きできます。

②【45.7万円】私立高校の授業料
2026年度から所得制限が撤廃され、私立の加算額も引き上げられました。
【重要】このお金は保護者や生徒の口座には振り込まれません。学校が代わりに受け取り、授業料と相殺されます。通帳ではなく、学校からの授業料の請求額を見てください。

③【70万円】私立大学の授業料
扶養する子どもが3人以上の多子世帯なら、所得制限なしで授業料70万円・入学金26万円まで減免されます(国公立大なら授業料54万円・入学金28万円)。
注意点は「扶養する子が3人以上」という条件です。上の子が就職して扶養から外れると、下の子が対象外になることがあります。きょうだいの年齢が離れている家庭ほど、事前に確認する価値があります。
対象は大学・短大・高専・専門学校で、大学院は含まれません。

④【返済不要】給付型奨学金
高等教育の修学支援新制度。授業料等の減免と、返さなくていい奨学金がセットになっています。
入口は高校3年の春(4月下旬ごろ)の「予約採用」です。進学後に申し込む「在学採用」は年2回。
━━━━━━━━━━

【授業料以外もあります】
高校生等奨学給付金は、教材費や制服代など授業料以外の教育費が対象です(非課税世帯など)。金額は都道府県が設定します。

─────────
※上限額・条件は学校の種類や都道府県により異なります。
出典:文部科学省。詳しくは学校・都道府県でご確認ください。

#高校無償化 #大学無償化 #就学支援金 #教育費 #学費 #奨学金 #高校受験 #大学受験 #中学生ママ #高校生ママ #多子世帯 #お金の勉強 #家計管理 #子育て
"""

CAPTION_KIGEN_H = """【申請の期限 ぜんぶ一覧】

📌 これは本当に保存しておいてください。過ぎたら取り戻せません。

もらえるはずのお金が消える理由は、たいてい「知らなかった」ではなく「間に合わなかった」です。

━━━━━━━━━━
①【15日】児童手当 ← いちばん危ない
出生・転入した日の【翌日から15日以内】。
遅れた月の分はさかのぼって受け取れません。0〜2歳なら月1万5,000円、第3子以降なら月3万円が、1か月まるごと消えます。
そして見落としやすいのが【里帰り出産】です。実家にいても、申請先は住民票のある市区町村です。実家の役所ではありません。

②【2年】高額療養費
診療した月の翌月1日から2年で時効。入院や帝王切開で高額を払った分が対象です。
そもそもマイナ保険証を窓口で出せば、支払いが最初から上限額までで済みます。立て替えも、3か月以上の待ち時間も不要になります。

③【2年】出産のお金
出産育児一時金は出産日の翌日から2年、出産手当金は産休開始の翌日から2年。
直接支払制度を使わなかった場合や、出産費用が50万円を下回って差額が出た場合は、申請しないと受け取れません。

④【5年】医療費控除 ← 唯一さかのぼれる
これだけは過去にさかのぼれます。
出産した年の分をまだ申告していないなら、いまからでも間に合います。会社の年末調整ではできないので、確定申告が必要です。
━━━━━━━━━━

【まとめ】
①だけは「今すぐ」の話です。②③は2年、④は5年。
出産・引っ越しの直後は手続きが集中して抜けやすいので、この4つだけでも押さえておいてください。

─────────
※期限や取り扱いは加入している健康保険・自治体により異なる場合があります。
出典:こども家庭庁／協会けんぽ／国税庁。詳しくは各窓口でご確認ください。

#児童手当 #里帰り出産 #出産準備 #産後 #高額療養費 #医療費控除 #確定申告 #新生児 #プレママ #引っ越し #お金の勉強 #家計管理 #子育て #知らないと損
"""


CAPTION_KABE2 = """【年収の壁 ぜんぶ一覧・2026年版】

📌 働き方を決める前に、この1枚を保存しておいてください。

「103万円を超えないように」と調整している方へ。
2025年の税制改正で、その壁はもうありません。いまの壁は4つです。

━━━━━━━━━━
①【106万円】社会保険に入る
週20時間以上・月額賃金8.8万円以上・勤務先の規模などの条件を満たすと、勤務先の社会保険に加入します。
手取りは減りますが、将来の年金が増え、傷病手当金なども使えるようになります。条件は勤務先に確認してください。

②【123万円】名前が変わるだけ
ここがいちばん誤解されています。
123万円を超えると配偶者控除から外れますが、そのまま配偶者特別控除に切り替わり、控除額は満額のまま引き継がれます。
つまり【手取りは減りません】。ここで働くのをやめるのが、いちばんもったいない。

③【130万円】106万に当てはまらない人の壁
勤務先の規模などで106万円の条件に当たらない場合、130万円で社会保険の扶養から外れます。
こちらは条件がなく、超えれば加入になります。

④【160万円】ここで初めて所得税
基礎控除と給与所得控除が引き上げられたため、本人に所得税がかかり始めるのは160万円からになりました。
配偶者特別控除が減り始めるのも、ここからです。
━━━━━━━━━━

【結論】
本当に手取りが減るのは、税金ではなく【社会保険】のほうです。
123万円は名前が変わるだけ。106万・130万を意識してください。

プロフィールのリンクから、年収を入れるとグラフで手取りが動くシミュレーターが使えます。
ご自身の場合がいくらになるか、配偶者の年収も入れて確かめてみてください。

─────────
※基礎控除の上乗せは令和7年分・8年分の措置で、令和9年分以後は変わる予定です。
出典:国税庁／厚生労働省。条件は勤務先・お住まいの状況により異なります。

#年収の壁 #パート #扶養内 #配偶者控除 #社会保険 #働き方 #主婦 #ワーママ #お金の勉強 #家計管理 #子育て #103万の壁 #106万の壁 #130万の壁
"""


COVER_CUSTOM = {k: cover_hayami(k) for k in HAYAMI}

COVERS = {
    "shinsei-list":  ("⚠️", "知らないと", "ずっと 0 円", "申請しないともらえないお金"),
    "jido-teate":    ("🧮", "児童手当って", "18年でいくら？", "0歳から高校生まで の合計"),
    "shussan-okane": ("👶", "出産でもらえるお金", "ぜんぶでいくら？", "だれでも受け取れる分＋会社員の上乗せ"),
    "018support":    ("💰", "東京都に住む人へ", "申請しないと 0 円", "018サポート 月5,000円"),
    "ichisai-kabe":    ("🍼", "保育園に入れないのは", "何歳？", "待機児童の6割は1歳児"),
    "tokyo23-shussan": ("🏙️", "東京23区で出産", "もらえる額に差", "港区は上限81万円"),
    "iryohi-22sai":    ("🏥", "子どもの医療費", "22歳まで無料？", "全国で6自治体だけ"),
    "kigen-list":      ("⏰", "1日過ぎると", "戻ってきません", "見落としやすい申請期限"),
    "ikuji-10wari":    ("👶", "育休の手取りが", "10割になる条件", "2025年4月からの上乗せ"),
    "koko-sagaku":     ("🎓", "高校無償化", "住む県で差が出る", "大阪は年63万円超まで"),
    "kyushoku-2026":   ("🍚", "2026年4月から", "給食費が変わる", "月5,200円・手続き不要"),
    "kogaku-ryoyohi":  ("🏥", "帝王切開の入院費", "いくら戻る？", "高額療養費のしくみ"),
    "iryohi-kojo":     ("🧾", "出産した年は", "お金が戻ります", "医療費控除のしくみ"),
    "nenshu-kabe":     ("🧱", "103万の壁は", "もうありません", "いまの壁は106・123・160万"),
    "ikukyu-jiki":     ("🗓️", "育休は いつ取るかで", "手取りが変わる", "14日に土日祝も含まれます"),
    "furusato":        ("🎁", "ふるさと納税", "子育て世帯の勘違い", "16歳未満は上限に影響しない"),
    "shotoku-seigen":  ("🏥", "所得制限があるのは", "全国で49自治体", "1,740市区町村を調べました"),
    "fuyo-kojo":       ("📋", "子どもが何人いても", "扶養控除は増えない", "16歳未満は対象外です"),
    "hitorioya":       ("🌱", "ひとり親が", "受け取れるお金", "手当・助成・控除をまとめて"),
    "kogaku-2026":     ("🏥", "入院の上限額が", "今月 上がりました", "2026年8月から・年間上限も新設"),
    "koko-furikomi":   ("🎓", "高校無償化のお金は", "口座に入りません", "学校が代わりに受け取ります"),
    "jido-shikyubi":   ("🗓️", "児童手当は", "毎月もらえません", "偶数月に2か月分ずつ"),
    "matome-8":        ("📌", "知らないと損する", "子育てのお金 8", "保存版・1枚にまとめました"),
    "nenkin-ikuji":    ("💴", "自営業の親は", "国民年金が免除されます", "2026年10月から・最大13か月"),
    "kogaku-2nen":     ("⏳", "2年前の入院費", "いまからでも戻ります", "高額療養費はさかのぼれます"),
    "shitsugyo-4nen":  ("🕰️", "出産で辞めた人の", "失業保険は4年待てます", "受給期間は延長できます"),
    "iryohi-5nen":     ("🧾", "医療費控除は", "去年の分だけじゃない", "5年さかのぼれます"),
}


CAPTION_ICHISAI = """【保育園、1歳より0歳のほうが入りやすい理由】

📌 育休をいつまで取るか迷っている人は保存しておいてください。

全国の待機児童は2,254人。その内訳がこちらです。

▶ 0歳 … 164人
▶ 1歳 … 1,361人
▶ 2歳 … 516人
▶ 3歳以上 … 213人

1歳児だけで全体の6割を占めています。
「育休を1年取って、4月に1歳クラスへ」がいちばん激しい競争になります。

一方で、待機児童ゼロの自治体は1,741のうち1,530(88%)。
つまり「入りにくい」は、地域と年齢の組み合わせで決まります。

お住まいの市区町村の待機児童数は、年齢別にプロフィールのリンクから調べられます。

※こども家庭庁「保育所等関連状況取りまとめ」令和7年4月1日時点

#保育園 #待機児童 #育休 #育休復帰 #ワーママ #保活 #子育て #新米ママ #プレママ #仕事と育児"""

CAPTION_TOKYO23 = """【東京23区、出産でもらえる額はこんなに違います】

📌 引っ越しを考えている人は保存推奨です。

区が独自に出しているお金の一例。

▶ 港区 … 出産費用助成 上限81万円
▶ 千代田区 … 出産費用助成 最大31万円
▶ 文京区 … 出産・子育て応援券 10万円分
▶ 江戸川区 … 乳児養育手当 月13,000円

ここでよくある誤解をひとつ。

多くの区が案内している「10万円分のギフト」は、実は区独自ではありません。
国の「妊婦のための支援給付」＋東京都の上乗せで、23区すべて共通です。
区が窓口になるので区の制度に見えるだけです。

23区すべての比較は、プロフィールのリンクから見られます。

※2026年7月時点。金額・条件は変わることがあるので各区の公式ページでご確認ください。

#東京23区 #東京子育て #出産準備 #プレママ #新米ママ #港区 #江戸川区 #文京区 #子育て #給付金"""

CAPTION_IRYOHI22 = """【子どもの医療費、22歳まで無料の自治体があります】

📌 引っ越し先を選ぶときの材料に。保存しておいてください。

全国1,740市区町村のうち、通院の助成が18歳年度末までなのは1,575。
いまや9割が高校卒業まで無料です。

でも、さらに上がありました。

【22歳の年度末まで】全国で6自治体だけ
▶ 北海道 南富良野町
▶ 千葉県 神崎町
▶ 千葉県 多古町
▶ 京都府 京丹後市
▶ 愛媛県 上島町
▶ 高知県 田野町

大学生になっても医療費がかからない計算になります。

お住まいの市区町村が何歳までかは、プロフィールのリンクから調べられます。
全1,741市区町村を収録しています。

※こども家庭庁「こどもに係る医療費の助成についての調査」令和7年4月1日時点

#子ども医療費 #医療費助成 #子育て #移住 #引っ越し #新米ママ #プレママ #ワーママ #自治体 #知って得する"""


# 並び順 = 投稿順。フォルダ名の連番はこの順に振られるので、
# 投稿順を変えたいときはこのリストを並べ替えて再実行する。
CAPTION_KIGEN = """【1日過ぎると戻ってこないお金があります】

📌 期限は覚えられないので、保存しておいてください。

▶ 児童手当 … 出生・転入の翌日から15日以内が原則。遅れると遡れないことがあります
▶ 出産育児一時金 … 出産日の翌日から2年で時効
▶ 高校の就学支援金 … 学校が案内する期限内。申請しないと受け取れません
▶ 多子世帯の大学無償化 … 学校の指定期間内。自動で減免されるわけではありません

一方で、あきらめなくていいものもあります。

▶ 医療費控除 … 申告し忘れても5年前までさかのぼれます
▶ 給食費の負担軽減(2026年4月〜) … そもそも申請不要です

「自動で入ってくるもの」と「申請しないと消えるもの」を分けて把握しておくのが確実です。

※詳しくはお住まいの市区町村・学校・勤務先の案内をご確認ください。

#給付金 #申請忘れ #児童手当 #医療費控除 #子育て #新米ママ #プレママ #ワーママ #家計管理 #知って得する"""

CAPTION_IKUJI10 = """【育休中の手取り、10割になることがあります】

📌 夫婦で育休の取り方を決める前に保存推奨です。

「育休に入ると収入が減る」と思われがちですが、実際はここまで補われます。

▶ 育児休業給付金 … 休業前賃金の67%(開始から180日)→ その後50%
▶ 出生後休業支援給付金 … 夫婦それぞれが14日以上取ると、最大28日間 13%上乗せ
▶ 社会保険料が免除 … 育休中は保険料がかかりません

給付は非課税で、さらに社会保険料もかからないため、
額面の給付率よりも手取りの目減りは小さくなります。
条件がそろうと実質10割相当になることがあります。

ポイントは、**夫婦それぞれが取ること**。
どちらか一方だけだと上乗せの対象になりません。

※2025年4月からの制度です。詳しくは勤務先・ハローワークでご確認ください。

#育休 #育休中 #産休 #育児休業給付金 #パパ育休 #ワーママ #共働き #新米ママ #プレママ #家計管理"""

CAPTION_KOKO = """【高校無償化、住む県で金額が変わります】

📌 進学先を決める前に保存しておいてください。

まず国の制度がこちら。

▶ 公立 … 年11万8,800円(授業料が実質無償)
▶ 私立 … 上限 年45万7,200円

ここに都道府県の上乗せが加わるので、実際の金額は住む場所で変わります。

▶ 大阪府 … 2026年度から全学年で所得制限なし。年63万円を超える授業料も対象
▶ 東京都 … 都独自の助成があり、国と合わせて年最大50万1,000円
▶ 神奈川県 … 2026年度から所得制限を撤廃する見通し

見落としやすいのが条件です。
**県の上乗せは「県内在住かつ県内進学」が要件のことが多い**ので、
越境通学だと国の分しか受けられない場合があります。

なお千葉県のように、国の拡充にあわせて県独自の減免を廃止する県もあります。
これは支援が減ったのではなく、国が肩代わりする形になったということです。

※令和8年度の制度は見直しが進んでいます。必ず各都道府県の公式ページで最新をご確認ください。

#高校無償化 #就学支援金 #高校受験 #教育費 #私立高校 #子育て #中学生ママ #高校生ママ #教育資金 #家計管理"""

CAPTION_KYUSHOKU = """【2026年4月から、給食費が変わります】

📌 意外と知られていないので保存しておいてください。

▶ 児童1人あたり 月額5,200円 を基準に支援
▶ 所得制限なし
▶ 保護者の手続きは不要

5,200円は、これまでの全国平均の給食費に物価上昇を加味した額です。
国と都道府県が1/2ずつ負担します。

ただし注意点がひとつ。

**対象は小学校です。**
中学校は国の制度の対象外ですが、独自に中学校まで無償化している自治体もあります。

給食費以外の学用品費などは「就学援助」の対象になる場合があるので、
そちらもあわせて確認しておくと安心です。

※詳しくはお住まいの市区町村の案内をご確認ください。

#給食費 #給食費無償化 #小学生ママ #教育費 #子育て #新1年生 #家計管理 #節約 #給付金 #知って得する"""


CAPTION_KOGAKU = """【帝王切開になったとき、入院費はいくら戻るか】

📌 入院が決まってからでは調べる余裕がありません。保存推奨です。

まず大前提から。

▶ 正常分娩 … 保険がきかないので高額療養費の対象外
▶ 帝王切開・切迫早産・吸引分娩 … 保険診療なので対象になります

「出産は対象外」と思い込んで申請していない人がとても多い制度です。

【1か月の自己負担の上限】
年収およそ370〜770万円なら
80,100円 ＋（医療費 − 267,000円）× 1%

【たとえば、切迫早産で1か月入院した場合】
▶ 医療費の総額 100万円
▶ 窓口で払う3割 30万円
▶ この月の上限額 約87,430円
→ 戻ってくるのは 約21万円

しかも、立て替えずに済ませる方法があります。

▶ マイナ保険証を使う … 窓口の支払いが最初から上限まで
▶ 限度額適用認定証を用意する … 入院が決まったら健康保険へ申請

【見落としやすい3つ】
▶ 計算は「月ごと」。月をまたぐ入院は合算されません
▶ 時効は2年（診療した月の翌月1日から）
▶ 出産育児一時金50万円とは別に受け取れます

※上限額は年齢と所得で変わります。詳しくは加入している健康保険にご確認ください。

#高額療養費 #帝王切開 #切迫早産 #出産準備 #プレママ #入院費 #医療費 #新米ママ #妊娠中 #知って得する"""


CAPTION_IRYOHIKOJO = """【出産した年は、確定申告でお金が戻ります】

📌 確定申告の時期に見返せるよう保存しておいてください。

医療費控除は、1年間(1〜12月)の医療費が10万円を超えたときに使えます。
出産した年は超えやすいので、該当する家庭が多い制度です。

【対象になるもの】
▶ 妊婦健診・分娩費・入院費
▶ 通院の電車・バス代(記録があれば)

【対象にならないもの】
▶ 里帰りの帰省費用
▶ 自家用車のガソリン代・駐車場代

【たとえば、こんな1年】
▶ 出産費用62万円 − 出産育児一時金50万円 = 12万円
▶ 妊婦健診の自己負担 3万円
▶ 家族の医療費 5万円
合計20万円 → 10万円を超えた分が控除対象
所得税率10%なら、住民税と合わせて約2万円が戻る計算です。

【つまずきやすい2つ】
▶ 年末調整ではできません。会社員でも確定申告が必要です
▶ 出産育児一時金は「その出産にかかった費用」からだけ引きます。医療費の合計から引くと、控除額を少なく計算してしまいます

【あきらめなくて大丈夫】
▶ 5年さかのぼって申告できます
▶ 共働きなら、所得が高い方で申告したほうが戻りが大きくなります

領収書は年初から家族全員分を1つの封筒にまとめておくのがいちばん楽です。

※詳しくは国税庁のページでご確認ください。個別の税務相談には応じられません。

#医療費控除 #確定申告 #出産費用 #プレママ #新米ママ #ワーママ #家計管理 #節約 #出産準備 #知って得する"""


CAPTION_KABE = """【103万の壁、もうありません】

📌 働き方を決める前に保存しておいてください。

2025年(令和7年)の税制改正で、基礎控除が48万円から最大95万円に、
給与所得控除の最低保障が55万円から65万円に引き上げられました。
足すと160万円。ここまで所得税はかかりません。

【いまの壁はこの4つ】
▶ 106万円 … 社会保険に加入(条件つき)
▶ 123万円 … 配偶者控除から配偶者特別控除に変わるだけ
▶ 160万円 … 所得税がかかり、配偶者特別控除も減り始める
▶ 201万5,999円 … 配偶者特別控除が終わる

【本当の崖は社会保険です】
年収105万円なら手取り105万円。
106万円になると手取りは約90.1万円。
1万円増やしただけで約149,000円下がります。
元に戻るのは年収122万円あたりです。

106万円の壁が効くのは、次をすべて満たす場合だけ。
・勤務先の従業員が50人超
・週20時間以上
・月額賃金8.8万円以上
・学生でない
ひとつでも外れると、壁は130万円まで動きます。

【よくある誤解】
123万円を超えても手取りは減りません。
配偶者控除から配偶者特別控除に切り替わるだけで、控除額は満額のまま。
実際に減り始めるのは160万円からです。

【106万の壁は消えていきます】
月額賃金8.8万円という条件は2025年6月から3年以内に撤廃。
勤務先の規模の条件も2027年10月に36人以上、2029年10月に21人以上、
2032年10月に11人以上、2035年10月には10人以下まで下がります。

自分の年収でどうなるかは、プロフィールのリンクからシミュレーターで動かせます。

※出典 国税庁・厚生労働省。手取りは目安です。個別の税務相談には応じられません。

#年収の壁 #103万の壁 #106万の壁 #扶養内 #パート #ワーママ #配偶者控除 #共働き #家計管理 #知って得する"""


CAPTION_IKUKYU = """【育休は「いつ取るか」で手取りが変わります】

📌 育休の時期を決める前に保存しておいてください。

休んでいる間は社会保険料が免除されます。免除されるルートは2つ。

▶ 育休の期間に、その月の末日が入っている
▶ または、開始した月に14日以上取っている

どちらかを満たせば、その月の健康保険料と厚生年金保険料がまるごと免除されます。

【ここが一番効きます】
14日には、土日も祝日も含まれます。
日本年金機構の資料にこう明記されています。
「土日等の休日も期間に含む（就業予定日がある場合は当該就業日を除く）」

つまり年末年始やゴールデンウィークをはさめば、
実際に欠勤する日は少なくても14日に届きます。

たとえば年末年始の休みが6日ある会社なら、前後に8日足すだけで条件クリア。
もともと給与が出ない休日を含めているので、失うものは多くありません。

【ただし賞与は別条件です】
賞与の保険料が免除されるのは、賞与月の末日を含む連続1か月超を取った場合だけ。
2022年10月から厳しくなり、月末に1日だけという方法はもう使えません。
古い情報のまま書いているサイトが今も残っているので注意してください。

【さらに夫婦それぞれ14日以上で】
出生後休業支援給付金（2025年4月〜）により、最大28日間、給付が13%上乗せされます。
社会保険料の免除と同じ14日なので、まとめて満たせます。

※出典 日本年金機構。金額は目安です。会社の就業規則によって欠勤の扱いが異なるため、人事にご確認ください。

#育休 #育児休業 #産休 #パパ育休 #社会保険料 #ワーママ #共働き #新米ママ #プレママ #家計管理"""


CAPTION_FURUSATO = """【出産した年のふるさと納税、控除がゼロになることがあります】

📌 寄付する前に保存しておいてください。

原因はワンストップ特例です。
これは「確定申告をしない人」のための制度なので、
あとから確定申告をすると、提出済みの申請がすべて無効になります。

【出産した年に起きること】
▶ 医療費が10万円を超える（出産した年は超えやすい）
▶ 医療費控除を申告する（これは確定申告が必要）
▶ 提出済みのワンストップがすべて無効になる

【たとえば5万円寄付した場合】
本来の自己負担は2,000円。
でも無効になると、48,000円がそのまま自己負担になります。

【でも防ぐのは簡単です】
確定申告のときに、寄付金控除も一緒に申告するだけ。
それだけで通常どおり控除されます。
寄付金受領証明書は捨てないでおいてください。

【同じことが起きる年】
▶ 住宅ローン控除の1年目（この年も確定申告が必要）
▶ 寄付先が6自治体以上（ワンストップは5自治体まで）

該当しそうなら、最初からワンストップを使わず確定申告でまとめるほうが確実です。

ふるさと納税の上限額の考え方は、プロフィールのリンクから読めます。

※詳しくは総務省・国税庁のページでご確認ください。個別の税務相談には応じられません。

#ふるさと納税 #ワンストップ特例 #医療費控除 #確定申告 #出産準備 #プレママ #新米ママ #ワーママ #家計管理 #知って得する"""


CAPTION_SEIGEN = """【「うちは所得が高いから対象外」その思い込み、もったいないです】

📌 引っ越しや進学の判断材料にもなります。保存推奨。

子どもの医療費助成に所得制限があると思って、
最初から諦めている家庭が少なくありません。

全国1,740市区町村のデータを調べました。

【所得制限がある自治体】
▶ 49市区町村だけ（全体の2.8%）

つまり97%以上の自治体には、所得制限がありません。

【内訳】
▶ 所得制限も自己負担もなし … 1,301市区町村（75%）
▶ 一部負担あり（1回数百円など） … 421市区町村
▶ 所得制限あり … 49市区町村

【対象年齢も広がっています】
▶ 18歳の年度末まで … 1,575市区町村（91%）
いまや9割の自治体が、高校卒業まで無料です。

所得で対象から外れるのは、50に1つの自治体だけ。
諦める前に、お住まいの市区町村を確認してみてください。

プロフィールのリンクから、全1,740市区町村を検索できます。
対象年齢・所得制限の有無・自己負担の有無・県内での順位まで分かります。

※出典：こども家庭庁「こどもに係る医療費の助成についての調査」令和7年4月1日時点

#子ども医療費 #医療費助成 #子育て #所得制限 #新米ママ #プレママ #ワーママ #引っ越し #自治体 #知って得する"""


CAPTION_FUYO = """【子どもが何人いても、扶養控除は増えません】

📌 年末調整の書類を書く前に保存しておいてください。

扶養控除の対象になるのは16歳以上の子どもだけです。
16歳未満は、児童手当が拡充されたときに対象から外れました。

【だからこうなります】
▶ 未就学児・小学生が何人いても、所得税の控除は増えません
▶ ふるさと納税の上限額も、16歳未満の子では下がりません
▶ 16〜18歳の子がいると扶養控除が効くので、上限額は下がります

【よくある損のしかた】
「子どもが3人いるから上限が低いはず」と思い込んで、
ふるさと納税を少なめにしてしまうケースです。
シミュレーターに入力するとき、16歳未満は扶養家族に含めません。

【でも、書かないと損をする欄があります】
扶養控除等申告書の「住民税に関する事項」という欄。
ここには16歳未満の子どもを記載します。
住民税の非課税限度額の判定に使われるためです。

所得税では効かないけれど、住民税では効く。
「対象外だから空欄でいい」が、いちばん多い間違いです。

※出典 国税庁。詳しくは勤務先やお住まいの市区町村にご確認ください。

#年末調整 #扶養控除 #ふるさと納税 #住民税 #子育て #新米ママ #ワーママ #家計管理 #節約 #知って得する"""


CAPTION_HITORIOYA = """【ひとり親が受け取れるお金を整理しました】

📌 手続きのときに見返せるよう保存しておいてください。

【児童扶養手当】
▶ 1人目（全部支給）… 月額 約48,050円
▶ 2人目以降の加算（全部支給）… 月額 約11,350円
子ども2人なら、月およそ59,400円が目安です（所得により変わります）。

【よくある取りこぼし】
「所得制限があるから無理」と決めつけて申請しないケースです。
全部支給に届かなくても、一部支給に該当することがあります。
まず窓口で確認してみてください。

【あわせて申請できるもの】
▶ ひとり親家庭等医療費助成（マル親）… 医療費の自己負担分を助成
▶ 就学援助（小・中学生）… 学用品費・給食費・修学旅行費など

【税金でも35万円ひけます】
ひとり親控除は婚姻歴を問いません。未婚でも対象です。
本人の合計所得500万円以下が条件で、年末調整でも申告できます。
出し忘れても5年さかのぼれます。

【忘れてはいけないこと】
児童扶養手当には毎年の現況届があります。
出し忘れると支給が止まります。

※金額は2026年時点の目安です。所得制限や自己負担は自治体で異なります。

#ひとり親 #シングルマザー #シングルファザー #児童扶養手当 #ひとり親控除 #子育て #給付金 #家計管理 #知って得する #ひとり親家庭"""


CAPTION_KOGAKU2026 = """【入院の上限額、今月から上がりました】

📌 いつ使うか分からない制度なので、保存しておくと安心です。

高額療養費は、1か月の医療費の自己負担が上限を超えたら、超えた分が戻ってくる制度です。
この上限額が【2026年8月の診療分から】引き上げられました。

【どれくらい変わったか】
標準報酬月額28〜50万円(区分ウ)の場合
▶ これまで:80,100円＋(総医療費−267,000円)×1%
▶ 今月から:85,800円＋(総医療費−286,000円)×1%

医療費が100万円かかった月なら
▶ これまでの上限 87,430円
▶ 今月からの上限 92,940円
差は5,510円です。

【上限額は所得で大きく変わります】
医療費100万円の月・70歳未満の場合
▶ 標準報酬月額26万円以下:61,500円
▶ 28〜50万円:92,940円
▶ 53〜79万円:183,130円
▶ 83万円以上:271,290円
▶ 低所得者(住民税非課税など):36,900円
いちばん下といちばん上で4倍以上ちがいます。
自分の区分は給与明細の標準報酬月額か、加入先の健康保険で確認できます。

【増えただけではありません】
今回、あわせて【年間上限】が新しくできました。
8月から翌年7月までの1年間で自己負担の合計が上限に達すると、その年はそれ以降の支払いが不要になります。
区分ウなら年間53万円。毎月の上限には届かないけれど通院が長く続く、というケースを救う仕組みです。
4回目から下がる「多数回該当」の金額は据え置きです。

【知っておくと損しないこと】
▶ マイナ保険証を窓口で出せば、支払いが最初から上限額までで済みます
▶ あとから申請すると、支給まで診療月から3か月以上かかります
▶ 出産でも、帝王切開や切迫早産の入院は保険診療なので対象です

─────────
金額は所得区分で変わります。70歳以上は別の区分です。
出典:協会けんぽ／厚生労働省。申請前に加入先の健康保険でご確認ください。

#高額療養費 #医療費 #入院 #帝王切開 #切迫早産 #マイナ保険証 #お金の勉強 #家計管理 #子育て #制度改正
"""

CAPTION_KOKOFURIKOMI = """【高校無償化のお金、口座には入りません】

📌 高校生の親になる前に、保存しておいてください。

「無償化されたのに振り込まれない」という声をよく見ますが、これは正常です。

【しくみ】
高等学校等就学支援金は、学校が生徒本人に代わって受け取り、授業料と相殺する形になっています。
だから保護者の口座にお金が入ることはありません。そのぶん授業料の請求が減る(または請求が来ない)というだけです。

【落とし穴】
自動では始まりません。申請しないと支給されません。
▶ 入学したら、学校から案内が来ます。必ず提出してください
▶ 年に1回、継続のための手続きがあります。出し忘れると支給が止まります

【対象】
所得制限はありません。2026年度から全世帯が対象です。
(公立の支援は2025年度に暫定措置として所得制限が実質撤廃され、2026年度の改正で本格的に撤廃、私立の加算額も引き上げられました)
私立の上限額や都道府県の上乗せ補助は地域によって違うので、通う学校と自治体で確認してください。

─────────
「振り込まれない＝もらえていない」ではありません。
通帳ではなく、授業料の請求額を見てください📌

出典:文部科学省。詳しい条件は学校・都道府県でご確認ください。

#高校無償化 #就学支援金 #高校生 #教育費 #学費 #子育て #お金の勉強 #家計管理 #中学生ママ #高校受験
"""

CAPTION_JIDOSHIKYUBI = """【児童手当、毎月は振り込まれません】

📌 「今月入ってない」と不安になる前に保存を。

児童手当は毎月ではなく、【年6回・偶数月に2か月分ずつ】まとめて振り込まれます。

【支給の月】
2月・4月・6月・8月・10月・12月
それぞれ、その前の2か月分が入ります。
▶ 2月に 12月分と1月分
▶ 4月に 2月分と3月分
月内の何日に入るかは市区町村によって違います(10日・15日などばらつきます)。

【1回に入る額】
0〜2歳:月15,000円 → 1回30,000円
3歳〜高校生年代:月10,000円 → 1回20,000円
第3子以降:年齢を問わず月30,000円 → 1回60,000円

【2024年10月から変わったこと】
▶ 対象が高校生年代まで広がりました(以前は中学生まで)
▶ 所得制限が撤廃され、年収に関係なく受け取れます
▶ 支払いが年3回から年6回になりました

【ここだけは気をつけて】
出生・転入などの手続きは【翌日から15日以内】が原則です。
遅れると、その分はさかのぼって受け取れません。引っ越しのときが特に危ないです。

─────────
出典:こども家庭庁。支給日や手続きの詳細はお住まいの市区町村でご確認ください。

#児童手当 #支給日 #子育て #育児 #新生児 #ワンオペ育児 #お金の勉強 #家計管理 #子育てママ #プレママ
"""


CAPTION_MATOME = """【放置すると消えるお金 6つ】

📌 どれも期限があります。必要になってから探すと間に合いません。

①【児童手当は出生の翌日から15日以内】
遅れた月の分はさかのぼれません。1日過ぎただけで月1〜3万円が消えます。
里帰り出産で実家にいる場合も、申請先は住所地の市区町村です。ここを勘違いする人が多いところ。

②【ワンストップ特例は確定申告で全部無効になる】
ワンストップは「確定申告をしない人」の制度です。医療費控除を申告した時点で、提出済みのワンストップはすべて無効に。
5万円寄付していたら、自己負担2,000円のはずが48,000円になります。
防ぎ方は簡単で、確定申告のときに寄付金控除も一緒に申告するだけです。寄付金受領証明書は捨てないでください。

③【出産した年の医療費控除は、申告しないと1円も戻らない】
医療費が年10万円を超えたら対象。出産した年は超えやすいです。
会社の年末調整ではできません。確定申告が必要です。
時効は5年なので、過去5年分はいまからでも間に合います。

④【高校無償化は自動では始まらない】
所得制限が撤廃されても、申請しなければ支給されません。
私立なら年45.7万円が自己負担になります。学校からの案内は必ず提出を。
入学時だけでなく、毎年の継続手続きも必要です。

⑤【認可外・預かり保育は「保育の必要性の認定」が要る】
認定を受けていないと、無償化の対象になりません。月3.7万円まで無償になるはずの分が、まるごと自己負担になります。
就労・妊娠出産・疾病・介護・求職活動などが認定の事由です。

⑥【高額療養費は2年で時効】
入院や帝王切開で高額な医療費を払った分は、2年を過ぎると取り戻せません。
そもそもマイナ保険証を窓口で出せば、支払いが最初から上限額までで済みます。立て替えも3か月の待ち時間も不要です。

─────────
①〜⑥はどれも「知っていれば防げた」ものです。
必要になるのは急なタイミングなので、保存しておいてください📌

※金額・条件は所得や自治体によって異なります。出典:こども家庭庁／文部科学省／国税庁／協会けんぽ。申請前に各公式ページとお住まいの市区町村でご確認ください。

#子育て #育児 #出産準備 #プレママ #新生児 #里帰り出産 #児童手当 #医療費控除 #ふるさと納税 #高校無償化 #保育園 #高額療養費 #お金の勉強 #家計管理 #知らないと損
"""



def build_cover(T, em, line1, line2, sub):
    """カバー画像(1080x1920)。動画の1フレーム目ではなく、これを投稿時に指定する。
    絵文字1つ+2行+補足。数字や表は載せない。"""
    img = Image.new("RGB", (W, H), T["bg"])
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 14], fill=T["brand"])
    d.rectangle([0, H - 14, W, H], fill=T["brand"])
    d.rounded_rectangle([72, 556, W - 72, 1341], radius=48, fill=T["soft"])
    paste_center(img, emoji_layer(em, 180), 672)
    paste_center(img, text_layer(line1, font(86), T["ink"]), 880)
    # 2行目は主役。幅からはみ出す長さのときだけ落とす
    size = 104
    while size > 62 and d.textlength(line2, font=font(size)) > W - 220:
        size -= 4
    paste_center(img, text_layer(line2, font(size), T["brand_d"]), 1050)
    paste_center(img, text_layer(sub, font(50), T["sub"]), 1240)
    paste_center(img, text_layer("こそだて給付ナビ", font(52), T["sub"]), 1400)
    return img


# --- 単一テーマ型(ストーリー構成) -----------------------------------------
# 2026-08の実測で、9万ビューを取った1本(iryohi-kojo)と早見表4本(いずれも3,000以下)が
# はっきり分かれた。当たった側だけが持っていたのは
#   ①一覧ではなく単一テーマ ②「すでに払ったお金が戻る」構造
#   ③該当するかを一瞬で判定できる限定 ④カバーは絵文字1つ+2行で数字を載せない
# の4点。当たった構成(7シーン)をそのまま仕様にして、dictを足すだけで増やせる形にする。
# シーン種別は bars(箇条3つ or 2つ) / big(大きな数字) / count(モデルケース+カウントアップ)。
STORY = {}


def _story_dur(spec):
    """シーンの尺を仕様から積む。bars は行数で変える(3行=6.6秒 / 2行=6.0秒)。"""
    t = 3.0
    for s in spec["scenes"]:
        if s["type"] == "bars":
            t += 6.6 if len(s["rows"]) >= 3 else 6.0
        elif s["type"] == "big":
            t += 6.0
        else:
            t += 9.0
    return t + 5.0


def _story_prepare(spec, T):
    """レイヤは1度だけ作る(フレームごとに作ると極端に遅くなる)。"""
    p = {
        "em": emoji_layer(spec["emoji"], 200),
        "hook": text_layer(spec["hook"], font(spec.get("hook_size", 78)), T["ink"]),
        "cta": cta_save(T, *spec["cta"]),
        "scenes": [],
    }
    for s in spec["scenes"]:
        o = {"type": s["type"], "title": text_layer(s["title"], font(56), T["sub"])}
        if s["type"] == "bars":
            o["rows"] = [bar_layer(a, b, T) for a, b in s["rows"]]
        elif s["type"] == "big":
            o["big"] = text_layer(s["big"], font(s.get("big_size", 80)), T["brand_d"])
            o["sub"] = text_layer(s["sub"], font(48), T["sub"])
            o["note"] = text_layer(s["note"], font(52), T["ink"])
        else:
            o["rows"] = [bar_layer(a, b, T) for a, b in s["rows"]]
            o["lead"] = text_layer(s["lead"], font(52), T["sub"])
            o["value"] = s["value"]
            o["unit"] = s.get("unit", "円")
        p["scenes"].append(o)
    return p


def story(name):
    """STORY[name] から frame 関数を作る。返り値は render_* と同じ (frame, dur)。"""
    def build(T):
        spec = STORY[name]
        p = _story_prepare(spec, T)
        cf = font(140)
        # 各シーンの開始時刻を先に決めておく
        marks, t = [], 3.0
        for s in spec["scenes"]:
            d = 6.6 if s["type"] == "bars" and len(s["rows"]) >= 3 else \
                6.0 if s["type"] in ("bars", "big") else 9.0
            marks.append((t, t + d))
            t += d
        cta_at = t
        total = t + 5.0

        def frame(tm):
            img = Image.new("RGB", (W, H), T["bg"])
            d = ImageDraw.Draw(img)
            d.rectangle([0, 0, W, 14], fill=T["brand"])
            d.rectangle([0, H - 14, W, H], fill=T["brand"])
            if tm < 3.0:
                q = ease_out(min(1, tm / 0.35))
                paste_center(img, p["em"], 660, dy=int((1 - q) * 40))
                paste_center(img, p["hook"], 1010, dy=int((1 - q) * 55))
                return img
            if tm >= cta_at:
                draw_cta(img, p["cta"], tm - cta_at)
                return img
            for (st, en), o in zip(marks, p["scenes"]):
                if not (st <= tm < en):
                    continue
                tt = tm - st
                if o["type"] == "bars":
                    three = len(o["rows"]) >= 3
                    paste_center(img, o["title"], 430 if three else 480,
                                 alpha=ease_out(min(1, tt / 0.4)))
                    step = 1.25 if three else 1.3
                    top = 680 if three else 750
                    for i, b in enumerate(o["rows"]):
                        s0 = 0.4 + i * step
                        if tt < s0:
                            break
                        q = ease_out(min(1, (tt - s0) / 0.4))
                        paste_at(img, b, 90, top + i * 210, alpha=q, dx=int((1 - q) * -70))
                elif o["type"] == "big":
                    paste_center(img, o["title"], 560, alpha=ease_out(min(1, tt / 0.4)))
                    if tt > 0.4:
                        pp = min(1, (tt - 0.4) / 0.35)
                        sc = 1.3 - 0.3 * ease_out(pp)
                        z = o["big"].resize((int(o["big"].width * sc), int(o["big"].height * sc)))
                        paste_center(img, z, 790, alpha=pp)
                    if tt > 1.2:
                        paste_center(img, o["sub"], 960, alpha=ease_out(min(1, (tt - 1.2) / 0.4)))
                    if tt > 2.2:
                        paste_center(img, o["note"], 1190, alpha=ease_out(min(1, (tt - 2.2) / 0.5)))
                else:
                    paste_center(img, o["title"], 430, alpha=ease_out(min(1, tt / 0.4)))
                    for i, b in enumerate(o["rows"]):
                        s0 = 0.4 + i * 1.1
                        if tt < s0:
                            break
                        q = ease_out(min(1, (tt - s0) / 0.4))
                        paste_at(img, b, 90, 660 + i * 200, alpha=q, dx=int((1 - q) * -70))
                    if tt > 4.0:
                        paste_center(img, o["lead"], 1250, alpha=ease_out(min(1, (tt - 4.0) / 0.4)))
                        cp = ease_out(min(1, max(0.0, (tt - 4.4) / 2.0)))
                        txt = f"{int(o['value'] * cp):,} {o['unit']}"
                        tw = d.textlength(txt, font=cf)
                        d.text(((W - tw) / 2, 1320), txt, font=cf, fill=T["brand_d"])
            return img

        return frame, total
    return build


STORY["nenkin-ikuji"] = {
    "emoji": "\U0001F4B4",
    "hook": "自営業の親は\n国民年金が免除されます",
    "cta": ("自営業やフリーランスの人に送ってください", "保存 して送る"),
    "scenes": [
        {"type": "bars", "title": "2026年10月に始まります", "rows": [
            ("新しくできる制度", "国民年金保険料の 育児期間の免除"),
            ("始まるのは", "2026年(令和8年)10月から"),
            ("対象になる人", "国民年金の第1号被保険者(自営業・フリーランスなど)"),
        ]},
        {"type": "big", "title": "何か月ぶん免除されるか",
         "big": "お母さん 最大 13 か月", "big_size": 76,
         "sub": "産前産後の4か月＋育児の9か月",
         "note": "お父さんは最大12か月。夫婦とも対象です"},
        {"type": "count", "title": "いくらぶんになるか", "rows": [
            ("令和8年度の保険料", "月 17,920円"),
            ("お母さん 13か月ぶん", "232,960円"),
            ("お父さん 12か月ぶん", "215,040円"),
        ], "lead": "夫婦とも自営業なら", "value": 448000},
        {"type": "bars", "title": "つまずきやすい2つ", "rows": [
            ("会社員と扶養の配偶者は対象外", "第2号・第3号には別の免除があります"),
            ("届出が必要です", "自動では免除されません"),
        ]},
        {"type": "bars", "title": "ここがいちばん大事", "rows": [
            ("免除でも年金は減りません", "納付したものとして老齢基礎年金に反映されます"),
            ("産前産後の免除は今もあります", "出産予定日の6か月前から届け出できます"),
        ]},
    ],
}

STORY["kogaku-2nen"] = {
    "emoji": "⏳",
    "hook": "2年前の入院費\nいまからでも戻ります",
    "cta": ("入院の予定がある人に送ってください", "保存 して送る"),
    "scenes": [
        {"type": "bars", "title": "高額療養費という制度です", "rows": [
            ("同じ月の医療費が上限を超えたら", "超えた分が戻ってきます"),
            ("上限は標準報酬月額で決まります", "28〜50万円なら 85,800円＋α"),
            ("同じ月・同じ世帯なら合算できます", "きょうだいの分もまとめられます"),
        ]},
        {"type": "big", "title": "いつまでさかのぼれるか",
         "big": "2 年", "big_size": 150,
         "sub": "診療を受けた月の翌月1日から2年",
         "note": "その月の分は、いまからでも請求できます"},
        {"type": "count", "title": "たとえば、子どもが入院した月", "rows": [
            ("保険診療の総額", "50万円"),
            ("窓口で払った3割", "150,000円"),
            ("上限額(標準報酬月額28〜50万円)", "87,940円"),
        ], "lead": "あとから戻るのは", "value": 62060},
        {"type": "bars", "title": "つまずきやすい2つ", "rows": [
            ("月をまたぐと合算できません", "同じ月(1日〜末日)の中で数えます"),
            ("差額ベッド代と食事代は対象外", "保険診療の自己負担だけが対象です"),
        ]},
        {"type": "bars", "title": "知っておくと効く2つ", "rows": [
            ("4回目からは下がります", "直近12か月で3回超えたら 44,400円に"),
            ("次からは立て替えなしに", "マイナ保険証か限度額適用認定証で窓口が上限までに"),
        ]},
    ],
}

STORY["shitsugyo-4nen"] = {
    "emoji": "\U0001F570️",
    "hook": "出産で辞めた人の\n失業保険は4年待てます",
    "cta": ("出産で仕事を辞めた人に送ってください", "保存 して送る"),
    "scenes": [
        {"type": "bars", "title": "よくある3つの勘違い", "rows": [
            ("妊娠で辞めたからもらえない", "すぐ働けないだけで、権利は消えていません"),
            ("1年たったら消える", "延長すれば最長4年まで延びます"),
            ("もう遅い", "延長後の期間の最後の日までなら申請できます"),
        ]},
        {"type": "big", "title": "どこまで延ばせるか",
         "big": "4 年", "big_size": 150,
         "sub": "本来は 離職日の翌日から1年",
         "note": "働けない期間を足して 最長4年まで"},
        {"type": "bars", "title": "どういう条件か", "rows": [
            ("妊娠・出産・育児などで", "引き続き30日以上働けないこと"),
            ("延ばせるのは", "本来の1年＋最大3年"),
            ("不妊治療から続いた場合も", "妊娠・出産・育児と連続して延長できます"),
        ]},
        {"type": "bars", "title": "つまずきやすい2つ", "rows": [
            ("延長しても給付日数は増えません", "受け取れる日数そのものは変わりません"),
            ("申請が遅れると減ることが", "所定給付日数の全部を受給できない場合があります"),
        ]},
        {"type": "bars", "title": "やることは2つ", "rows": [
            ("ハローワークに延長を申請", "住んでいる場所を管轄するハローワークです"),
            ("働ける状態になってから受給", "求職の申し込みをして受け取り始めます"),
        ]},
    ],
}

STORY["iryohi-5nen"] = {
    "emoji": "\U0001F9FE",
    "hook": "医療費控除は\n去年の分だけじゃありません",
    "cta": ("去年もその前も出していない人へ", "保存 しておく"),
    "scenes": [
        {"type": "big", "title": "いつまでさかのぼれるか",
         "big": "5 年", "big_size": 150,
         "sub": "その年の翌年1月1日から5年間",
         "note": "5年前の分まで、いまから出せます"},
        {"type": "bars", "title": "見落としやすい3つ", "rows": [
            ("通院の交通費", "電車・バス代。記録があれば対象です"),
            ("子どもの歯列矯正", "発育のために必要と認められる場合"),
            ("市販薬", "治療のために買った分は対象です"),
        ]},
        {"type": "bars", "title": "こちらは対象になりません", "rows": [
            ("自家用車のガソリン代・駐車場代", "通院でも対象外です"),
            ("予防のためのサプリ・健康診断", "病気が見つかって治療した場合を除きます"),
            ("里帰り出産の帰省費用", "通院のための交通費ではありません"),
        ]},
        {"type": "count", "title": "たとえば、3年前のこんな年", "rows": [
            ("子どもの入院と家族の通院で", "年間 300,000円"),
            ("10万円を引いた控除額", "200,000円"),
            ("所得税率10%の人なら", "20,000円"),
        ], "lead": "この年の分だけで戻るのは", "value": 20000},
        {"type": "bars", "title": "つまずきやすい2つ", "rows": [
            ("年末調整ではできません", "会社員でも自分で確定申告が必要です"),
            ("共働きは所得が高いほうで", "税率が高いほど戻る額が大きくなります"),
        ]},
    ],
}


CAPTION_NENKIN_IKUJI = """【2026年10月から、自営業の親は国民年金が免除されます】

来月からの新しい制度です。まだほとんど知られていません。

▶ 対象は 国民年金の第1号被保険者(自営業・フリーランス・学生など)
▶ お母さん 最大13か月(産前産後4か月＋育児9か月)
▶ お父さん 最大12か月(養育を始めた月〜1歳の誕生日の前月)
▶ 夫婦とも対象です

令和8年度の保険料は月17,920円。
お母さん13か月で232,960円、お父さん12か月で215,040円。
夫婦とも自営業なら、合わせて448,000円ぶんになります。

そしていちばん大事なのは、免除でも年金が減らないこと。
免除された期間も「納付したもの」として老齢基礎年金に反映されます。

ただし、届出が必要です。自動では免除されません。
会社員と扶養に入っている配偶者(第2号・第3号)は、この制度ではなく別の免除があります。

産前産後の免除は今もあり、出産予定日の6か月前から届け出できます。
出産後でも届け出できます。

自営業やフリーランスで子育て中の人に、そのまま送ってあげてください📌

※出典:日本年金機構。制度の詳細は開始時期に合わせて更新される場合があります。手続きの前に必ず日本年金機構とお住まいの市区町村でご確認ください。

#国民年金 #自営業 #フリーランス #個人事業主 #保険料免除 #子育て #育児 #出産準備 #プレママ #新米ママ #年金 #家計管理 #お金の勉強 #知らないと損 #2026年10月
"""

CAPTION_KOGAKU_2NEN = """【2年前の入院費、いまからでも戻ります】

高額療養費は、あとからでも申請できます。
時効は「診療を受けた月の翌月1日から2年」。
その月の分なら、今からでも請求できます。

▶ 同じ月の医療費が上限を超えたら、超えた分が戻る
▶ 上限は標準報酬月額で決まる(28〜50万円なら 85,800円＋α)
▶ 同じ月・同じ世帯なら合算できる(きょうだいの分も)

たとえば子どもが入院して、保険診療の総額が50万円だった月。
窓口で払う3割は150,000円。上限額は87,940円。
差額の62,060円が、あとから戻ります。

つまずきやすいのはこの2つ。
・月をまたぐと合算できません(同じ月の1日〜末日で数えます)
・差額ベッド代と食事代は対象外です

そして知っておくと効くのがこの2つ。
・直近12か月で3回超えたら、4回目からは44,400円に下がります
・マイナ保険証か限度額適用認定証があれば、次からは窓口の支払いが最初から上限まで。立て替えが要りません

入院の予定がある人に送っておいてください📌

※金額は2026年8月診療分からの自己負担限度額(70歳未満)です。区分は年収ではなく標準報酬月額で決まります。出典:協会けんぽ。申請前に加入している健康保険でご確認ください。

#高額療養費 #入院 #医療費 #子どもの入院 #帝王切開 #切迫早産 #子育て #育児 #ママ #限度額適用認定証 #マイナ保険証 #家計管理 #お金の勉強 #知らないと損 #保存版
"""

CAPTION_SHITSUGYO_4NEN = """【出産で辞めた人の失業保険は、4年待てます】

「妊娠で辞めたからもらえない」
これがいちばん多い勘違いです。

失業給付は「すぐ働ける人」が対象なので、
妊娠・出産の時期はそのままでは受け取れません。
でも権利が消えたわけではなく、待つことができます。

▶ 本来の受給期間は 離職日の翌日から1年
▶ 妊娠・出産・育児などで引き続き30日以上働けないなら、その分を足せる
▶ 最長で 離職日の翌日から4年(1年＋最大3年)
▶ 不妊治療から続けて、妊娠・出産・育児と連続して延長することもできます

申請は、延長後の受給期間の最後の日までなら可能です。
ただし遅くなるほど、所定給付日数の全部を受け取れない可能性があります。
思い出した時点で動くのが確実です。

延長しても、もらえる日数そのものは増えません。
「受け取れる期間を後ろにずらす」制度です。

やることは2つ。
①住んでいる場所を管轄するハローワークに延長を申請する
②働ける状態になってから、求職の申し込みをして受け取り始める

出産で仕事を辞めた人に、そのまま送ってあげてください📌

※出典:厚生労働省。個別の条件はハローワークの判断になります。手続きの前に住居所を管轄するハローワークでご確認ください。

#失業保険 #失業給付 #雇用保険 #受給期間延長 #ハローワーク #出産退職 #退職 #妊娠 #出産 #子育て #育児 #ママ #家計管理 #お金の勉強 #知らないと損
"""

CAPTION_IRYOHI_5NEN = """【医療費控除は、去年の分だけじゃありません】

還付申告は「その年の翌年1月1日から5年間」。
5年前の分まで、いまから出せます。

見落としやすいのはこの3つ。
▶ 通院の交通費(電車・バス代。記録があれば対象)
▶ 子どもの歯列矯正(発育のために必要と認められる場合)
▶ 市販薬(治療のために買った分)

逆に、これは対象になりません。
・自家用車のガソリン代と駐車場代
・予防のためのサプリと健康診断(病気が見つかって治療した場合を除く)
・里帰り出産の帰省費用

たとえば3年前、子どもの入院と家族の通院で年間30万円かかった年。
10万円を引いた20万円が控除額になり、
所得税率10%の人なら約20,000円が戻ります。
住民税も下がります。

つまずきやすいのはこの2つ。
・年末調整ではできません。会社員でも自分で確定申告が必要です
・共働きなら所得が高いほうで。税率が高いほど戻る額が大きくなります

去年もその前も出していない人は、保存しておいてください📌

※総所得が200万円未満の場合は「10万円」ではなく所得の5%が基準になります。出典:国税庁。申告の前に国税庁のページと所轄の税務署でご確認ください。

#医療費控除 #確定申告 #還付申告 #還付金 #歯列矯正 #子育て #育児 #ママ #節約 #家計管理 #お金の勉強 #知らないと損 #保存版 #税金 #子どもの医療費
"""

REELS = [
    # (名前, テーマ, 描画関数, キャプション, 状態)
    ("018support",      "mint",     render_018,        CAPTION_018,       "投稿済み"),
    ("shinsei-list",    "coral",    render_shinsei,    CAPTION_SHINSEI,   "投稿済み"),
    ("ichisai-kabe",    "lavender", render_ichisai,    CAPTION_ICHISAI,   "投稿済み"),
    ("jido-teate",      "navy",     render_jidoteate,  CAPTION_JIDOTEATE, "投稿済み"),
    ("iryohi-22sai",    "coral",    render_iryohi22,   CAPTION_IRYOHI22,  "投稿済み"),
    ("tokyo23-shussan", "mint",     render_tokyo23,    CAPTION_TOKYO23,   "投稿済み"),
    ("shussan-okane",   "peach",    render_shussan,    CAPTION_SHUSSAN,   "投稿済み"),
    ("kigen-list",      "lavender", render_kigen,      CAPTION_KIGEN,     "投稿済み"),
    ("ikuji-10wari",    "peach",    render_ikuji10,    CAPTION_IKUJI10,   "投稿済み"),
    ("koko-sagaku",     "navy",     render_kokosagaku, CAPTION_KOKO,      "投稿済み"),
    ("kyushoku-2026",   "mint",     render_kyushoku,   CAPTION_KYUSHOKU,  "投稿済み"),
    ("kogaku-ryoyohi",  "coral",    render_kogaku,     CAPTION_KOGAKU,    "投稿済み"),
    ("iryohi-kojo",     "lavender", render_iryohikojo, CAPTION_IRYOHIKOJO, "投稿済み"),
    ("nenshu-kabe",     "navy",     render_kabe,       CAPTION_KABE,      "投稿済み"),
    ("ikukyu-jiki",     "mint",     render_ikukyu,     CAPTION_IKUKYU,    "投稿済み"),
    ("furusato",        "coral",    render_furusato,   CAPTION_FURUSATO,  "未投稿"),
    ("shotoku-seigen",  "navy",     render_shotokuseigen, CAPTION_SEIGEN, "未投稿"),
    ("fuyo-kojo",       "lavender", render_fuyokojo,   CAPTION_FUYO,      "未投稿"),
    ("hitorioya",       "peach",    render_hitorioya,  CAPTION_HITORIOYA, "未投稿"),
    ("kogaku-2026",     "navy",     render_kogaku2026,   CAPTION_KOGAKU2026,   "未投稿"),
    ("koko-furikomi",   "peach",    render_kokofurikomi, CAPTION_KOKOFURIKOMI, "未投稿"),
    ("jido-shikyubi",   "mint",     render_jidoshikyubi, CAPTION_JIDOSHIKYUBI, "未投稿"),
    ("matome-8",        "lavender", render_matome,       CAPTION_MATOME,       "未投稿"),
    ("kabe-hayami",     "coral",    hayami("kabe-hayami"),    CAPTION_KABE2,     "未投稿"),
    ("shussan-hayami",  "coral",    hayami("shussan-hayami"), CAPTION_SHUSSAN_H, "未投稿"),
    ("gakuhi-hayami",   "coral",    hayami("gakuhi-hayami"),  CAPTION_GAKUHI_H,  "未投稿"),
    ("kigen-hayami",    "coral",    hayami("kigen-hayami"),   CAPTION_KIGEN_H,   "未投稿"),
    ("nenkin-ikuji",    "mint",     story("nenkin-ikuji"),   CAPTION_NENKIN_IKUJI,   "未投稿"),
    ("kogaku-2nen",     "coral",    story("kogaku-2nen"),    CAPTION_KOGAKU_2NEN,    "未投稿"),
    ("shitsugyo-4nen",  "lavender", story("shitsugyo-4nen"), CAPTION_SHITSUGYO_4NEN, "未投稿"),
    ("iryohi-5nen",     "navy",     story("iryohi-5nen"),    CAPTION_IRYOHI_5NEN,    "未投稿"),
]


# 冒頭で動きが止まると「画像だ」と判断されてスワイプされる。
# 個々のシーンの秒数を書き換えるとバグを入れやすいので、
# ①全体を一定倍速にする ②常に進むプログレスバーを重ねる の2点を
# ラッパーで一括して効かせる。
SPEED = 1.35        # 15秒台 → 11秒台。リストの送りも同じ比率で速くなる
BAR_H = 22


def polish(frame_fn, dur, T):
    """再生速度を上げ、上端に進行バーを重ねる。返り値は (関数, 新しい尺)。"""
    new_dur = dur / SPEED

    def f(t):
        img = frame_fn(min(t * SPEED, dur - 1e-3))
        # 全編をゆっくり寄る(Ken Burns)。シーンが切り替わらない間も画が動き続けるので
        # 「静止画では?」と思われてスワイプされるのを防ぐ。
        prog = min(1.0, t / new_dur)
        s = 1.0 + 0.045 * prog
        cw, ch = int(W / s), int(H / s)
        img = img.crop(((W - cw) // 2, (H - ch) // 2,
                        (W - cw) // 2 + cw, (H - ch) // 2 + ch)).resize((W, H), Image.BILINEAR)
        # 進行バーはズームの外側に描く(端が切れないように)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, BAR_H], fill=T["tint"])
        d.rectangle([0, 0, int(W * prog), BAR_H], fill=T["brand_d"])
        return img

    return f, new_dur


def slot(i, name):
    """out/instagram/reels/03-ichisai-kabe のような1本ぶんのフォルダ名。"""
    return os.path.join(OUT, f"{i:02d}-{name}")


def write_index():
    """out/instagram/reels/README.md を毎回作り直す。
    Explorerで開いたときに「次に何を投稿するか」が分かるようにするための索引。"""
    lines = ["# リール一覧", "",
             "1本1フォルダ。中身は `video.mp4` / `cover.png` / `caption.txt` の3点セット。",
             "フォルダの連番 = 投稿順。順番を変えたいときは `pipeline/reel.py` の `REELS` を",
             "並べ替えて `python pipeline/reel.py` を実行し直す。", "",
             "| # | フォルダ | 内容 | 状態 |", "|---|---|---|---|"]
    NOTE = {
        "018support": "018サポート 月5,000円",
        "shinsei-list": "申請しないともらえないお金5つ",
        "ichisai-kabe": "待機児童の6割は1歳児",
        "jido-teate": "児童手当は18年で約234万円",
        "iryohi-22sai": "医療費22歳まで無料は6自治体",
        "tokyo23-shussan": "23区の出産でもらえる額の差",
        "shussan-okane": "出産でもらえるお金の合計",
        "kigen-list": "見落としやすい申請期限",
        "ikuji-10wari": "育休の手取りが10割になる条件",
        "koko-sagaku": "高校無償化の都道府県差",
        "kyushoku-2026": "2026年4月からの給食費",
        "kogaku-ryoyohi": "帝王切開・切迫早産と高額療養費",
        "iryohi-kojo": "出産した年の医療費控除",
        "nenshu-kabe": "年収の壁(103万はもうない)",
        "ikukyu-jiki": "育休をいつ取ると得か",
        "furusato": "ふるさと納税の勘違い(子育て世帯)",
        "shotoku-seigen": "医療費助成の所得制限は49自治体だけ",
        "fuyo-kojo": "16歳未満に扶養控除はない",
        "hitorioya": "ひとり親の手当・助成・控除",
        "nenkin-ikuji": "国民年金の育児免除(2026年10月開始)",
        "kogaku-2nen": "高額療養費は2年さかのぼれる",
        "shitsugyo-4nen": "出産退職の失業保険は4年待てる",
        "iryohi-5nen": "医療費控除は5年さかのぼれる",
    }
    for i, (name, _t, _f, _c, status) in enumerate(REELS, 1):
        lines.append(f"| {i:02d} | `{i:02d}-{name}/` | {NOTE.get(name, '')} | {status} |")
    lines += ["", "※カバー画像は投稿時に「カバーを編集 → ギャラリーから追加」で必ず指定する。",
              "動画の1フレーム目を自動採用させると意図しない絵になる。", ""]
    with open(os.path.join(OUT, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    import sys
    only = sys.argv[1:]  # 引数で名前を指定すると、その分だけ作り直せる
    for i, (name, theme, fn, cap, _status) in enumerate(REELS, 1):
        if only and name not in only:
            continue
        d = slot(i, name)
        frame_fn, dur = polish(*fn(THEMES[theme]), T=THEMES[theme])
        out, n = encode(frame_fn, dur, d, cap)
        size = os.path.getsize(out) / 1024
        if name in COVER_CUSTOM:
            COVER_CUSTOM[name](THEMES[theme]).save(os.path.join(d, "cover.png"))
        elif name in COVERS:
            build_cover(THEMES[theme], *COVERS[name]).save(os.path.join(d, "cover.png"))
        print(f"  {i:02d}-{name}/ [{theme}]: {dur:.1f}秒 / {n}フレーム / {size:.0f}KB (+cover)")
    write_index()
    print(f"\n→ {OUT}")


if __name__ == "__main__":
    main()
