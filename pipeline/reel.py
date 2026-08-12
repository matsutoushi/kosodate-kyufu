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
    d.text((48, 26), text, font=font(56), fill=T["ink"])
    d.text((48, 92), note, font=font(36), fill=T["sub"])
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


def cta_save(T, line1, line2):
    """終盤の共通CTA。実測でプロフィール遷移が0だったため、
    2段階の「プロフィール→リンク」ではなく1タップで済む『保存』を主役にする。"""
    return {
        "em": emoji_layer("🔖", 150),
        "l1": text_layer(line1, font(56), T["sub"]),
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


# --- カバー画像 -------------------------------------------------------------
# リールは全要素がフェードインするので1フレーム目がほぼ空白。Instagramに自動選択
# させるとプロフィールが白紙で並ぶため、カバーは必ず別途アップロードする。
#
# ⚠️切り抜きの制約: リールのカバーはプロフィールのグリッドで中央から切られる。
#   3:4で切ると y240〜1680、1:1で切ると y420〜1500 しか残らない。
#   → 文字はすべて **y500〜1400** に収める(どちらで切られても読める)。
COVER_SAFE = (500, 1400)


def build_cover(T, emoji, line1, line2, tag):
    img = Image.new("RGB", (W, H), T["bg"])
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 14], fill=T["brand"])
    d.rectangle([0, H - 14, W, H], fill=T["brand"])
    # 安全領域の中で組む(中央 y=950 を基準に上下へ展開)
    d.rounded_rectangle([70, 560, W - 70, 1340], radius=60, fill=T["soft"])
    paste_center(img, emoji_layer(emoji, 190), 700)
    paste_center(img, text_layer(line1, font(84), T["ink"]), 900)
    paste_center(img, text_layer(line2, font(96), T["brand_d"]), 1080)
    # タグと屋号(切られても本体が成立するよう、装飾の位置づけにする)
    paste_center(img, text_layer(tag, font(44), T["sub"]), 1250)
    paste_center(img, text_layer("こそだて給付ナビ", font(46), T["sub"]), 1430)
    return img


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
    ("kogaku-ryoyohi",  "coral",    render_kogaku,     CAPTION_KOGAKU,    "未投稿"),
    ("iryohi-kojo",     "lavender", render_iryohikojo, CAPTION_IRYOHIKOJO, "未投稿"),
    ("nenshu-kabe",     "navy",     render_kabe,       CAPTION_KABE,      "未投稿"),
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
        if name in COVERS:
            build_cover(THEMES[theme], *COVERS[name]).save(os.path.join(d, "cover.png"))
        print(f"  {i:02d}-{name}/ [{theme}]: {dur:.1f}秒 / {n}フレーム / {size:.0f}KB (+cover)")
    write_index()
    print(f"\n→ {OUT}")


if __name__ == "__main__":
    main()
