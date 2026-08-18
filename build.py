"""
静的サイトビルダー: data/programs.json → site/*.html
「子育て世帯がもらえるお金」ガイド(作業名)。モバイルファースト・信頼重視のクリーンなデザイン。
標準ライブラリのみ。python build.py で site/ に出力。
"""
import html
import datetime
import hashlib
import json
import urllib.parse
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data", "programs.json")
ENRICH = os.path.join(ROOT, "data", "enrich.json")
IRYOHI = os.path.join(ROOT, "data", "iryohi_municipalities.json")
TAIKI = os.path.join(ROOT, "data", "taiki_municipalities.json")
IRYOHI_PREF = os.path.join(ROOT, "data", "iryohi_prefectures.json")
SITE = os.path.join(ROOT, "site")

SITE_NAME = "こそだて給付ナビ"
TAGLINE = "子育て世帯が“もらえるお金”を、ムダなく受け取るための地図"
DOMAIN = "kosodate-kyufu.com"
BASE_URL = f"https://{DOMAIN}"
GA4_ID = "G-ZW9ZH2FCPS"  # GA4測定ID。ここ1箇所で全ページに反映される
GSC_TOKEN = "q0qAeAIxlo6jsG2oXXGQfxLfMg-FL-Gf--5B3YYFuDQ"  # Search Console 所有権確認
VC_LINKSWITCH_PID = "892667160"  # バリューコマース LinkSwitch(通常リンクを自動でアフィリエイト化)
VC_SID = "3776805"
# お問い合わせフォーム(Googleフォーム)。メールアドレスを公開せずに連絡手段を用意するため。
CONTACT_FORM = "https://docs.google.com/forms/d/e/1FAIpQLSdzkTiL7dqWmIKnurJG4bOQoQVJV8vbX6ttMS0GXp1yR0VrAA/viewform"
OPERATOR_NAME = "こそだて給付ナビ 編集部"

def related_card(prog_id=None, hikaku_pages=()):
    """制度ページ下部の導線。制度ごとに広告を紐づけると不自然になるため、
    「家計を軽くする」まとめページ1本に集約する。"""
    if not hikaku_pages:
        return ""
    return """<div class="sec-title">もらうだけでなく、減らす</div>
<a class="card" href="./kakei.html">
  <div class="t">🏠 家計を軽くする、5つの見直し</div>
  <div class="s">固定費は一度下げれば、効果がずっと続きます</div>
  <div class="d">ふるさと納税・通信費・電気ガス・教育費などをまとめました →</div>
</a>"""


GSEARCH = "https://www.google.com/search?q="

NAV = [
    ("./index.html", "ホーム"),
    ("./shindan.html", "もらえる診断"),
    ("./ichiran.html", "金額の早見表"),
    ("./chiiki.html", "地域で調べる"),
    ("./kabe.html", "年収の壁"),
    ("./kakei.html", "家計の見直し"),
]


def site_nav(current=""):
    """全ページ共通のナビ。下までスクロールしないと移動できない状態を解消する。"""
    items = "".join(
        f'<a href="{u}" class="{"on" if u.endswith(current) and current else ""}">{html.escape(t)}</a>'
        for u, t in NAV)
    return f'<nav class="gnav"><div class="wrap">{items}</div></nav>'


# ---- 共通パーツ -------------------------------------------------------------

def head(title, desc, path="/"):
    ga = ""
    if GA4_ID:
        ga = (f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA4_ID}"></script>'
              f"<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}"
              f"gtag('js',new Date());gtag('config','{GA4_ID}');</script>")
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="canonical" href="{BASE_URL}{path}">
<meta property="og:site_name" content="{html.escape(SITE_NAME)}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:url" content="{BASE_URL}{path}">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
{f'<meta name="google-site-verification" content="{GSC_TOKEN}">' if GSC_TOKEN else ''}
{ga}
<style>{CSS}</style>
</head>
<body>
"""

CSS = """
:root{
  --bg:#fffdf9; --card:#ffffff; --ink:#2b2b33; --sub:#6b6b76;
  --brand:#ff8a65; --brand-d:#f4643b; --accent:#4db6ac; --line:#efe7dd;
  --shadow:0 2px 12px rgba(120,90,60,.08); --radius:16px;
}
*{box-sizing:border-box}
body{margin:0;font-family:"Hiragino Kaku Gothic ProN","Noto Sans JP",system-ui,sans-serif;
  background:var(--bg);color:var(--ink);line-height:1.7;-webkit-text-size-adjust:100%}
a{color:var(--brand-d);text-decoration:none}
.wrap{max-width:720px;margin:0 auto;padding:0 16px}
header.site{background:linear-gradient(135deg,#ffd9c9,#ffe9dc);padding:22px 0 18px;text-align:center}
header.site .logo{font-size:1.4rem;font-weight:800;color:var(--brand-d);letter-spacing:.02em}
header.site .tag{font-size:.82rem;color:#8a5a44;margin-top:4px}
.hero{padding:26px 0 8px;text-align:center}
.hero h1{font-size:1.5rem;margin:.2em 0;letter-spacing:.01em}
.hero p{color:var(--sub);font-size:.92rem;margin:.4em 0 0}
.cta{display:inline-block;background:var(--brand);color:#fff;font-weight:700;
  padding:14px 26px;border-radius:999px;margin:18px 0 6px;box-shadow:var(--shadow);font-size:1rem}
.cta:active{transform:translateY(1px)}
.sec-title{font-size:1.05rem;font-weight:800;margin:28px 0 12px;padding-left:10px;border-left:5px solid var(--brand)}
.cats{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}
.cat{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
  padding:14px 12px;text-align:center;box-shadow:var(--shadow)}
.cat .emoji{font-size:1.6rem}.cat .lb{font-weight:700;font-size:.9rem;margin-top:4px}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
  padding:16px;margin:12px 0;box-shadow:var(--shadow);display:block}
.card .t{font-weight:800;font-size:1.05rem}
.card .s{color:var(--brand-d);font-weight:700;font-size:.86rem;margin:4px 0 6px}
.card .d{color:var(--sub);font-size:.88rem}
.badge{display:inline-block;background:#f6efe6;font-size:.72rem;color:#8a7a68;
  border-radius:999px;padding:2px 10px;margin-right:6px}
.prog dl{margin:0}
.prog dt{font-weight:800;font-size:.82rem;color:var(--accent);margin-top:14px;letter-spacing:.02em}
.prog dd{margin:3px 0 0;font-size:.95rem}
.amount{background:#fff5ef;border:1px dashed var(--brand);border-radius:12px;padding:12px 14px;margin:12px 0;font-weight:700}
.note{background:#f4faf9;border-left:4px solid var(--accent);padding:10px 12px;border-radius:8px;font-size:.86rem;color:#4a6a66;margin-top:14px}
.offbtn{display:inline-block;margin-top:16px;border:2px solid var(--brand);color:var(--brand-d);
  font-weight:700;padding:10px 18px;border-radius:999px;font-size:.9rem}
.back{display:inline-block;margin:16px 0;color:var(--sub);font-size:.86rem}
.pr{font-size:.72rem;color:#a99;text-align:center;margin:6px 0}
.disc{font-size:.76rem;color:#9a8f83;background:#faf5ee;border-radius:12px;padding:12px 14px;margin:22px 0}
footer{text-align:center;color:var(--sub);font-size:.78rem;padding:26px 0 40px}
footer a{color:var(--sub)}
/* 診断 */
.q{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:14px 16px;margin:10px 0;box-shadow:var(--shadow)}
.q label{display:flex;align-items:center;gap:10px;font-size:.95rem;cursor:pointer}
.q input{width:20px;height:20px;accent-color:var(--brand)}
#result{margin-top:16px}
/* 読み物パート */
.body p{margin:.9em 0}
.why{background:#fff8f4;border-radius:12px;padding:14px 16px;font-size:.92rem;color:#6b5348}
.case{background:#f2faf8;border:1px solid #d6ece7;border-radius:12px;padding:14px 16px;margin:14px 0}
.case .h{font-weight:800;color:#2f7f74;font-size:.86rem;margin-bottom:4px}
ul.tips,ul.mis{padding-left:0;list-style:none;margin:8px 0}
ul.tips li,ul.mis li{position:relative;padding:8px 0 8px 30px;border-bottom:1px dashed var(--line);font-size:.93rem}
ul.tips li:before{content:"✅";position:absolute;left:2px}
ul.mis li:before{content:"⚠️";position:absolute;left:2px}
.faq dt{font-weight:800;font-size:.95rem;color:var(--ink);margin-top:14px}
.faq dt:before{content:"Q. ";color:var(--brand-d)}
.faq dd{margin:4px 0 0;font-size:.92rem;color:#55525c}
.faq dd:before{content:"A. ";font-weight:800;color:var(--accent)}
/* 地域検索 */
.search{width:100%;padding:14px 16px;font-size:1rem;border:2px solid var(--line);border-radius:12px;margin:10px 0}
.search:focus{outline:none;border-color:var(--brand)}
.mrow{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin:8px 0;box-shadow:var(--shadow)}
.mrow .n{font-weight:800}
.mrow .meta{font-size:.85rem;color:var(--sub);margin-top:4px}
.pill{display:inline-block;font-size:.74rem;border-radius:999px;padding:2px 9px;margin-right:5px}
.p-good{background:#e6f5f1;color:#2f7f74}.p-warn{background:#fdeee6;color:#b4623c}
table.rank{width:100%;border-collapse:collapse;font-size:.88rem;margin:10px 0}
table.rank th,table.rank td{border-bottom:1px solid var(--line);padding:8px 6px;text-align:left}
table.rank th{color:var(--sub);font-size:.8rem}
.stat{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}
.stat div{flex:1;min-width:100px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px;text-align:center;box-shadow:var(--shadow)}
.stat .v{font-size:1.3rem;font-weight:800;color:var(--brand-d)}
.stat .l{font-size:.74rem;color:var(--sub)}
/* グローバルナビ(横スクロール可・スマホ前提) */
.gnav{background:#fff;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:20}
.gnav .wrap{display:flex;gap:4px;overflow-x:auto;-webkit-overflow-scrolling:touch;padding:0 12px}
.gnav a{flex:0 0 auto;padding:12px 14px;font-size:.88rem;font-weight:700;color:var(--sub);
  white-space:nowrap;border-bottom:3px solid transparent}
.gnav a.on{color:var(--brand-d);border-bottom-color:var(--brand)}
.gnav::-webkit-scrollbar{display:none}
/* 地域の検索結果の補足 */
.localnote{background:#fff8f4;border-radius:12px;padding:14px 16px;margin:14px 0;font-size:.9rem}
.dsec{border-top:1px solid var(--line);margin-top:10px;padding-top:10px}
.dsec:first-of-type{border-top:0;margin-top:6px;padding-top:0}
.dh{font-weight:800;font-size:.86rem;color:var(--accent);margin-bottom:2px}
.mrow{padding:14px 16px}
.localnote a{font-weight:700}
"""

def footer():
    return f"""
<div class="wrap">
  <div class="disc">{html.escape(DISCLAIMER)}<br>
  ※本サイトは制度紹介のための情報提供であり、申請の可否・金額を保証するものではありません。最新・正確な情報は各公式ページと市区町村でご確認ください。</div>
</div>
<footer><div class="wrap">
  {html.escape(SITE_NAME)} ／ <a href="./index.html">ホーム</a> ・ <a href="./shindan.html">もらえるお金しんだん</a> ・ <a href="./chiiki.html">地域別で調べる</a><br>
  <a href="./policy.html">プライバシーポリシー・免責事項</a> ・ <a href="{html.escape(CONTACT_FORM)}" target="_blank" rel="noopener">お問い合わせ</a><br>
  出典は各制度ページの公式リンクをご確認ください。
</div></footer>
</body></html>"""

DISCLAIMER = ""

# ---- ページ生成 -------------------------------------------------------------

def build_index(data):
    cats = data["categories"]
    progs = data["programs"]
    parts = [head(f"{SITE_NAME}｜{TAGLINE}",
                  "子育て世帯がもらえるお金・返ってくるお金を、妊娠・出産・育児・ひとり親・教育の場面ごとにやさしく解説。", "/")]
    parts.append(f"""
<header class="site"><div class="wrap">
  <div class="logo">{html.escape(SITE_NAME)}</div>
  <div class="tag">{html.escape(TAGLINE)}</div>
</div></header>
{site_nav("index.html")}
<div class="wrap">
  <div class="hero">
    <h1>知らないと損する、<br>子育ての「もらえるお金」</h1>
    <p>制度はたくさんあるのに、案内は来ません。<br>あなたが受け取れるお金を、いっしょに確認しましょう。</p>
    <a class="cta" href="./shindan.html">▶ もらえるお金を30秒でしんだん</a>
  </div>

  <a class="card" href="./kabe.html" style="background:linear-gradient(135deg,#f7f9fc,#fff6f0)">
    <div class="t">🧱 「103万の壁」は、もうありません</div>
    <div class="s">いくらまで働くと得か、スライダーで試算できます</div>
    <div class="d">2025年の改正で壁が動きました。106万・123万・160万のどれに当たるかを確認 →</div>
  </a>

  <a class="card" href="./chiiki.html" style="background:linear-gradient(135deg,#fff6f0,#f2faf8)">
    <div class="t">📍 あなたの街は何歳まで医療費が無料?</div>
    <div class="s">全国1,740市区町村を検索できます</div>
    <div class="d">子ども医療費助成は自治体の制度。住む場所で驚くほど違います →</div>
  </a>

  <div class="sec-title">制度をさがす</div>
  <input class="search" id="pq" type="search" placeholder="例: 児童手当／医療費／高校／ひとり親" autocomplete="off">
  <p style="font-size:.82rem;color:var(--sub);margin:4px 0 0">キーワードで下の制度一覧をしぼり込めます。
  金額だけざっと見たい方は <a href="./ichiran.html"><strong>金額の早見表</strong></a> へ。</p>

  <div class="sec-title">場面から探す</div>
  <div class="cats">""")
    for c in cats:
        parts.append(f'<a class="cat" href="#{c["id"]}"><div class="emoji">{c["emoji"]}</div><div class="lb">{html.escape(c["label"])}</div></a>')
    parts.append("</div>")

    for c in cats:
        cprogs = [p for p in progs if p["category"] == c["id"]]
        if not cprogs:
            continue
        parts.append(f'<div class="sec-title pgroup" id="{c["id"]}">{c["emoji"]} {html.escape(c["label"])}</div>')
        for p in cprogs:
            hay = html.escape((p["title"] + p["subtitle"] + p["summary"] + p.get("target", "")).lower())
            parts.append(f"""<a class="card pcard" data-hay="{hay}" href="./{p['id']}.html">
  <div class="t">{html.escape(p['title'])}</div>
  <div class="s">{html.escape(p['subtitle'])}</div>
  <div class="d">{html.escape(p['summary'][:70])}…</div>
</a>""")
    hk = data.get("_hikaku") or []
    if hk:
        parts.append('<div class="sec-title">もらうだけじゃない、減らす工夫も</div>')
        for p in hk:
            parts.append(f"""<a class="card" href="./{p['id']}.html">
  <div class="t">{p.get('emoji','')} {html.escape(p.get('nav_title', p['title']))}</div>
  <div class="d">{html.escape(p['lead'][:64])}… →</div>
</a>""")
    # 解説記事。トップから記事への導線が無いと、記事が孤立してクロールされにくい。
    arts = data.get("_articles") or []
    if arts:
        parts.append('<div class="sec-title">くわしく読む</div>')
        for a in arts:
            parts.append(f"""<a class="card" href="./{a['id']}.html">
  <div class="t">{a.get('emoji','')} {html.escape(a['title'])}</div>
  <div class="d">{html.escape(a['desc'][:76])}… →</div>
</a>""")
    parts.append("</div>")
    parts.append("""<script>
const pq = document.getElementById('pq');
const cards = [...document.querySelectorAll('.pcard')];
const groups = [...document.querySelectorAll('.pgroup')];
pq && pq.addEventListener('input', () => {
  const v = pq.value.trim().toLowerCase();
  cards.forEach(c => { c.style.display = (!v || c.dataset.hay.includes(v)) ? '' : 'none'; });
  groups.forEach(g => {
    let el = g.nextElementSibling, any = false;
    while (el && !el.classList.contains('pgroup') && !el.classList.contains('sec-title')) {
      if (el.classList.contains('pcard') && el.style.display !== 'none') any = true;
      el = el.nextElementSibling;
    }
    g.style.display = (!v || any) ? '' : 'none';
  });
});
</script>""")
    parts.append(footer())
    return "".join(parts)


def build_program(p, data):
    parts = [head(f"{p['title']}｜{SITE_NAME}", p["summary"][:100], f"/{p['id']}.html")]
    parts.append(f"""
<header class="site"><div class="wrap"><a class="logo" href="./index.html">{html.escape(SITE_NAME)}</a></div></header>
{site_nav()}
<div class="wrap prog">
  <a class="back" href="./index.html">← 一覧にもどる</a>
  <h1 style="font-size:1.35rem;margin:.2em 0">{html.escape(p['title'])}</h1>
  <div class="s" style="color:var(--brand-d);font-weight:700">{html.escape(p['subtitle'])}</div>
  <div class="amount">💰 {html.escape(p['amount'])}</div>
  <p>{html.escape(p['summary'])}</p>
  <dl>
    <dt>対象になる人</dt><dd>{html.escape(p['target'])}</dd>
    <dt>申請先・方法</dt><dd>{html.escape(p['how'])}</dd>
    <dt>申請の期限</dt><dd>{html.escape(p['deadline'])}</dd>
  </dl>""")
    e = p.get("_enrich") or {}
    if e.get("why"):
        parts.append(f'<div class="sec-title">なぜこの制度があるの?</div><div class="why">{html.escape(e["why"])}</div>')
    if e.get("detail"):
        parts.append('<div class="sec-title">くわしく知る</div><div class="body">')
        for para in e["detail"]:
            parts.append(f"<p>{html.escape(para)}</p>")
        parts.append("</div>")
    if e.get("case"):
        parts.append(f'<div class="case"><div class="h">💡 モデルケース</div>{html.escape(e["case"])}</div>')
    if e.get("prefectures"):
        pf = e["prefectures"]
        parts.append(f'<div class="sec-title">{html.escape(pf["title"])}</div>')
        parts.append(f'<p>{html.escape(pf["lead"])}</p>')
        for r in pf["rows"]:
            parts.append(f"""<div class="card" style="cursor:default">
  <div class="t">{html.escape(r['name'])}</div>
  <div class="s">{html.escape(r['headline'])}</div>
  <div class="d">{html.escape(r['detail'])}</div>
  <a class="offbtn" href="{html.escape(r['url'])}" target="_blank" rel="noopener">公式ページで確認する</a>
</div>""")
        if pf.get("note"):
            parts.append(f'<div class="note">📌 {html.escape(pf["note"])}</div>')
    if p.get("id") == "kodomo-iryohi":
        parts.append('<a class="cta" href="./chiiki.html" style="display:block;text-align:center">📍 お住まいの市区町村の助成を調べる</a>')
    if e.get("tips"):
        parts.append('<div class="sec-title">申請のコツ</div><ul class="tips">')
        for t in e["tips"]:
            parts.append(f"<li>{html.escape(t)}</li>")
        parts.append("</ul>")
    if e.get("mistakes"):
        parts.append('<div class="sec-title">よくある“もったいない”</div><ul class="mis">')
        for t in e["mistakes"]:
            parts.append(f"<li>{html.escape(t)}</li>")
        parts.append("</ul>")
    if e.get("faq"):
        parts.append('<div class="sec-title">よくある質問</div><dl class="faq">')
        for qa in e["faq"]:
            parts.append(f'<dt>{html.escape(qa["q"])}</dt><dd>{html.escape(qa["a"])}</dd>')
        parts.append("</dl>")
    if p.get("note"):
        parts.append(f'<div class="note">📌 {html.escape(p["note"])}</div>')
    if p.get("official_url"):
        parts.append(f'<a class="offbtn" href="{html.escape(p["official_url"])}" target="_blank" rel="noopener">🔗 {html.escape(p["official_name"])}の公式ページで確認</a>')
    else:
        parts.append(f'<div class="note">🔗 {html.escape(p["official_name"])}</div>')
    parts.append(f'<p style="font-size:.74rem;color:#a99;margin-top:16px">最終更新: {html.escape(p.get("updated",""))}／出典: {html.escape(p["official_name"])}</p>')
    # 同じカテゴリの制度へ回遊(読んで終わりの行き止まりを防ぐ)
    same = [x for x in data["programs"] if x["category"] == p["category"] and x["id"] != p["id"]][:3]
    if same:
        cat = next((c for c in data["categories"] if c["id"] == p["category"]), None)
        label = f'{cat["emoji"]} {cat["label"]}' if cat else "同じ場面"
        parts.append(f'<div class="sec-title">{html.escape(label)}の他の制度</div>')
        for x in same:
            parts.append(f"""<a class="card" href="./{x['id']}.html">
  <div class="t">{html.escape(x['title'])}</div>
  <div class="s">{html.escape(x['subtitle'])}</div>
</a>""")
    # 制度に対応する解説記事があれば、その制度ページから導線を張る
    # (新しい記事を作るたびにリンク元を用意しないと孤立ページになる)
    ART_FOR = {"ikuji-kyugyo-kyufu": "ikukyu-jiki",
               "iryohi-kojo": "furusato-onestop",
               "jido-fuyo-teate": "hitorioya-kojo",
               "hitorioya-iryohi": "hitorioya-kojo"}
    _aid = ART_FOR.get(p["id"])
    if _aid:
        _a = {x["id"]: x for x in (data.get("_articles") or [])}.get(_aid)
        if _a:
            parts.append('<div class="sec-title">あわせて読みたい</div>'
                         f'<a class="card" href="./{_a["id"]}.html">'
                         f'<div class="t">{_a.get("emoji","")} {html.escape(_a["title"])}</div>'
                         f'<div class="d">{html.escape(_a["desc"][:80])}… →</div></a>')
    parts.append(related_card(p["id"], data.get("_hikaku") or []))
    parts.append("</div>")
    parts.append(footer())
    return "".join(parts)


def build_shindan(data):
    progs = data["programs"]
    hikaku_pages = data.get("_hikaku") or []
    # 簡易チェック: 状況にチェック → 該当しうる制度を表示(クライアントサイド)
    checks = [
        ("pregnant", "いま妊娠中／妊娠を予定している", ["ninpu-shien-kyufu", "ninpu-kenshin", "shussan-ichijikin", "shussan-teate", "iryohi-kojo"]),
        ("funin", "不妊治療を受けている／検討している", ["funin-chiryo"]),
        ("postnatal", "出産して1年以内(産後の体調や育児が不安)", ["sango-care"]),
        ("company", "会社員・公務員で産休・育休を取る(取った)", ["shussan-teate", "ikuji-kyugyo-kyufu"]),
        ("baby", "0〜2歳／未就学の子どもがいる", ["jido-teate", "kodomo-iryohi", "hoiku-mushouka"]),
        ("shougaku", "小・中学生の子どもがいる", ["jido-teate", "kyushoku", "shugaku-enjo", "kodomo-iryohi"]),
        ("koukou", "高校生年代の子どもがいる", ["jido-teate", "koko-shushi-kin", "koko-shogaku-kyufu"]),
        ("daigaku", "大学・専門学校への進学を控えている(在学中)", ["kyufu-shogakukin"]),
        ("tashi", "扶養している子どもが3人以上いる", ["jido-teate", "tashi-mushouka"]),
        ("single", "ひとり親家庭である", ["jido-fuyo-teate", "hitorioya-iryohi", "kodomo-iryohi"]),
        ("shogai", "障害のある子どもを育てている", ["tokubetsu-jido-fuyo", "shogaiji-fukushi"]),
        ("iryohi", "今年は医療費が多い(帝王切開・入院・通院が続いた)", ["kogaku-ryoyohi", "iryohi-kojo"]),
    ]
    title_map = {p["id"]: [p["title"], p["subtitle"]] for p in progs}
    import json as _j
    parts = [head(f"もらえるお金しんだん｜{SITE_NAME}", "かんたんな質問で、あなたが受け取れる可能性のある子育て支援制度がわかります。", "/shindan.html")]
    parts.append(f"""
<header class="site"><div class="wrap"><a class="logo" href="./index.html">{html.escape(SITE_NAME)}</a></div></header>
{site_nav()}
<div class="wrap">
  <a class="back" href="./index.html">← ホーム</a>
  <h1 style="font-size:1.3rem">もらえるお金しんだん</h1>
  <p style="color:var(--sub);font-size:.9rem">あてはまるものにチェックしてください。該当しうる制度を表示します(参考情報です)。</p>
  <div id="qs">""")
    for cid, label, _ in checks:
        parts.append(f'<div class="q"><label><input type="checkbox" data-k="{cid}"> {html.escape(label)}</label></div>')
    parts.append("""</div>
  <div id="result"></div>

  <div class="sec-title">もらうだけでなく、減らす</div>
  <p style="color:var(--sub);font-size:.92rem">受け取れる制度を確認したら、出ていくお金も見直してみてください。
  固定費は一度下げれば、その効果がずっと続きます。</p>
  """ + hikaku_cards(hikaku_pages) + """
</div>""")
    parts.append(f"""<script>
const MAP = {_j.dumps({c[0]: c[2] for c in checks}, ensure_ascii=False)};
const TITLES = {_j.dumps(title_map, ensure_ascii=False)};
const boxes = document.querySelectorAll('input[data-k]');
function render(){{
  const hit = new Set();
  boxes.forEach(b=>{{ if(b.checked) (MAP[b.dataset.k]||[]).forEach(id=>hit.add(id)); }});
  const r = document.getElementById('result');
  if(hit.size===0){{ r.innerHTML=''; return; }}
  let h = '<div class="sec-title">受け取れる可能性のある制度</div>';
  hit.forEach(id=>{{ const t = TITLES[id]; h += '<a class="card" href="./'+id+'.html"><div class="t">'+t[0]+'</div><div class="s">'+t[1]+'</div><div class="d">タップで詳細と申請方法へ →</div></a>'; }});
  h += '<div class="note">※チェック内容から機械的に表示しています。実際の対象可否・金額は各公式ページと市区町村でご確認ください。</div>';
  r.innerHTML = h;
}}
boxes.forEach(b=>b.addEventListener('change',render));
</script>""")
    parts.append(footer())
    return "".join(parts)


def build_ichiran(data):
    """金額の早見表。全制度を1画面でざっと見比べられる。SNSからの「まとめて見たい」需要に応える。"""
    cats = data["categories"]
    progs = data["programs"]
    parts = [head(f"子育てでもらえるお金 金額の早見表｜{SITE_NAME}",
                  "児童手当・出産育児一時金・高校無償化など、子育て世帯がもらえるお金の金額を一覧表にまとめました。",
                  "/ichiran.html")]
    parts.append(f"""
<header class="site"><div class="wrap"><a class="logo" href="./index.html">{html.escape(SITE_NAME)}</a></div></header>
{site_nav("ichiran.html")}
<div class="wrap">
  <a class="back" href="./index.html">← ホーム</a>
  <h1 style="font-size:1.35rem;margin:.2em 0">金額の早見表</h1>
  <p style="color:var(--sub);font-size:.92rem">全{len(progs)}制度の「いくらもらえるか」を一覧にしました。
  制度名をタップすると、対象者や申請方法のくわしい解説に飛べます。</p>""")
    for c in cats:
        cprogs = [p for p in progs if p["category"] == c["id"]]
        if not cprogs:
            continue
        parts.append(f'<div class="sec-title">{c["emoji"]} {html.escape(c["label"])}</div>')
        parts.append('<div style="overflow-x:auto"><table class="rank"><tr><th style="min-width:9em">制度</th><th>金額・内容</th></tr>')
        for p in cprogs:
            parts.append(
                f'<tr><td><a href="./{p["id"]}.html"><strong>{html.escape(p["title"])}</strong></a>'
                f'<div style="font-size:.76rem;color:var(--sub)">{html.escape(p["subtitle"])}</div></td>'
                f'<td style="font-size:.88rem">{html.escape(p["amount"])}</td></tr>')
        parts.append("</table></div>")
    parts.append("""
  <div class="note">📌 金額・条件は改正や自治体によって変わります。この表は概要をつかむためのもので、
  申請前に必ず各制度ページの公式リンクからご確認ください。</div>
  <a class="cta" href="./shindan.html" style="display:block;text-align:center">▶ 自分がもらえる制度を30秒でしんだん</a>
</div>""")
    parts.append(footer())
    return "".join(parts)


def taiki_section(taiki):
    """待機児童の全国像。「ゼロが9割」なのに1歳児だけ突出している点を伝える。"""
    ms = taiki["municipalities"]
    total = sum(m["wait"] for m in ms)
    zero = sum(1 for m in ms if m["wait"] == 0)
    by_age = {k: sum(m["wait_age"].get(k, 0) for m in ms) for k in ("0", "1", "2", "3+")}
    top = sorted([m for m in ms if m["wait"] > 0], key=lambda m: -m["wait"])[:10]

    rows = "".join(
        f'<tr><td>{html.escape(m["pref"])} {html.escape(m["city"])}</td>'
        f'<td style="text-align:right">{m["wait"]}人</td>'
        f'<td style="text-align:right">{m["wait_age"].get("1", 0)}人</td></tr>'
        for m in top)

    return f"""
  <div class="sec-title">保育園には入れる? 待機児童のいま</div>
  <div class="stat">
    <div><div class="v">{total:,}</div><div class="l">全国の待機児童</div></div>
    <div><div class="v">{zero:,}</div><div class="l">待機児童ゼロの<br>自治体</div></div>
    <div><div class="v">{by_age['1']:,}</div><div class="l">うち1歳児</div></div>
  </div>
  <p style="font-size:.92rem">全国{len(ms):,}市区町村のうち<strong>{zero:,}({zero/len(ms)*100:.0f}%)は待機児童ゼロ</strong>です。
  「保活は大変」というイメージほど、いまは全国的に厳しくはありません。</p>
  <p style="font-size:.92rem">ただし中身を見ると話が変わります。待機児童{total:,}人のうち
  <strong>{by_age['1']:,}人({by_age['1']/total*100:.0f}%)が1歳児</strong>。0歳児は{by_age['0']}人、2歳児は{by_age['2']}人、3歳以上は{by_age['3+']}人です。</p>
  <div class="note">📌 <strong>これは「育休明けの壁」です。</strong>0歳の4月に入園させれば入りやすく、
  1年間の育休を取って1歳の4月に申し込むと急に入りにくくなる。
  育休をいつまで取るかを決めるときは、お住まいの自治体の1歳児の状況を確認しておくと安心です。</div>

  <div class="sec-title">待機児童が多い自治体</div>
  <table class="rank"><tr><th>自治体</th><th style="text-align:right">待機児童</th><th style="text-align:right">うち1歳児</th></tr>
  {rows}
  </table>
  <p style="font-size:.78rem;color:#a99">
    出典: {html.escape(taiki["source"])}({html.escape(taiki["as_of"])})<br>
    <a href="{html.escape(taiki["source_url"])}" target="_blank" rel="noopener">こども家庭庁の公表資料はこちら</a><br>
    ※待機児童の定義は国が定めていますが、認可外を利用しているなど数に含まれない「隠れ待機児童」もいます。
  </p>
"""


def build_chiiki(iry, hikaku_pages=(), taiki=None, iry_pref=None, cities=()):
    """全市区町村の「子育てのしやすさ」を検索できるページ。地域差の可視化がこのサイトの核。
    子ども医療費助成 + 保育園の待機児童数を1つの検索にまとめる。"""
    import json as _j
    ms = iry["municipalities"]
    tk = {(t["pref"], t["city"]): t for t in (taiki or {}).get("municipalities", [])}
    pf = {p["pref"]: p for p in (iry_pref or {}).get("prefectures", [])}

    # 県内での位置づけ(医療費の手厚さ順位)を先に算出しておく
    by_pref = {}
    for m in ms:
        by_pref.setdefault(m["pref"], []).append(m)
    rank_of = {}
    for pref, lst in by_pref.items():
        # 対象年齢が高い→所得制限なし→自己負担なし の順で手厚いとみなす
        ordered = sorted(lst, key=lambda x: (-x["rank_out"], x["limit_out"], x["copay_out"]))
        for i, x in enumerate(ordered, 1):
            rank_of[(x["pref"], x["city"])] = i

    rows_js = []
    for m in ms:
        t = tk.get((m["pref"], m["city"])) or {}
        wa = t.get("wait_age", {})
        rows_js.append([
            m["pref"], m["city"], m["age_out"], m["age_in"],
            m["limit_out"], m["copay_out"],
            t.get("wait", -1),
            [wa.get("0", 0), wa.get("1", 0), wa.get("2", 0), wa.get("3+", 0)],
            t.get("apply", 0),
            rank_of.get((m["pref"], m["city"]), 0),
            len(by_pref.get(m["pref"], [])),
        ])
    pref_js = {k: [v.get("age_out"), v.get("limit_out"), v.get("copay_out"), v.get("has_program")]
               for k, v in pf.items()}
    city_js = {f'{c["pref"]}{c["city"]}': c["id"] for c in (cities or [])}
    total = len(ms)
    n18 = sum(1 for m in ms if m["rank_out"] >= 18)
    nolimit = sum(1 for m in ms if not m["limit_out"])
    nocopay = sum(1 for m in ms if not m["copay_out"])
    top = [m for m in ms if m["rank_out"] >= 20]
    top.sort(key=lambda m: -m["rank_out"])
    low = [m for m in ms if m["rank_out"] <= 12]

    parts = [head(f"あなたの街の子育て環境を調べる｜{SITE_NAME}",
                  f"全国{total}市区町村の子ども医療費助成(対象年齢・所得制限・自己負担)を検索できます。住む場所で驚くほど違います。", "/chiiki.html")]
    parts.append(f"""
<header class="site"><div class="wrap"><a class="logo" href="./index.html">{html.escape(SITE_NAME)}</a></div></header>
{site_nav()}
<div class="wrap">
  <a class="back" href="./index.html">← ホーム</a>
  <h1 style="font-size:1.35rem;margin:.2em 0">あなたの街の子育て環境を調べる</h1>
  <a class="card" href="./chiiki-list.html">
    <div class="t">📚 市区町村の一覧から探す</div>
    <div class="d">医療費助成の対象年齢・待機児童・県内順位を、市区町村ごとにまとめています →</div>
  </a>
  <p style="color:var(--sub);font-size:.92rem">子ども医療費助成は<strong>国ではなく自治体の制度</strong>。だから住む場所で大きく違います。
  全国{total:,}市区町村を検索できます。</p>

  <div class="stat">
    <div><div class="v">{n18:,}</div><div class="l">18歳年度末まで<br>助成(通院)</div></div>
    <div><div class="v">{nolimit:,}</div><div class="l">所得制限なし</div></div>
    <div><div class="v">{nocopay:,}</div><div class="l">自己負担なし</div></div>
  </div>

  <div class="sec-title">市区町村を検索</div>
  <p style="color:var(--sub);font-size:.88rem;margin:0 0 6px">
  医療費助成に加えて、<strong>保育園の待機児童数</strong>もあわせて表示します。</p>
  <input class="search" id="q" type="search" placeholder="例: 世田谷区／札幌市／京丹後市" autocomplete="off">
  <div id="mres"></div>

  <div class="localnote">
    <strong>💡 実は、給付金の多くは全国共通です</strong><br>
    児童手当・出産育児一時金・育児休業給付金など、金額の大きい制度は、どこに住んでいても同じ内容で受け取れます。
    「うちの地域はどうなんだろう」と不安になりがちですが、<strong>まずは全国共通の制度を取りこぼさないこと</strong>が
    いちばん効きます。<br>
    <a href="./shindan.html">▶ 受け取れる制度を30秒で確認する</a>
  </div>

  <div class="note">
    <strong>逆に、地域によって変わるのはこの4つです</strong><br>
    ① <strong>子ども医療費助成</strong>(上の検索で確認できます)<br>
    ② <strong>保育園の入りやすさ</strong>(同上)<br>
    ③ <strong>高校授業料の上乗せ支援</strong> — 国の就学支援金に都道府県が独自に上乗せしています。
    大阪府は所得制限なしで年63万円超の授業料にも対応、東京都は国と合わせて年最大50万1,000円など、
    差がとても大きい部分です。<strong>多くは「県内進学」が条件</strong>なので越境通学は要注意。
    <a href="./koko-shushi-kin.html">▶ くわしく</a><br>
    ④ <strong>自治体独自の給付金・助成</strong>(出産祝い金、中学校の給食費無償化など)<br>
    ③④は全国をまとめた公的データが存在しないため、検索結果の
    「公式サイトで探す」リンクから、お住まいの自治体・都道府県のページをご確認ください。
  </div>

  <div class="sec-title">👑 いちばん手厚い自治体(通院 20歳年度末〜)</div>
  <table class="rank"><tr><th>自治体</th><th>通院</th><th>入院</th></tr>""")
    for m in top:
        parts.append(f'<tr><td>{html.escape(m["pref"])} {html.escape(m["city"])}</td><td>{html.escape(m["age_out"])}</td><td>{html.escape(m["age_in"])}</td></tr>')
    parts.append(f"""</table>
  <div class="note">大学生年代(22歳年度末)まで助成する自治体が{sum(1 for m in ms if m["rank_out"]>=22)}あります。移住・引っ越しを考えるときの意外な判断材料になります。</div>

  <div class="sec-title">通院が「就学前まで」の自治体</div>
  <table class="rank"><tr><th>自治体</th><th>通院</th><th>入院</th></tr>""")
    for m in low:
        parts.append(f'<tr><td>{html.escape(m["pref"])} {html.escape(m["city"])}</td><td>{html.escape(m["age_out"])}</td><td>{html.escape(m["age_in"])}</td></tr>')
    parts.append(f"""</table>
  <p style="font-size:.78rem;color:#a99;margin-top:18px">
    出典: {html.escape(iry["source"])}({html.escape(iry["as_of"])})<br>
    <a href="{html.escape(iry["source_url"])}" target="_blank" rel="noopener">こども家庭庁の公表資料はこちら</a><br>
    ※本表は公表資料をもとに整理したものです。実際の助成内容(対象範囲・手続き)は各市区町村の最新情報をご確認ください。
  </p>

  <div class="sec-title">くわしく調べた自治体</div>
  <a class="card" href="./tokyo23.html">
    <div class="t">🗼 東京23区の子育て支援をくらべる</div>
    <div class="s">23区すべての医療費・待機児童・区独自の制度を一覧で</div>
    <div class="d">018サポートなど東京都共通の制度も含めてまとめました →</div>
  </a>
  <a class="card" href="./saitama-misato.html">
    <div class="t">📍 埼玉県三郷市の子育て支援</div>
    <div class="s">子育て移動支援(1万円相当)など市独自の制度</div>
    <div class="d">市の公式サイトで確認した制度をまとめました →</div>
  </a>

  {taiki_section(taiki) if taiki else ""}

  <div class="sec-title">住む場所は変えられなくても</div>
  <p style="color:var(--sub);font-size:.92rem">医療費の助成額は自治体が決めることなので、自分では変えられません。
  でも、毎月の固定費は自分で下げられます。浮いたお金は、助成の差を埋めるくらいの効果になることもあります。</p>
  {hikaku_cards([p for p in hikaku_pages if p["id"] in ("hikaku-denki", "hikaku-sim", "hikaku-furusato")])}
</div>
<script>
const M = {_j.dumps(rows_js, ensure_ascii=False)};
const PREF = {_j.dumps(pref_js, ensure_ascii=False)};
const CITYPAGE = {_j.dumps(city_js, ensure_ascii=False)};
const q = document.getElementById('q'), out = document.getElementById('mres');
function draw(){{
  const v = q.value.trim();
  if(!v){{ out.innerHTML=''; return; }}
  const hits = M.filter(r => (r[0]+r[1]).includes(v)).slice(0,12);
  if(!hits.length){{ out.innerHTML='<div class="note">見つかりませんでした。市区町村名の一部で試してください(例:世田谷)。</div>'; return; }}
  out.innerHTML = hits.map(r => {{
    const [pref, city, ageOut, ageIn, limitOut, copayOut, wait, waitAge, apply, rank, total] = r;
    let h = '<div class="mrow"><div class="n">'+pref+' '+city+'</div>';

    // 医療費助成
    h += '<div class="dsec"><div class="dh">🏥 子ども医療費助成</div>'+
      '<div class="meta">通院 <strong>'+ageOut+'</strong>まで ／ 入院 <strong>'+ageIn+'</strong>まで</div>'+
      '<div style="margin-top:6px">'+
      (limitOut?'<span class="pill p-warn">所得制限あり</span>':'<span class="pill p-good">所得制限なし</span>')+
      (copayOut?'<span class="pill p-warn">自己負担あり</span>':'<span class="pill p-good">自己負担なし</span>')+
      '</div>';
    if (rank && total > 1) {{
      h += '<div class="meta">県内の手厚さ <strong>'+pref+'内 '+total+'市区町村中 '+rank+'位</strong></div>';
    }}
    const p = PREF[pref];
    if (p) {{
      h += '<div class="meta">※'+pref+'の制度: ' +
        (p[3] === false ? '県独自の助成なし(市区町村が実施)' :
          ('通院 '+(p[0]||'—')+'まで' + (p[1]===true?' / 所得制限あり':p[1]===false?' / 所得制限なし':''))) +
        '</div>';
    }}
    h += '</div>';

    // 保育園
    if (wait >= 0) {{
      h += '<div class="dsec"><div class="dh">🍼 保育園</div>'+
        '<div class="meta">待機児童 <strong>'+(wait===0?'0人':wait+'人')+'</strong>'+
        (apply?'（申込 '+apply.toLocaleString()+'人）':'')+'</div>';
      if (wait > 0) {{
        const labels = ['0歳','1歳','2歳','3歳〜'];
        const parts = waitAge.map((v,i)=> v>0 ? labels[i]+' '+v+'人' : null).filter(Boolean);
        if (parts.length) h += '<div class="meta">内訳: '+parts.join(' / ')+'</div>';
        if (waitAge[1] > 0 && waitAge[1] >= Math.max(...waitAge)) {{
          h += '<div class="meta" style="color:var(--brand-d)">⚠️ 1歳児がいちばん入りにくい地域です（育休明けは要注意）</div>';
        }}
      }} else {{
        h += '<div style="margin-top:4px"><span class="pill p-good">待機児童ゼロ</span></div>';
      }}
      h += '</div>';
    }}

    // 次の行動
    const q2 = encodeURIComponent(pref + city + ' 子育て 給付金 助成');
    const cp = CITYPAGE[pref + city];
    if (cp) {{
      h += '<div class="dsec"><div class="dh">📖 くわしい市の支援</div>'+
        '<div class="meta">'+city+'独自の給付金・助成を調べてまとめました。</div>'+
        '<a class="offbtn" style="margin-top:8px" href="./'+cp+'.html">'+city+'の子育て支援を見る</a></div>';
    }}
    h += '<div class="dsec"><div class="dh">📋 この街で確認すること</div>'+
      '<div class="meta">出産祝い金・入学祝い金・中学校の給食費など、自治体独自の支援は公式サイトで確認できます。</div>'+
      '<div style="margin-top:8px;font-size:.86rem">'+
      '<a href="https://www.google.com/search?q='+q2+'" target="_blank" rel="noopener">🔎 '+city+'の独自支援を探す</a>'+
      '　<a href="#" data-pref="'+pref+'" class="samepref">📍 '+pref+'内で比べる</a>'+
      '</div></div>';

    return h + '</div>';
  }}).join('');
  document.querySelectorAll('.samepref').forEach(a=>a.addEventListener('click',e=>{{
    e.preventDefault(); q.value = e.target.dataset.pref; draw();
  }}));
}}
q.addEventListener('input', draw);
</script>""")
    parts.append(footer())
    return "".join(parts)


def build_kakei(hikaku_pages):
    """「家計を軽くする」まとめページ。制度ページからの導線をここに集約する。"""
    parts = [head(f"家計を軽くする、5つの見直し｜{SITE_NAME}",
                  "子育て世帯が使える制度を確認したら、出ていくお金も見直してみませんか。ふるさと納税・通信費・電気ガス・教育費の考え方をまとめました。",
                  "/kakei.html")]
    parts.append(f"""
<header class="site"><div class="wrap"><a class="logo" href="./index.html">{html.escape(SITE_NAME)}</a></div></header>
{site_nav()}
<div class="wrap body">
  <a class="back" href="./index.html">← ホーム</a>
  <div class="pr">※本ページはプロモーションを含みます</div>
  <h1 style="font-size:1.35rem;margin:.2em 0">家計を軽くする、5つの見直し</h1>

  <p>このサイトでは「もらえるお金」を中心に紹介しています。ただ、家計を楽にする方法は
  受け取ることだけではありません。<strong>出ていくお金を減らす</strong>という方向もあります。</p>

  <p>しかも給付金の多くが一度きりなのに対して、<strong>固定費は一度下げれば効果がずっと続きます</strong>。
  月3,000円下がれば、年間で36,000円。子どもが小学校を卒業するまで続ければ、それなりの金額になります。</p>

  <div class="note">💡 全部をやる必要はありません。手をつけやすいものから1つずつで十分です。
  それぞれのページに、選び方と注意点をまとめています。</div>

  <div class="sec-title">見直しの候補</div>""")

    order = ["hikaku-sim", "hikaku-denki", "hikaku-furusato", "hikaku-kawanai",
             "hikaku-kyozai", "hikaku-card"]
    why = {
        "hikaku-sim": "効果が大きく、一度やれば戻らない。まず手をつけるならここ。",
        "hikaku-denki": "生活を変えずに単価だけ下げられる。手続きもオンラインで完結。",
        "hikaku-furusato": "実質2,000円の負担で、おむつや米など必ず使うものが届く。",
        "hikaku-kyozai": "塾より費用を抑えたい家庭の選択肢。合うかどうかは試してから。",
        "hikaku-card": "毎月必ず出ていく支出の支払い方を変えるだけ。",
        "hikaku-kawanai": "短い期間しか使わないものは、買わずに済ませる手もある。",
    }
    pages = {p["id"]: p for p in hikaku_pages}
    for i, pid in enumerate(order, 1):
        p = pages.get(pid)
        if not p:
            continue
        parts.append(f"""<a class="card" href="./{pid}.html">
  <div class="t">{p.get('emoji','')} {html.escape(p.get('nav_title', p['title']))}</div>
  <div class="s">{html.escape(why.get(pid,''))}</div>
  <div class="d">{html.escape(p['lead'][:70])}… →</div>
</a>""")

    parts.append("""
  <div class="sec-title">やる順番に迷ったら</div>
  <ul class="tips">
    <li>まず<strong>通信費</strong>。家族分をまとめて見直すと効果が一番大きく出ます</li>
    <li>次に<strong>電気・ガス</strong>。使用量が多い家庭ほど差が出ます</li>
    <li><strong>ふるさと納税</strong>は年末に向けて。上限額の確認から始めてください</li>
    <li>教育費とカードは、生活が落ち着いてからで構いません</li>
  </ul>

  <div class="note">⚠️ 料金やキャンペーンの条件は頻繁に変わります。申し込み前に必ず各社の公式サイトで
  最新の条件をご確認ください。当サイトは特定の事業者を推奨するものではありません。</div>

  <a class="cta" href="./shindan.html" style="display:block;text-align:center">
    ▶ 受け取れる制度も確認する
  </a>
</div>""")
    parts.append(footer())
    return "".join(parts)


def build_city(c, iry_map, taiki_map, rank_map):
    """自治体ページ。全国データ(医療費・保育園)＋手作業で調べた市独自の支援。"""
    key = (c["pref"], c["city"])
    med = iry_map.get(key)
    tk = taiki_map.get(key)
    rank = rank_map.get(key)
    name = f'{c["pref"]}{c["city"]}'

    parts = [head(f"{name}の子育て支援・助成金・補助金｜{SITE_NAME}",
                  f"{name}の子ども医療費助成(子供医療費)、保育園の待機児童、"
                  f"市独自の給付金・助成金・補助金・支援金をまとめました。",
                  f"/{c['id']}.html")]
    parts.append(f"""
<header class="site"><div class="wrap"><a class="logo" href="./index.html">{html.escape(SITE_NAME)}</a></div></header>
{site_nav()}
<div class="wrap body">
  <a class="back" href="./chiiki.html">← 地域で調べる</a>
  <h1 style="font-size:1.4rem;margin:.2em 0">{html.escape(name)}の子育て支援</h1>
  <p>{html.escape(c['lead'])}</p>
  <p style="font-size:.92rem;color:var(--sub)">{html.escape(c["city"])}の子育て支援は、
  「助成金」「補助金」「支援金」「給付金」と呼び方がわかれています。
  名前がちがうだけで同じ制度のこともあるので、このページではまとめて確認できるようにしました。</p>""")

    if med:
        parts.append(f"""
  <div class="sec-title">🏥 こども医療費助成</div>
  <div class="amount">通院 {html.escape(med['age_out'])}まで ／ 入院 {html.escape(med['age_in'])}まで</div>
  <div style="margin:8px 0">
    {'<span class="pill p-warn">所得制限あり</span>' if med['limit_out'] else '<span class="pill p-good">所得制限なし</span>'}
    {'<span class="pill p-warn">自己負担あり</span>' if med['copay_out'] else '<span class="pill p-good">自己負担なし</span>'}
  </div>
  <p style="font-size:.86rem;color:var(--sub)">自治体によって
  「子ども医療費助成」「子供医療費助成」「乳幼児医療費助成」と名前がちがいますが、同じ制度です。</p>""")
        if rank:
            parts.append(f'<p style="font-size:.9rem;color:var(--sub)">県内の手厚さ: {html.escape(c["pref"])}内 {rank[1]}市区町村中 <strong>{rank[0]}位</strong></p>')

    if tk:
        w = tk["wait"]
        wa = tk["wait_age"]
        parts.append(f"""
  <div class="sec-title">🍼 保育園</div>
  <div class="amount">待機児童 {('0人' if w == 0 else str(w) + '人')}（申込 {tk['apply']:,}人）</div>""")
        if w > 0:
            det = " / ".join(f"{lb} {wa.get(k,0)}人" for k, lb in
                             (("0", "0歳"), ("1", "1歳"), ("2", "2歳"), ("3+", "3歳〜")) if wa.get(k, 0) > 0)
            parts.append(f'<p style="font-size:.9rem;color:var(--sub)">内訳: {det}</p>')
        else:
            parts.append('<p style="font-size:.9rem;color:var(--sub)">直近の調査では、希望しても入れなかった児童はいませんでした。ただし年度途中の入園は別なので、市の窓口で空き状況をご確認ください。</p>')

    parts.append(f'<div class="sec-title">💰 {html.escape(c["city"])}の支援制度</div>')
    if c.get("own_note"):
        parts.append(f'<div class="note">🔍 {html.escape(c["own_note"])}</div>')
    for p in c["programs"]:
        parts.append(f"""<div class="card" style="cursor:default">
  <div><span class="badge">{html.escape(p['tag'])}</span></div>
  <div class="t" style="margin-top:6px">{html.escape(p['name'])}</div>
  <div class="s">{html.escape(p['amount'])}</div>
  <div class="d" style="margin:8px 0">{html.escape(p['summary'])}</div>
  <dl style="margin:0">
    <dt style="font-weight:800;font-size:.78rem;color:var(--accent);margin-top:10px">対象</dt>
    <dd style="margin:2px 0 0;font-size:.9rem">{html.escape(p['target'])}</dd>
    <dt style="font-weight:800;font-size:.78rem;color:var(--accent);margin-top:8px">申請</dt>
    <dd style="margin:2px 0 0;font-size:.9rem">{html.escape(p['how'])}</dd>
    <dt style="font-weight:800;font-size:.78rem;color:var(--accent);margin-top:8px">期限</dt>
    <dd style="margin:2px 0 0;font-size:.9rem">{html.escape(p['deadline'])}</dd>
  </dl>
  <a class="offbtn" href="{html.escape(p['url'])}" target="_blank" rel="noopener">市の公式ページで確認</a>
</div>""")

    parts.append(f"""
  <div class="note">📌 {html.escape(c['note'])}</div>
  <div class="localnote">
    <strong>全国共通の制度も忘れずに</strong><br>
    児童手当・出産育児一時金・育児休業給付金などは、どこに住んでいても同じ内容で受け取れます。
    市独自の支援とあわせて確認してください。<br>
    <a href="./shindan.html">▶ 受け取れる制度を30秒で確認する</a>
  </div>
  <a class="offbtn" href="{html.escape(c['kosodate_top']) if c.get('kosodate_top') else GSEARCH + urllib.parse.quote(c['pref'] + c['city'] + ' 子育て 給付金 公式')}" target="_blank" rel="noopener">🔗 {html.escape(c['city'])}の子育て支援ページ(公式)</a>
""")
    parts.append(related_card(None, [1]))
    parts.append("</div>")
    parts.append(footer())
    return "".join(parts)


def build_city_index(cities, iry_map, taiki_map, rank_map, group_pref, page_id, title, lead):
    """同じ都道府県の自治体を横並びで比較できる一覧。引っ越し検討に直結する。"""
    rows = [c for c in cities if c["pref"] == group_pref]
    if not rows:
        return None
    parts = [head(f"{title}｜{SITE_NAME}", lead[:100], f"/{page_id}.html")]
    parts.append(f"""
<header class="site"><div class="wrap"><a class="logo" href="./index.html">{html.escape(SITE_NAME)}</a></div></header>
{site_nav()}
<div class="wrap body">
  <a class="back" href="./chiiki.html">← 地域で調べる</a>
  <h1 style="font-size:1.4rem;margin:.2em 0">{html.escape(title)}</h1>
  <p>{html.escape(lead)}</p>
  <div style="overflow-x:auto">
  <table class="rank"><tr><th>自治体</th><th>医療費(通院)</th><th style="text-align:right">待機児童</th><th style="text-align:right">独自制度</th></tr>""")
    for c in sorted(rows, key=lambda x: x["city"]):
        k = (c["pref"], c["city"])
        med = iry_map.get(k)
        tk = taiki_map.get(k)
        own = sum(1 for p in c["programs"] if "独自" in p.get("tag", ""))
        own_txt = str(own) if own else ("なし" if c.get("checked_own") else "—")
        parts.append(
            f'<tr><td><a href="./{c["id"]}.html">{html.escape(c["city"])}</a></td>'
            f'<td>{html.escape(med["age_out"]) if med else "—"}</td>'
            f'<td style="text-align:right">{(str(tk["wait"]) + "人") if tk else "—"}</td>'
            f'<td style="text-align:right">{own_txt}</td></tr>')
    parts.append("""</table></div>
  <div class="note">「独自制度」は、当サイトが公式サイトなどで確認できた<strong>その自治体独自の支援</strong>の件数です。
  「なし」は調べたうえで独自の大きな現金給付が確認できなかったという意味で、支援が何もないわけではありません
  (産後ケアや一時預かりなどのサービスは各区で実施されています)。<br>
  なお各区が「出産応援ギフト」などの名前で案内している10万円分のギフトは、
  <strong>国の給付に東京都が上乗せしたもの</strong>で、23区共通です。区独自の制度と混同されやすいので注意してください。</div>
</div>""")
    parts.append(footer())
    return "".join(parts)


def build_policy():
    """プライバシーポリシー・免責事項。GA4のCookie利用とアフィリエイト表記のために必要。"""
    parts = [head(f"プライバシーポリシー・免責事項｜{SITE_NAME}",
                  f"{SITE_NAME}のプライバシーポリシーおよび免責事項です。", "/policy.html")]
    parts.append(f"""
<header class="site"><div class="wrap"><a class="logo" href="./index.html">{html.escape(SITE_NAME)}</a></div></header>
{site_nav()}
<div class="wrap body">
  <a class="back" href="./index.html">← ホーム</a>
  <h1 style="font-size:1.3rem">プライバシーポリシー・免責事項</h1>

  <div class="sec-title">当サイトについて</div>
  <p>{html.escape(SITE_NAME)}(以下「当サイト」)は、子育て世帯が利用できる国や自治体の支援制度について、
  公的機関が公表している情報をもとに、わかりやすく整理して提供する情報サイトです。</p>

  <div class="sec-title">アクセス解析ツールについて</div>
  <p>当サイトでは、サイトの利用状況を把握するためにGoogleアナリティクス(Google LLC提供)を利用しています。
  Googleアナリティクスはトラフィックデータの収集のためにCookieを使用しますが、
  このデータは匿名で収集されており、個人を特定するものではありません。</p>
  <p>この機能はブラウザの設定でCookieを無効にすることで収集を拒否できます。
  詳しくは<a href="https://policies.google.com/technologies/partner-sites" target="_blank" rel="noopener">Googleのポリシーと規約</a>をご確認ください。</p>

  <div class="sec-title">広告について</div>
  <p>当サイトでは、第三者配信のアフィリエイトプログラムを利用しています。
  これにより、広告主から支払われる成果報酬を得る場合があります。
  当該ページには、その旨を「本ページはプロモーションを含みます」等の表記で明示しています。</p>
  <p>アフィリエイトプログラムにおいて、広告配信事業者がCookieを使用して
  利用者の当サイトへの過去のアクセス情報に基づいて広告を配信することがあります。</p>

  <div class="sec-title">免責事項</div>
  <p>当サイトに掲載する情報は、公的機関の公表資料をもとに、可能な限り正確を期して作成しています。
  ただし、制度の内容・金額・対象条件は法改正や年度の切り替え、お住まいの自治体によって異なり、
  また変更される場合があります。</p>
  <p><strong>当サイトの情報は制度の概要をつかむための参考情報であり、
  申請の可否や受給額を保証するものではありません。</strong>
  実際の申請にあたっては、必ず各制度の公式ページおよびお住まいの市区町村の窓口で
  最新かつ正確な情報をご確認ください。</p>
  <p>当サイトの情報を利用したことにより生じたいかなる損害についても、当サイトは責任を負いかねます。
  また、当サイトは特定の金融商品・サービスの購入や申込みを勧誘するものではなく、
  投資助言・税務相談・法律相談を行うものではありません。</p>

  <div class="sec-title">著作権について</div>
  <p>当サイトが引用・参照する公的機関の公表資料の著作権は、各機関に帰属します。
  当サイトは各情報の出典を明示し、公式ページへのリンクを掲載しています。</p>

  <div class="sec-title">リンクについて</div>
  <p>当サイトは原則リンクフリーです。リンクを行う場合の許可・連絡は不要です。</p>

  <div class="sec-title">運営者情報</div>
  <dl>
    <dt>サイト名</dt><dd>{html.escape(SITE_NAME)}</dd>
    <dt>URL</dt><dd>{BASE_URL}</dd>
    <dt>運営者</dt><dd>{html.escape(OPERATOR_NAME)}</dd>
    <dt>お問い合わせ</dt><dd>下記のフォームよりご連絡ください。掲載内容の誤りのご指摘も歓迎しています。</dd>
  </dl>
  <a class="offbtn" href="{html.escape(CONTACT_FORM)}" target="_blank" rel="noopener">✉️ お問い合わせフォーム</a>

  <p style="font-size:.78rem;color:#a99;margin-top:20px">制定日: 2026年7月25日</p>
</div>""")
    parts.append(footer())
    return "".join(parts)


def build_city_auto_index(ids):
    """自動生成した自治体ページの一覧。都道府県ごとにまとめる。
    孤立ページにするとGoogleにも人にも辿り着けないので、必ずここから繋ぐ。"""
    byp = {}
    for cid in ids:
        rest = cid[len("chiiki-"):]
        for suf in ("都", "道", "府", "県"):
            i = rest.find(suf)
            if i > 0:
                byp.setdefault(rest[:i + 1], []).append((cid, rest[i + 1:]))
                break
    parts = [head(f"市区町村から探す｜{SITE_NAME}",
                  "子ども医療費助成が何歳までか、保育園の待機児童が何人かを、市区町村ごとにまとめています。",
                  "/chiiki-list.html")]
    parts.append(f"""
<header class="site"><div class="wrap"><a class="logo" href="./index.html">{html.escape(SITE_NAME)}</a></div></header>
{site_nav()}
<div class="wrap body">
  <a class="back" href="./chiiki.html">← 地域で調べる</a>
  <h1 style="font-size:1.35rem;margin:.2em 0">市区町村から探す</h1>
  <p>子ども医療費助成が何歳までか、保育園の待機児童が何人か、県内で何番目に手厚いかを
  市区町村ごとにまとめています。まずは規模の大きい市区町村から掲載しています。</p>""")
    for pref in sorted(byp):
        parts.append(f'<div class="sec-title">{html.escape(pref)}</div><p style="line-height:2.2">')
        for cid, city in sorted(byp[pref], key=lambda x: x[1]):
            parts.append(f'<a href="./{urllib.parse.quote(cid)}.html" '
                         f'style="display:inline-block;margin:0 8px 4px 0">{html.escape(city)}</a>')
        parts.append("</p>")
    parts.append('<div class="note">掲載のない市区町村は、'
                 '<a href="./chiiki.html">地域で調べる</a>から検索できます。</div>')
    parts.append("</div>" + footer())
    return "".join(parts)


def build_kabe():
    """「年収の壁」試算ツール。スライダーを動かすと世帯の手取りが追従する。
    しきい値は国税庁・厚労省の一次情報から取った確定値のみを使う(下のTHRESHOLDS)。
    社会保険料率と税率は概算なので、画面上で「目安」と明示すること。"""
    parts = [head(f"年収の壁シミュレーター｜{SITE_NAME}",
                  "妻(配偶者)の年収をスライダーで動かすと、世帯の手取りがどう変わるかがその場で分かります。"
                  "123万・130万・160万の壁を国税庁と厚生労働省の資料にもとづいて整理しました。",
                  "/kabe.html")]
    parts.append(f"""
<header class="site"><div class="wrap"><a class="logo" href="./index.html">{html.escape(SITE_NAME)}</a></div></header>
{site_nav()}
<div class="wrap body">
  <a class="back" href="./index.html">← ホーム</a>
  <div class="pr">※本ページはプロモーションを含みます</div>
  <h1 style="font-size:1.35rem;margin:.2em 0">年収の壁シミュレーター</h1>
  <p>2025年(令和7年)の税制改正で「103万円の壁」はなくなりました。いまの壁がどこにあるのか、
  スライダーを動かして確かめてください。<strong>世帯の手取り</strong>がその場で計算されます。</p>

  <div class="card" style="cursor:default">
    <label style="display:block;font-weight:700;margin-bottom:6px">パートで働く方の年収
      <span id="kIncome" style="color:#F4643B;font-size:1.3rem">1,000,000</span> 円</label>
    <input id="kSlider" type="range" min="0" max="2500000" step="10000" value="1000000"
           style="width:100%;accent-color:#FF8A65;height:28px">
    <div style="display:flex;justify-content:space-between;font-size:.75rem;color:#6B6B76">
      <span>0円</span><span>250万円</span></div>

    <label style="display:block;font-weight:700;margin:16px 0 6px">配偶者(働いている側)の年収
      <span id="kHIncome" style="color:#2F8A80;font-size:1.15rem">5,000,000</span> 円</label>
    <input id="kHSlider" type="range" min="1000000" max="14000000" step="100000" value="5000000"
           style="width:100%;accent-color:#4DB6AC;height:24px">

    <div style="margin-top:14px;font-size:.9rem">
      <label style="display:block;margin-bottom:4px"><input type="checkbox" id="kBig" checked> 勤務先の従業員が50人超</label>
      <label style="display:block;margin-bottom:4px"><input type="checkbox" id="kHours" checked> 週20時間以上働く</label>
      <label style="display:block"><input type="checkbox" id="kStudent"> 学生である</label>
      <div style="color:#6B6B76;font-size:.8rem;margin-top:8px;line-height:1.6">
        この3つは<strong>106万円の壁が効くかどうか</strong>を決める条件です。
        「従業員50人超」と「週20時間以上」の<strong>両方</strong>にあてはまり、かつ学生でない場合だけ、
        年収106万円で社会保険に加入します。どちらか一方でも外れると、壁は130万円まで動きます。
      </div>
    </div>

    <div id="kQuick" style="margin-top:14px;padding:12px;border-radius:10px;background:#FFF5EF;
         line-height:1.8;font-size:.95rem"></div>
    <div style="color:#6B6B76;font-size:.8rem;margin-top:8px;line-height:1.6">
      グラフの縦軸は<strong>世帯の手取り合計</strong>です。ふたりぶんの収入から、
      社会保険料・所得税・住民税を引いた目安を出しています。
      相手の年収を動かすと世帯の水準ごと上下し、働く側の年収を動かすと軸は固定されたまま線が動きます。
    </div>
  </div>

  <canvas id="kChart" width="720" height="380"
          style="width:100%;height:auto;background:#FFFDF9;border-radius:12px;margin:10px 0"></canvas>

  <div id="kVerdict"></div>

  <div class="sec-title">いまの壁の一覧</div>
  <ul class="tips">
    <li><strong>123万円</strong> … 「配偶者控除」から「配偶者特別控除」に切り替わります。<strong>ただし控除額は満額のまま引き継がれるので、ここで手取りが減ることはありません</strong></li>
    <li><strong>160万円</strong> … 本人に所得税がかかり始め、<strong>配偶者特別控除もここから段階的に減り始めます</strong>。実質的な分かれ目はこちら</li>
    <li><strong>130万円</strong> … 社会保険の扶養から外れます(従業員50人以下の勤務先などの場合)</li>
    <li><strong>106万円</strong> … 従業員50人超・週20時間以上・月額8.8万円以上・学生でない、をすべて満たすと社会保険に加入します</li>
    <li><strong>201万5,999円</strong> … 配偶者特別控除もここで終わります</li>
  </ul>

  <div class="note">📌 <strong>103万円の壁は、もうありません。</strong>
  基礎控除が48万円から最大95万円に、給与所得控除の最低保障が55万円から65万円に引き上げられたためです。
  扶養に入れるかどうかの線は123万円に移りました。</div>

  <div class="sec-title">106万円の壁は、これから消えていきます</div>
  <p>社会保険の加入要件のうち<strong>月額賃金8.8万円以上という条件は、2025年6月から3年以内に撤廃</strong>されることが決まっています。
  勤務先の規模の条件も段階的に下がります。</p>
  <ul class="tips">
    <li>2027年10月 … 従業員36人以上</li>
    <li>2029年10月 … 従業員21人以上</li>
    <li>2032年10月 … 従業員11人以上</li>
    <li>2035年10月 … 従業員10人以下も対象に</li>
  </ul>
  <div class="note">📌 つまり将来的には、106万円の壁は「週20時間以上働くかどうか」だけで決まるようになります。
  いま50人以下の職場で働いている方も、いずれ対象になります。</div>

  <div class="sec-title">この試算の前提</div>
  <ul class="mis">
    <li>手取りの計算は<strong>目安</strong>です。社会保険料は収入の約15%、所得税は5%、住民税は10%として概算しています</li>
    <li>実際の保険料は加入する健康保険や住んでいる地域で変わります</li>
    <li>住民税は年収100万円前後から自治体ごとの基準でかかり始めます(この試算には含めていません)</li>
    <li>配偶者特別控除は配偶者の収入に応じて段階的に減りますが、ここでは簡略化しています</li>
    <li>勤務先の家族手当・扶養手当が年収で決まる場合は、別途その影響があります</li>
  </ul>

  <div class="note">この試算は一般的な制度の説明であり、個別の税務相談ではありません。
  正確な金額は勤務先・お住まいの市区町村・税務署にご確認ください。</div>

  <div class="sec-title">出典</div>
  <ul class="tips">
    <li><a href="https://www.nta.go.jp/users/gensen/2025kiso/index.htm" target="_blank" rel="noopener">国税庁 令和7年度税制改正による所得税の基礎控除の見直し等について</a></li>
    <li><a href="https://www.mhlw.go.jp/stf/taiou_001_00002.html" target="_blank" rel="noopener">厚生労働省「年収の壁」への対応</a></li>
  </ul>

  <div class="sec-title">ここから先は、計算では出せません</div>
  <p>このシミュレーターで分かるのは、壁をどこで超えるかと手取りの目安までです。
  実際には、社会保険をどちらの扶養に入れるか、保険を見直すべきか、教育資金をどう準備するか——
  といった条件が絡み合います。<strong>そこは計算式ではなく、個別に見てもらうしかない領域です。</strong></p>

  <div class="card" style="cursor:default">
    <div class="t">お金の専門家(FP)に無料で相談する</div>
    <div class="d" style="margin:6px 0 10px">全国約3,000名のFPから紹介を受けられるサービスです。
    訪問でもオンラインでも相談でき、何度でも無料。担当者が合わなければ変更も無料でできます。</div>
    <ul class="mis" style="margin:0">
      <li>次に当てはまる方は対象外です: 世帯年収100万円以下 / 20歳未満 / 無職・学生 / 海外在住</li>
      <li>生命保険に関する相談が前提です。損害保険だけの相談は対象外です</li>
      <li>相談は無料ですが、面談の時間は必要です。数分で終わる形だけの面談はできません</li>
    </ul>
    <div class="note">📌 当サイトは特定の保険や事業者をすすめる立場にありません。
    自分で判断しきれないときの選択肢のひとつとしてご覧ください。</div>
    <a class="offbtn" href="https://ck.jp.ap.valuecommerce.com/servlet/referral?sid=3776805&pid=892679912"
       target="_blank" rel="noopener sponsored nofollow"><img
       src="https://ad.jp.ap.valuecommerce.com/servlet/gifbanner?sid=3776805&pid=892679912"
       height="1" width="1" border="0" alt="">FPの無料相談について見る</a>
  </div>

  <div class="sec-title">もっとくわしく</div>
  <a class="card" href="./nenmatsu-chosei.html">
    <div class="t">📋 年末調整、子育て世帯が書き忘れるところ</div>
    <div class="d">16歳未満の子どもは扶養控除の対象外ですが、住民税の欄には記載が必要です →</div>
  </a>
  <a class="card" href="./nenshu-kabe.html">
    <div class="t">📊 103万の壁はもうありません。いまの壁は106万・123万・160万</div>
    <div class="d">なぜ壁が動いたのか、配偶者控除と配偶者特別控除の関係を、国税庁と厚生労働省の資料にもとづいて解説しています →</div>
  </a>

  <a class="cta" href="./shindan.html" style="display:block;text-align:center">もらえる給付金も調べる →</a>
</div>
<script>
(function(){{
  var S=document.getElementById('kSlider'), L=document.getElementById('kIncome'),
      V=document.getElementById('kVerdict'), C=document.getElementById('kChart'),
      B=document.getElementById('kBig'), H=document.getElementById('kHours'),
      ST=document.getElementById('kStudent'),
      HS=document.getElementById('kHSlider'), HL=document.getElementById('kHIncome'),
      Q=document.getElementById('kQuick');
  var yen=function(n){{return Math.round(n).toLocaleString('ja-JP');}};

  // 社会保険に入るかどうか(厚労省の要件)
  function insured(inc){{
    if(ST.checked) return false;                        // 学生は対象外
    if(B.checked && H.checked && inc>=1060000) return true;  // 106万の壁
    return inc>=1300000;                                // 130万の壁(扶養から外れる)
  }}
  // 配偶者(働いている側)の合計所得ざっくり。給与所得控除を引いた額
  function partnerIncome(h){{
    var ded = h<=1900000 ? 650000
            : h<=3600000 ? h*0.3+80000
            : h<=6600000 ? h*0.2+440000
            : h<=8500000 ? h*0.1+1100000 : 1950000;
    return Math.max(0, h-ded);
  }}
  // 【国税庁 No.1195 の表(令和7年分以後)をそのまま持つ】控除は2つの軸で決まる。
  //  ・配偶者控除か配偶者特別控除かの「区分」は、働く側の合計所得(58万円以下かどうか)で決まる
  //  ・控除額は 働く側の所得=行 / 相手の所得=列 の組み合わせで決まる
  //  相手の合計所得が1,000万円を超えると、どちらの控除も使えない。
  var SPOUSE_TABLE = [
    [ 950000, [380000,260000,130000]],
    [1000000, [360000,240000,120000]],
    [1050000, [310000,210000,110000]],
    [1100000, [260000,180000, 90000]],
    [1150000, [210000,140000, 70000]],
    [1200000, [160000,110000, 60000]],
    [1250000, [110000, 80000, 40000]],
    [1300000, [ 60000, 40000, 20000]],
    [1330000, [ 30000, 20000, 10000]]
  ];
  function spouseAllowance(wInc, h){{
    var a = partnerIncome(wInc);        // 働く側の合計所得
    var b = partnerIncome(h);           // 相手の合計所得
    if(b>10000000) return {{amt:0, kind:'対象外'}};
    var col = b>9500000 ? 2 : b>9000000 ? 1 : 0;
    if(a<=580000) return {{amt:[380000,260000,130000][col], kind:'配偶者控除'}};
    for(var i=0;i<SPOUSE_TABLE.length;i++){{
      if(a<=SPOUSE_TABLE[i][0]) return {{amt:SPOUSE_TABLE[i][1][col], kind:'配偶者特別控除'}};
    }}
    return {{amt:0, kind:'控除なし'}};
  }}
  function spouseDeduction(h){{ return spouseAllowance(0,h).amt; }}
  // 控除を失ったときの増税額は相手の税率で決まる(所得税+住民税10%の概算)
  function partnerRate(h){{
    var a = partnerIncome(h);
    var it = a<=1950000 ? 0.05 : a<=3300000 ? 0.10 : a<=6950000 ? 0.20
           : a<=9000000 ? 0.23 : a<=18000000 ? 0.33 : 0.40;
    return it + 0.10;
  }}
  // 満額からいくら減ったか。表が5万円刻みなので、グラフは階段状になる。
  function lostDeduction(inc, h){{
    return spouseDeduction(h) - spouseAllowance(inc,h).amt;
  }}
  // 基礎控除(令和7・8年分。合計所得で変わる)
  function basicDed(a){{
    return a<=1320000 ? 950000 : a<=3360000 ? 880000
         : a<=4890000 ? 680000 : a<=6550000 ? 630000
         : a<=23500000 ? 580000 : 0;
  }}
  // 所得税(超過累進)。課税所得から求める
  function incomeTax(t){{
    if(t<=0) return 0;
    if(t<=1950000)  return t*0.05;
    if(t<=3300000)  return t*0.10 - 97500;
    if(t<=6950000)  return t*0.20 - 427500;
    if(t<=9000000)  return t*0.23 - 636000;
    if(t<=18000000) return t*0.33 - 1536000;
    if(t<=40000000) return t*0.40 - 2796000;
    return t*0.45 - 4796000;
  }}
  // 働いている側(相手)の手取り。配偶者(特別)控除の有無で変わる
  function partnerNet(h, deduction){{
    var ins = h*0.15;                       // 社会保険料 約15%
    var a = partnerIncome(h);               // 給与所得
    var taxable = Math.max(0, a - ins - basicDed(a) - deduction);
    return h - ins - incomeTax(taxable) - taxable*0.10;   // 住民税10%
  }}
  // 世帯の手取り合計(目安)。noTax=true なら働く側の所得税がなかった場合の比較線
  function net(inc, noTax){{
    var h = +HS.value;
    var ins = insured(inc) ? inc*0.15 : 0;              // 社会保険料 約15%
    var taxable = Math.max(0, inc - 650000 - 950000);   // 給与所得控除65万 + 基礎控除95万
    var itax = noTax ? 0 : taxable*0.05;                // 働く側の所得税(概算5%)
    // 世帯合計 = 相手の手取り(控除の影響込み) + 働く側の手取り
    return partnerNet(h, spouseAllowance(inc,h).amt) + (inc - ins - itax);
  }}

  function draw(cur){{
    var ctx=C.getContext('2d'), W=C.width, Hh=C.height, PL=68, PR=16, PT=46, PB=40;
    ctx.clearRect(0,0,W,Hh);
    var max=2500000, ny=[];
    for(var x=0;x<=max;x+=5000){{ ny.push([x,net(x)]); }}
    // 縦軸は0からではなく、変化が見えるように範囲を絞る。
    // ただし相手の年収を動かすたびに軸が動くと読みづらいので、
    // 「控除の損失が最大のとき」と「まったくないとき」の両端で固定する。
    // こうすると相手の年収を変えても軸は動かず、線だけが動く。
    // 縦軸は相手の年収だけで決める。働く側のスライダーを動かしても軸は動かず、
    // 線だけが動く。相手のスライダーを動かしたときは世帯の水準ごと上下する。
    var baseNet = partnerNet(+HS.value, spouseDeduction(+HS.value));
    var lo = baseNet - 250000, hi = baseNet + max*0.95;
    var sx=function(x){{return PL+(W-PL-PR)*x/max;}};
    var sy=function(v){{return Hh-PB-(Hh-PT-PB)*(v-lo)/(hi-lo);}};

    // 横目盛り(縦軸のラベル)
    ctx.font='11px sans-serif'; ctx.textAlign='right';
    var step=Math.pow(10,Math.floor(Math.log(hi-lo)/Math.LN10))/2;
    if((hi-lo)/step>7) step*=2;
    for(var g=Math.ceil(lo/step)*step; g<=hi; g+=step){{
      ctx.strokeStyle='#F0EAE4'; ctx.beginPath();
      ctx.moveTo(PL,sy(g)); ctx.lineTo(W-PR,sy(g)); ctx.stroke();
      ctx.fillStyle='#8A8A94'; ctx.fillText((Math.round(g/10000))+'万', PL-8, sy(g)+4);
    }}
    ctx.textAlign='left';

    // 壁の縦線
    var walls=[[1060000,'106万'],[1230000,'123万'],[1300000,'130万'],[1600000,'160万']];
    walls.forEach(function(w){{
      ctx.strokeStyle='#D9CEC6'; ctx.setLineDash([4,4]); ctx.beginPath();
      ctx.moveTo(sx(w[0]),PT); ctx.lineTo(sx(w[0]),Hh-PB); ctx.stroke(); ctx.setLineDash([]);
      ctx.fillStyle='#8A8A94'; ctx.textAlign='center';
      ctx.fillText(w[1], sx(w[0]), PT-6); ctx.textAlign='left';
    }});
    // 横軸の目盛り
    ctx.fillStyle='#8A8A94'; ctx.textAlign='center';
    [0,500000,1000000,1500000,2000000,2500000].forEach(function(x){{
      ctx.fillText((x/10000)+'万', sx(x), Hh-PB+16);
    }});
    ctx.textAlign='left';

    // 比較線: 所得税がなかった場合(160万円から実線と離れていくのが所得税の影響)
    ctx.strokeStyle='#9AA7B4'; ctx.lineWidth=2; ctx.setLineDash([6,5]); ctx.beginPath();
    for(var x2=0;x2<=max;x2+=5000){{
      var v2=net(x2,true);
      x2?ctx.lineTo(sx(x2),sy(v2)):ctx.moveTo(sx(x2),sy(v2));
    }}
    ctx.stroke(); ctx.setLineDash([]);
    // 手取りの線
    ctx.strokeStyle='#FF8A65'; ctx.lineWidth=3; ctx.beginPath();
    ny.forEach(function(p,i){{ i?ctx.lineTo(sx(p[0]),sy(p[1])):ctx.moveTo(sx(p[0]),sy(p[1])); }});
    ctx.stroke();
    // 凡例(横軸のラベルと重ならないよう、グラフの内側に置く)
    ctx.font='11px sans-serif';
    var lw=150, lh=40, lx=W-PR-lw-10, ly=Hh-PB-lh-12;
    ctx.fillStyle='rgba(255,255,255,0.88)';
    ctx.beginPath(); ctx.roundRect(lx, ly, lw, lh, 6); ctx.fill();
    ctx.strokeStyle='#EFE7E1'; ctx.lineWidth=1; ctx.stroke();
    ctx.fillStyle='#FF8A65'; ctx.fillRect(lx+10, ly+11, 14, 3);
    ctx.fillStyle='#6B6B76'; ctx.fillText('実際の手取り', lx+30, ly+15);
    ctx.fillStyle='#9AA7B4'; ctx.fillRect(lx+10, ly+27, 14, 3);
    ctx.fillStyle='#6B6B76'; ctx.fillText('所得税なしの場合', lx+30, ly+31);
    // 現在地
    ctx.strokeStyle='#F4643B'; ctx.setLineDash([3,3]); ctx.lineWidth=1; ctx.beginPath();
    ctx.moveTo(sx(cur),PT); ctx.lineTo(sx(cur),Hh-PB); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle='#F4643B'; ctx.beginPath();
    ctx.arc(sx(cur),sy(net(cur)),7,0,Math.PI*2); ctx.fill();

    ctx.fillStyle='#2B2B33'; ctx.font='bold 13px sans-serif';
    ctx.fillText('世帯の手取り合計(目安)', PL, 16);
    ctx.fillStyle='#8A8A94'; ctx.font='10px sans-serif';
    ctx.fillText('※縦軸は0からではありません(変化を見やすくするため)', PL, 30);
  }}

  function update(){{
    var inc=+S.value; L.textContent=yen(inc);
    var hInc=+HS.value; HL.textContent=yen(hInc);
    var ins=insured(inc), rows=[];
    // スライダーのすぐ下に要点だけ出す(グラフまでスクロールしなくても分かるように)
    var ok=function(b,s){{return '<span style="color:'+(b?'#3F6F69':'#D14757')+'">'+s+'</span>';}};
    // 控除の判定は「働く側の年収」と「相手の所得」の両方で決まる。
    // 相手の合計所得が1,000万円を超えると、配偶者控除も配偶者特別控除も使えない。
    function spouseStatus(inc, h){{
      var r = spouseAllowance(inc,h), full = spouseDeduction(h);
      var man = function(v){{return (v/10000)+'万円';}};
      if(r.kind==='対象外') return ['控除なし(配偶者の所得が1,000万円超)', false,
        '配偶者の合計所得が1,000万円を超えているため、働く側の年収にかかわらず受けられません。'];
      if(r.kind==='控除なし') return ['控除なし(働く側の所得が133万円超)', false,
        '給与だけなら年収201万5,999円を超えた状態です。配偶者特別控除もここで終わりです。'];
      if(r.kind==='配偶者控除') return ['配偶者控除 '+man(r.amt), true,
        '働く側の合計所得が58万円以下(給与なら123万円以下)なのでこちらです。'];
      return ['配偶者特別控除 '+man(r.amt)+(r.amt<full?'（満額'+man(full)+'から減っています）':''),
        r.amt>=full,
        '123万円を超えると配偶者特別控除に切り替わります。控除額は満額のまま160万円まで続き、'
        +'そこから5万円刻みで段階的に減っていきます。'];
    }}
    var sp = spouseStatus(inc, hInc);
    Q.innerHTML =
      '世帯の手取り合計 <span style="color:#F4643B;font-size:1.25rem">'+yen(net(inc))+'</span> 円<br>'
      + ok(sp[1], (sp[1]?'✓ ':'✗ ')+sp[0])
      + '<br>' + ok(!ins, ins?'✗ 社会保険に加入':'✓ 社会保険は扶養のまま')
      + '　' + ok(inc<=1600000, inc<=1600000?'✓ 所得税なし':'✗ 所得税あり');
    rows.push(['配偶者の控除', sp[0], sp[1], sp[2]]);
    rows.push(['本人の所得税', inc<=1600000 ? 'かかりません' : 'かかります', inc<=1600000]);
    rows.push(['社会保険', ins ? '自分で加入します' : '扶養のままです', !ins]);
    var h='<div class="sec-title">この年収だとどうなるか</div>';
    rows.forEach(function(r){{
      h+='<div class="card" style="cursor:default"><div class="t">'+r[0]+
         '</div><div class="d" style="color:'+(r[2]?'#3F6F69':'#D14757')+';font-weight:700">'+r[1]+'</div>'+
         (r[3]?'<div class="d" style="margin-top:4px">'+r[3]+'</div>':'')+'</div>';
    }});
    h+='<div class="note">世帯の手取り合計(目安): <strong>'+yen(net(inc))+' 円</strong>'+
       (ins?'（社会保険料の負担が発生しています）':'')+'</div>';
    // 働き損の区間を知らせる
    var best=net(inc), warn=0;
    for(var x=inc+10000;x<=inc+400000;x+=10000){{ if(net(x)<best){{ warn=x; break; }} }}
    if(warn) h+='<div class="note">📌 ここから少し増やすと、手取りが下がる区間に入ります。'+
       '増やすなら一気に超えたほうが有利です。</div>';
    V.innerHTML=h; draw(inc);
  }}
  S.addEventListener('input',update);
  HS.addEventListener('input',update);
  [B,H,ST].forEach(function(e){{e.addEventListener('change',update);}});
  update();
}})();
</script>""")
    parts.append(footer())
    return "".join(parts)


def build_article(a, articles=()):
    """解説記事ページ。制度でも比較でもない読み物を汎用に描く。
    data/articles.json に足すだけでページが増える(将来の税金まわりもここに置く)。"""
    parts = [head(f"{a['title']}｜{SITE_NAME}", a["desc"], f"/{a['id']}.html")]
    parts.append(f"""
<header class="site"><div class="wrap"><a class="logo" href="./index.html">{html.escape(SITE_NAME)}</a></div></header>
{site_nav()}
<div class="wrap body">
  <a class="back" href="./hikaku-furusato.html">← ふるさと納税の比較へ</a>
  {'<div class="pr">※本ページはプロモーションを含みます</div>' if a.get("pr", True) else ''}
  <h1 style="font-size:1.35rem;margin:.2em 0">{html.escape(a['title'])}</h1>
  <div class="s" style="margin:.2em 0 1em">最終更新: {html.escape(a.get('updated',''))}</div>
  <p>{html.escape(a['lead'])}</p>""")

    for s in a.get("sections", []):
        parts.append(f'<div class="sec-title">{html.escape(s["h"])}</div>')
        for para in s.get("p", []):
            parts.append(f"<p>{html.escape(para)}</p>")
        if s.get("list"):
            parts.append('<ul class="tips">')
            for it in s["list"]:
                parts.append(f"<li>{html.escape(it)}</li>")
            parts.append("</ul>")
        if s.get("note"):
            parts.append(f'<div class="note">📌 {html.escape(s["note"])}</div>')

    if a.get("faq"):
        parts.append('<div class="sec-title">よくある質問</div>')
        for q in a["faq"]:
            parts.append('<div class="card" style="cursor:default">'
                         f'<div class="t">{html.escape(q["q"])}</div>'
                         f'<div class="d" style="margin-top:6px">{html.escape(q["a"])}</div></div>')

    parts.append(f'<a class="cta" href="{html.escape(a.get("cta_href", "./hikaku-furusato.html"))}" '
                 'style="display:block;text-align:center">'
                 f'{html.escape(a.get("cta_text", "ふるさと納税の申し込み先をくらべる"))} →</a>')

    nxt = {x["id"]: x for x in articles}.get(a.get("next"))
    if nxt:
        parts.append('<div class="sec-title">あわせて読みたい</div>'
                     f'<a class="card" href="./{nxt["id"]}.html">'
                     f'<div class="t">{nxt.get("emoji", "")} {html.escape(nxt["title"])}</div>'
                     f'<div class="d">{html.escape(nxt["desc"][:70])}… →</div></a>')

    if a.get("official"):
        parts.append('<div class="sec-title">公式情報</div><ul class="tips">')
        for o in a["official"]:
            parts.append(f'<li><a href="{html.escape(o["url"])}" target="_blank" rel="noopener">'
                         f'{html.escape(o["name"])}</a></li>')
        parts.append("</ul>")

    parts.append('<div class="note">制度の内容や金額は変わることがあります。'
                 '実際の手続きの前に、必ず公式ページや各自治体の案内でご確認ください。'
                 'なお当サイトは個別の税務相談には応じられません。</div>')
    parts.append("</div>" + footer())
    return "".join(parts)


def hikaku_cards(pages, exclude=None):
    """比較ページ同士の相互リンク(カード)。"""
    out = []
    for p in pages:
        if p["id"] == exclude:
            continue
        out.append(f"""<a class="card" href="./{p['id']}.html">
  <div class="t">{html.escape(p.get('nav_title', p['title']))}</div>
  <div class="d">{html.escape(p['lead'][:60])}… →</div>
</a>""")
    return "".join(out)


def build_hikaku(pg, all_pages=()):
    """比較ページ(収益エンジン)。PR表記を明示し、公式情報へのリンクも併記する。"""
    parts = [head(f"{pg['title']}｜{SITE_NAME}", pg["lead"][:100], f"/{pg['id']}.html")]
    parts.append(f"""
<header class="site"><div class="wrap"><a class="logo" href="./index.html">{html.escape(SITE_NAME)}</a></div></header>
{site_nav()}
<div class="wrap">
  <a class="back" href="./index.html">← ホーム</a>
  <div class="pr">※本ページはプロモーションを含みます</div>
  <h1 style="font-size:1.35rem;margin:.2em 0">{html.escape(pg['title'])}</h1>
  <p>{html.escape(pg['lead'])}</p>

  <div class="sec-title">はじめかた(4ステップ)</div>
  <ul class="tips">""")
    for s in pg["howto"]:
        parts.append(f"<li>{html.escape(s)}</li>")
    parts.append("</ul>")
    # 比較ページに紐づく解説記事(あれば)。申し込み前に読ませたいものを先に置く。
    for a in (pg.get("_articles") or []):
        parts.append(f"""<a class="card" href="./{a['id']}.html">
  <div class="t">{a.get('emoji', '')} {html.escape(a['title'])}</div>
  <div class="d">{html.escape(a['desc'][:80])}… →</div>
</a>""")
    parts.append('<div class="sec-title">主要サイトの選び方</div>')

    for it in pg["items"]:
        parts.append(f"""<div class="card" style="cursor:default">
  <div class="t">{html.escape(it['name'])}</div>
  <div class="d" style="margin:6px 0 10px">{html.escape(it['point'])}</div>
  <ul class="tips" style="margin:0">""")
        for g in it["good"]:
            parts.append(f"<li>{html.escape(g)}</li>")
        parts.append("</ul><ul class=\"mis\" style=\"margin:0\">")
        for c in it["care"]:
            parts.append(f"<li>{html.escape(c)}</li>")
        parts.append("</ul>")
        if it.get("notice"):
            parts.append(f'<div class="note">📌 {html.escape(it["notice"])}</div>')
        url = it.get("aff_url") or it.get("official")
        if url:
            label = it.get("cta") or (f"{it['name']}を見る" if it.get("aff_url") else "公式サイトを見る")
            # ASPの計測用1x1ピクセルはアンカー内に置く必要がある
            pixel = (f'<img src="{html.escape(it["aff_pixel"])}" height="1" width="1" border="0" alt="">'
                     if it.get("aff_pixel") else "")
            parts.append(f'<a class="offbtn" href="{html.escape(url)}" target="_blank" '
                         f'rel="noopener sponsored nofollow">{pixel}{html.escape(label)}</a>')
        parts.append("</div>")

    parts.append('<div class="sec-title">子育て世帯の選び方のコツ</div><ul class="tips">')
    for t in pg["kosodate_tips"]:
        parts.append(f"<li>{html.escape(t)}</li>")
    parts.append("</ul>")
    parts.append(f'<div class="note">⚠️ {html.escape(pg["caution"])}</div>')
    if pg.get("official_ref"):
        parts.append(f'<a class="offbtn" href="{html.escape(pg["official_ref"])}" target="_blank" rel="noopener">🔗 公的機関の解説ページ</a>')
    others = hikaku_cards(all_pages, exclude=pg["id"])
    if others:
        parts.append('<div class="sec-title">ほかの見直しも</div>')
        parts.append(others)
    parts.append("</div>")
    # LinkSwitch は比較ページのみ(制度ページは広告を置かない方針)
    if VC_LINKSWITCH_PID:
        parts.append(f'<script>var vc_pid="{VC_LINKSWITCH_PID}";</script>'
                     '<script src="//aml.valuecommerce.com/vcdal.js" async></script>')
    parts.append(footer())
    return "".join(parts)


def main():
    global DISCLAIMER
    data = json.load(open(DATA, encoding="utf-8"))
    DISCLAIMER = data.get("disclaimer", "")
    # 読み物パートをマージ
    if os.path.exists(ENRICH):
        enrich = json.load(open(ENRICH, encoding="utf-8"))
        for p in data["programs"]:
            p["_enrich"] = enrich.get(p["id"])
    os.makedirs(SITE, exist_ok=True)
    # 比較ページ(収益)
    # 解説記事は比較ページより先に読む(比較ページ側に記事への導線を差し込むため)
    articles_path = os.path.join(ROOT, "data", "articles.json")
    arts = []
    if os.path.exists(articles_path):
        arts = json.load(open(articles_path, encoding="utf-8"))["articles"]
        data["_articles"] = arts

    hikaku_path = os.path.join(ROOT, "data", "hikaku.json")
    if os.path.exists(hikaku_path):
        hk = json.load(open(hikaku_path, encoding="utf-8"))
        data["_hikaku"] = hk["pages"]
        for pg in hk["pages"]:
            if pg["id"] == "hikaku-furusato":
                pg["_articles"] = arts
            with open(os.path.join(SITE, pg["id"] + ".html"), "w", encoding="utf-8") as f:
                f.write(build_hikaku(pg, hk["pages"]))
        print(f"  比較ページ: {len(hk['pages'])}本")

    with open(os.path.join(SITE, "kabe.html"), "w", encoding="utf-8") as f:
        f.write(build_kabe())
    print("  年収の壁シミュレーター: kabe.html")

    for a in arts:
        with open(os.path.join(SITE, a["id"] + ".html"), "w", encoding="utf-8") as f:
            f.write(build_article(a, arts))
    if arts:
        print(f"  解説記事: {len(arts)}本")

    # 自治体ページ(全国データが無いため手作業で調べた市独自の支援)
    cities_path = os.path.join(ROOT, "data", "cities.json")
    city_pages = []
    if os.path.exists(cities_path) and os.path.exists(IRYOHI):
        cj = json.load(open(cities_path, encoding="utf-8"))
        _iry = json.load(open(IRYOHI, encoding="utf-8"))["municipalities"]
        iry_map = {(m["pref"], m["city"]): m for m in _iry}
        _tk = json.load(open(TAIKI, encoding="utf-8"))["municipalities"] if os.path.exists(TAIKI) else []
        taiki_map = {(t["pref"], t["city"]): t for t in _tk}
        bp = {}
        for m in _iry:
            bp.setdefault(m["pref"], []).append(m)
        rank_map = {}
        for pref, lst in bp.items():
            for i, x in enumerate(sorted(lst, key=lambda x: (-x["rank_out"], x["limit_out"], x["copay_out"])), 1):
                rank_map[(x["pref"], x["city"])] = (i, len(lst))
        for c in cj["cities"]:
            with open(os.path.join(SITE, c["id"] + ".html"), "w", encoding="utf-8") as f:
                f.write(build_city(c, iry_map, taiki_map, rank_map))
            city_pages.append(c)
        # --- 全国データだけで作れる自治体ページを、規模の大きい順に自動生成する ---
        # 手作業の独自制度は無いが、医療費助成・待機児童の年齢別内訳・県内順位は
        # 一次データから出せる。競合が「自治体によります」で済ませている領域なので、
        # ロングテールの検索に対して意味のあるページになる。
        AUTO_N = 200
        have = {(c["pref"], c["city"]) for c in cj["cities"]}
        pool = [t for t in _tk
                if (t["pref"], t["city"]) in iry_map and (t["pref"], t["city"]) not in have]
        pool.sort(key=lambda t: -(t.get("apply") or 0))
        auto_ids = []
        for t in pool[:AUTO_N]:
            cid = f'chiiki-{t["pref"]}{t["city"]}'
            auto = {
                "id": cid, "pref": t["pref"], "city": t["city"],
                "lead": f'{t["pref"]}{t["city"]}の子ども医療費助成と保育園の状況を、'
                        'こども家庭庁の公表データからまとめました。'
                        '市区町村が独自に出している給付金は、下の公式サイト検索から確認できます。',
                "programs": [], "checked": "",
                "note": "このページは全国の公表データから自動で作成しています。"
                        "市区町村が独自に実施している給付金は含まれていません。",
            }
            with open(os.path.join(SITE, cid + ".html"), "w", encoding="utf-8") as f:
                f.write(build_city(auto, iry_map, taiki_map, rank_map))
            auto_ids.append(cid)
        data["_city_auto"] = auto_ids
        with open(os.path.join(SITE, "chiiki-list.html"), "w", encoding="utf-8") as f:
            f.write(build_city_auto_index(auto_ids))
        print(f"  自動生成の自治体ページ: {len(auto_ids)}件")

        idx = build_city_index(city_pages, iry_map, taiki_map, rank_map, "東京都", "tokyo23",
                               "東京23区の子育て支援をくらべる",
                               "東京23区は、東京都全域の制度(018サポートなど)が共通して使えるうえに、区ごとの独自支援があります。医療費助成・待機児童・区独自の制度をまとめて比べられます。")
        if idx:
            with open(os.path.join(SITE, "tokyo23.html"), "w", encoding="utf-8") as f:
                f.write(idx)
            city_pages_extra = ["tokyo23"]
        else:
            city_pages_extra = []
        data["_city_extra"] = city_pages_extra
        print(f"  自治体ページ: {len(city_pages)}件 + 一覧{len(city_pages_extra)}件")
    data["_cities"] = city_pages

    # 地域ページ
    if os.path.exists(IRYOHI):
        iry = json.load(open(IRYOHI, encoding="utf-8"))
        tk = json.load(open(TAIKI, encoding="utf-8")) if os.path.exists(TAIKI) else None
        with open(os.path.join(SITE, "chiiki.html"), "w", encoding="utf-8") as f:
            ip = json.load(open(IRYOHI_PREF, encoding="utf-8")) if os.path.exists(IRYOHI_PREF) else None
            f.write(build_chiiki(iry, data.get("_hikaku") or [], tk, ip, data.get("_cities") or []))
        if tk:
            print(f"  待機児童データ: {tk['count']}市区町村")
        print(f"  地域ページ: {iry['count']}市区町村")

    with open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as f:
        f.write(build_index(data))
    for p in data["programs"]:
        with open(os.path.join(SITE, p["id"] + ".html"), "w", encoding="utf-8") as f:
            f.write(build_program(p, data))
    with open(os.path.join(SITE, "shindan.html"), "w", encoding="utf-8") as f:
        f.write(build_shindan(data))
    with open(os.path.join(SITE, "ichiran.html"), "w", encoding="utf-8") as f:
        f.write(build_ichiran(data))
    with open(os.path.join(SITE, "policy.html"), "w", encoding="utf-8") as f:
        f.write(build_policy())

    if data.get("_hikaku"):
        with open(os.path.join(SITE, "kakei.html"), "w", encoding="utf-8") as f:
            f.write(build_kakei(data["_hikaku"]))

    # 独自ドメイン(GitHub Pages用)
    with open(os.path.join(SITE, "CNAME"), "w", encoding="utf-8") as f:
        f.write(DOMAIN + "\n")

    # sitemap.xml / robots.txt
    pages = ["/", "/shindan.html", "/ichiran.html", "/chiiki.html", "/kakei.html", "/policy.html"]
    pages += [f"/{c['id']}.html" for c in (data.get("_cities") or [])]
    pages += [f"/{x}.html" for x in (data.get("_city_extra") or [])]
    pages += [f"/{p['id']}.html" for p in data["programs"]]
    pages += [f"/{a['id']}.html" for a in (data.get("_articles") or [])]
    pages += ["/kabe.html"]
    pages += [f"/{x}.html" for x in (data.get("_city_auto") or [])]
    pages += ["/chiiki-list.html"]
    if os.path.exists(hikaku_path):
        pages += [f"/{pg['id']}.html" for pg in json.load(open(hikaku_path, encoding="utf-8"))["pages"]]
    # ページごとの最終更新日。data/lastmod.json に中身のハッシュと日付を持ち、
    # ハッシュが変わったページだけ日付を更新する。
    # 全ページに同じ固定日を入れると「更新されていないサイト」と読まれて再クロールが遅れ、
    # 逆に毎回ビルド日を入れると「毎日全ページ変わる」ことになり信用されない。
    lm_path = os.path.join(ROOT, "data", "lastmod.json")
    lastmod = json.load(open(lm_path, encoding="utf-8")) if os.path.exists(lm_path) else {}
    build_day = datetime.date.today().isoformat()
    changed = 0
    for u in pages:
        fp = os.path.join(SITE, "index.html" if u == "/" else u.lstrip("/"))
        if not os.path.exists(fp):
            continue
        h = hashlib.md5(open(fp, "rb").read()).hexdigest()
        if lastmod.get(u, {}).get("hash") != h:
            lastmod[u] = {"hash": h, "date": build_day}
            changed += 1
    with open(lm_path, "w", encoding="utf-8") as f:
        json.dump(lastmod, f, ensure_ascii=False, indent=0, sort_keys=True)
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in pages:
        d = lastmod.get(u, {}).get("date", build_day)
        sm.append(f"<url><loc>{BASE_URL}{u}</loc><lastmod>{d}</lastmod></url>")
    sm.append("</urlset>")
    with open(os.path.join(SITE, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(sm))
    with open(os.path.join(SITE, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\n\nSitemap: {BASE_URL}/sitemap.xml\n")

    print(f"ビルド完了: {len(data['programs'])}制度 + トップ + しんだん → {SITE}")
    print(f"  CNAME({DOMAIN}) / sitemap.xml({len(pages)}URL・更新{changed}件) / robots.txt")
    if not GA4_ID:
        print("  ※GA4未設定: build.py の GA4_ID に測定IDを入れると全ページに反映されます")


if __name__ == "__main__":
    main()
