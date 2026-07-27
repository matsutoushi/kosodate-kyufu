"""
静的サイトビルダー: data/programs.json → site/*.html
「子育て世帯がもらえるお金」ガイド(作業名)。モバイルファースト・信頼重視のクリーンなデザイン。
標準ライブラリのみ。python build.py で site/ に出力。
"""
import html
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data", "programs.json")
ENRICH = os.path.join(ROOT, "data", "enrich.json")
IRYOHI = os.path.join(ROOT, "data", "iryohi_municipalities.json")
SITE = os.path.join(ROOT, "site")

SITE_NAME = "こそだて給付ナビ"
TAGLINE = "子育て世帯が“もらえるお金”を、ムダなく受け取るための地図"
DOMAIN = "kosodate-kyufu.com"
BASE_URL = f"https://{DOMAIN}"
GA4_ID = "G-ZW9ZH2FCPS"  # GA4測定ID。ここ1箇所で全ページに反映される
GSC_TOKEN = "q0qAeAIxlo6jsG2oXXGQfxLfMg-FL-Gf--5B3YYFuDQ"  # Search Console 所有権確認
VC_LINKSWITCH_PID = "892667160"  # バリューコマース LinkSwitch(通常リンクを自動でアフィリエイト化)
VC_SID = "3776805"

# 制度ページから、文脈の合う「家計を軽くする」ページへの導線。
# 押し売りにならないよう、各ページ1本だけ・関連の強いものに限る。
RELATED = {
    "jido-teate": ("hikaku-furusato", "児童手当が入る月に、ふるさと納税の準備を"),
    "ninpu-shien-kyufu": ("hikaku-furusato", "おむつ・日用品はふるさと納税でも備えられます"),
    "shussan-ichijikin": ("hikaku-card", "出産費用の支払いも、ポイントを取りこぼさずに"),
    "shussan-teate": ("hikaku-sim", "収入が減る産休・育休こそ、固定費の見直しを"),
    "ikuji-kyugyo-kyufu": ("hikaku-sim", "育休で収入が下がる時期の固定費対策"),
    "hoiku-mushouka": ("hikaku-kyozai", "保育料が浮いた分を、学びに回すなら"),
    "kodomo-iryohi": ("hikaku-denki", "医療費以外でも、毎月の固定費は下げられます"),
    "ninpu-kenshin": ("hikaku-denki", "在宅時間が増える妊娠中は、光熱費の見直しも"),
    "jido-fuyo-teate": ("hikaku-sim", "毎月の固定費を下げると、手当以上に効くことも"),
    "hitorioya-iryohi": ("hikaku-denki", "電気・ガスの見直しで、毎月の負担を軽く"),
    "koko-shushi-kin": ("hikaku-kyozai", "授業料以外にかかる学びの費用は"),
    "koko-shogaku-kyufu": ("hikaku-kyozai", "教材費の負担を抑える選択肢"),
    "shugaku-enjo": ("hikaku-kyozai", "家庭学習の費用を抑えるなら"),
    "tokubetsu-jido-fuyo": ("hikaku-denki", "毎月の固定費を下げる方法も"),
    "shogaiji-fukushi": ("hikaku-sim", "通信費の見直しで、毎月の負担を軽く"),
}


def related_card(prog_id, hikaku_pages):
    """制度ページ下部の関連導線(1本だけ)。"""
    rel = RELATED.get(prog_id)
    if not rel:
        return ""
    hid, lead = rel
    pg = next((p for p in hikaku_pages if p["id"] == hid), None)
    if not pg:
        return ""
    return f"""<div class="sec-title">もらうだけでなく、減らす</div>
<a class="card" href="./{hid}.html">
  <div class="t">{pg.get('emoji','')} {html.escape(pg.get('nav_title', pg['title']))}</div>
  <div class="s">{html.escape(lead)}</div>
  <div class="d">家計を軽くする方法を整理しました →</div>
</a>"""


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
"""

def footer():
    return f"""
<div class="wrap">
  <div class="disc">{html.escape(DISCLAIMER)}<br>
  ※本サイトは制度紹介のための情報提供であり、申請の可否・金額を保証するものではありません。最新・正確な情報は各公式ページと市区町村でご確認ください。</div>
</div>
<footer><div class="wrap">
  {html.escape(SITE_NAME)} ／ <a href="./index.html">ホーム</a> ・ <a href="./shindan.html">もらえるお金しんだん</a> ・ <a href="./chiiki.html">地域別で調べる</a><br>
  <a href="./policy.html">プライバシーポリシー・免責事項</a><br>
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
<div class="wrap">
  <div class="hero">
    <h1>知らないと損する、<br>子育ての「もらえるお金」</h1>
    <p>制度はたくさんあるのに、案内は来ません。<br>あなたが受け取れるお金を、いっしょに確認しましょう。</p>
    <a class="cta" href="./shindan.html">▶ もらえるお金を30秒でしんだん</a>
  </div>

  <a class="card" href="./chiiki.html" style="background:linear-gradient(135deg,#fff6f0,#f2faf8)">
    <div class="t">📍 あなたの街は何歳まで医療費が無料?</div>
    <div class="s">全国1,740市区町村を検索できます</div>
    <div class="d">子ども医療費助成は自治体の制度。住む場所で驚くほど違います →</div>
  </a>

  <div class="sec-title">場面から探す</div>
  <div class="cats">""")
    for c in cats:
        parts.append(f'<a class="cat" href="#{c["id"]}"><div class="emoji">{c["emoji"]}</div><div class="lb">{html.escape(c["label"])}</div></a>')
    parts.append("</div>")

    for c in cats:
        cprogs = [p for p in progs if p["category"] == c["id"]]
        if not cprogs:
            continue
        parts.append(f'<div class="sec-title" id="{c["id"]}">{c["emoji"]} {html.escape(c["label"])}</div>')
        for p in cprogs:
            parts.append(f"""<a class="card" href="./{p['id']}.html">
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
    parts.append("</div>")
    parts.append(footer())
    return "".join(parts)


def build_program(p, data):
    parts = [head(f"{p['title']}｜{SITE_NAME}", p["summary"][:100], f"/{p['id']}.html")]
    parts.append(f"""
<header class="site"><div class="wrap"><a class="logo" href="./index.html">{html.escape(SITE_NAME)}</a></div></header>
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
    parts.append(related_card(p["id"], data.get("_hikaku") or []))
    parts.append("</div>")
    parts.append(footer())
    return "".join(parts)


def build_shindan(data):
    progs = data["programs"]
    hikaku_pages = data.get("_hikaku") or []
    # 簡易チェック: 状況にチェック → 該当しうる制度を表示(クライアントサイド)
    checks = [
        ("pregnant", "いま妊娠中／妊娠を予定している", ["ninpu-shien-kyufu", "ninpu-kenshin", "shussan-ichijikin", "shussan-teate"]),
        ("company", "会社員・公務員で産休・育休を取る(取った)", ["shussan-teate", "ikuji-kyugyo-kyufu"]),
        ("baby", "0〜2歳／未就学の子どもがいる", ["jido-teate", "kodomo-iryohi", "hoiku-mushouka"]),
        ("shougaku", "小・中学生の子どもがいる", ["jido-teate", "shugaku-enjo", "kodomo-iryohi"]),
        ("koukou", "高校生年代の子どもがいる", ["jido-teate", "koko-shushi-kin", "koko-shogaku-kyufu"]),
        ("single", "ひとり親家庭である", ["jido-fuyo-teate", "hitorioya-iryohi", "kodomo-iryohi"]),
        ("shogai", "障害のある子どもを育てている", ["tokubetsu-jido-fuyo", "shogaiji-fukushi"]),
    ]
    title_map = {p["id"]: p["title"] for p in progs}
    import json as _j
    parts = [head(f"もらえるお金しんだん｜{SITE_NAME}", "かんたんな質問で、あなたが受け取れる可能性のある子育て支援制度がわかります。", "/shindan.html")]
    parts.append(f"""
<header class="site"><div class="wrap"><a class="logo" href="./index.html">{html.escape(SITE_NAME)}</a></div></header>
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
  hit.forEach(id=>{{ h += '<a class="card" href="./'+id+'.html"><div class="t">'+TITLES[id]+'</div><div class="d">タップで詳細と申請方法へ →</div></a>'; }});
  h += '<div class="note">※チェック内容から機械的に表示しています。実際の対象可否・金額は各公式ページと市区町村でご確認ください。</div>';
  r.innerHTML = h;
}}
boxes.forEach(b=>b.addEventListener('change',render));
</script>""")
    parts.append(footer())
    return "".join(parts)


def build_chiiki(iry, hikaku_pages=()):
    """全市区町村の子ども医療費助成を検索できるページ。地域差を可視化する目玉。"""
    import json as _j
    ms = iry["municipalities"]
    total = len(ms)
    n18 = sum(1 for m in ms if m["rank_out"] >= 18)
    nolimit = sum(1 for m in ms if not m["limit_out"])
    nocopay = sum(1 for m in ms if not m["copay_out"])
    top = [m for m in ms if m["rank_out"] >= 20]
    top.sort(key=lambda m: -m["rank_out"])
    low = [m for m in ms if m["rank_out"] <= 12]

    parts = [head(f"あなたの市区町村の子ども医療費助成｜{SITE_NAME}",
                  f"全国{total}市区町村の子ども医療費助成(対象年齢・所得制限・自己負担)を検索できます。住む場所で驚くほど違います。", "/chiiki.html")]
    parts.append(f"""
<header class="site"><div class="wrap"><a class="logo" href="./index.html">{html.escape(SITE_NAME)}</a></div></header>
<div class="wrap">
  <a class="back" href="./index.html">← ホーム</a>
  <h1 style="font-size:1.35rem;margin:.2em 0">子どもの医療費、あなたの街は何歳まで?</h1>
  <p style="color:var(--sub);font-size:.92rem">子ども医療費助成は<strong>国ではなく自治体の制度</strong>。だから住む場所で大きく違います。
  全国{total:,}市区町村を検索できます。</p>

  <div class="stat">
    <div><div class="v">{n18:,}</div><div class="l">18歳年度末まで<br>助成(通院)</div></div>
    <div><div class="v">{nolimit:,}</div><div class="l">所得制限なし</div></div>
    <div><div class="v">{nocopay:,}</div><div class="l">自己負担なし</div></div>
  </div>

  <div class="sec-title">市区町村を検索</div>
  <input class="search" id="q" type="search" placeholder="例: 世田谷区／札幌市／京丹後市" autocomplete="off">
  <div id="mres"></div>

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

  <div class="sec-title">住む場所は変えられなくても</div>
  <p style="color:var(--sub);font-size:.92rem">医療費の助成額は自治体が決めることなので、自分では変えられません。
  でも、毎月の固定費は自分で下げられます。浮いたお金は、助成の差を埋めるくらいの効果になることもあります。</p>
  {hikaku_cards([p for p in hikaku_pages if p["id"] in ("hikaku-denki", "hikaku-sim", "hikaku-furusato")])}
</div>
<script>
const M = {_j.dumps([[m["pref"], m["city"], m["age_out"], m["age_in"], m["limit_out"], m["copay_out"]] for m in ms], ensure_ascii=False)};
const q = document.getElementById('q'), out = document.getElementById('mres');
function draw(){{
  const v = q.value.trim();
  if(!v){{ out.innerHTML=''; return; }}
  const hits = M.filter(r => (r[0]+r[1]).includes(v)).slice(0,40);
  if(!hits.length){{ out.innerHTML='<div class="note">見つかりませんでした。市区町村名の一部で試してください(例:世田谷)。</div>'; return; }}
  out.innerHTML = hits.map(r =>
    '<div class="mrow"><div class="n">'+r[0]+' '+r[1]+'</div>'+
    '<div class="meta">通院 <strong>'+r[2]+'</strong>まで ／ 入院 <strong>'+r[3]+'</strong>まで</div>'+
    '<div style="margin-top:6px">'+
      (r[4]?'<span class="pill p-warn">所得制限あり</span>':'<span class="pill p-good">所得制限なし</span>')+
      (r[5]?'<span class="pill p-warn">自己負担あり</span>':'<span class="pill p-good">自己負担なし</span>')+
    '</div></div>').join('');
}}
q.addEventListener('input', draw);
</script>""")
    parts.append(footer())
    return "".join(parts)


def build_policy():
    """プライバシーポリシー・免責事項。GA4のCookie利用とアフィリエイト表記のために必要。"""
    parts = [head(f"プライバシーポリシー・免責事項｜{SITE_NAME}",
                  f"{SITE_NAME}のプライバシーポリシーおよび免責事項です。", "/policy.html")]
    parts.append(f"""
<header class="site"><div class="wrap"><a class="logo" href="./index.html">{html.escape(SITE_NAME)}</a></div></header>
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

  <p style="font-size:.78rem;color:#a99;margin-top:20px">制定日: 2026年7月25日</p>
</div>""")
    parts.append(footer())
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
<div class="wrap">
  <a class="back" href="./index.html">← ホーム</a>
  <div class="pr">※本ページはプロモーションを含みます</div>
  <h1 style="font-size:1.35rem;margin:.2em 0">{html.escape(pg['title'])}</h1>
  <p>{html.escape(pg['lead'])}</p>

  <div class="sec-title">はじめかた(4ステップ)</div>
  <ul class="tips">""")
    for s in pg["howto"]:
        parts.append(f"<li>{html.escape(s)}</li>")
    parts.append('</ul><div class="sec-title">主要サイトの選び方</div>')

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
    hikaku_path = os.path.join(ROOT, "data", "hikaku.json")
    if os.path.exists(hikaku_path):
        hk = json.load(open(hikaku_path, encoding="utf-8"))
        data["_hikaku"] = hk["pages"]
        for pg in hk["pages"]:
            with open(os.path.join(SITE, pg["id"] + ".html"), "w", encoding="utf-8") as f:
                f.write(build_hikaku(pg, hk["pages"]))
        print(f"  比較ページ: {len(hk['pages'])}本")
    # 地域ページ
    if os.path.exists(IRYOHI):
        iry = json.load(open(IRYOHI, encoding="utf-8"))
        with open(os.path.join(SITE, "chiiki.html"), "w", encoding="utf-8") as f:
            f.write(build_chiiki(iry, data.get("_hikaku") or []))
        print(f"  地域ページ: {iry['count']}市区町村")

    with open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as f:
        f.write(build_index(data))
    for p in data["programs"]:
        with open(os.path.join(SITE, p["id"] + ".html"), "w", encoding="utf-8") as f:
            f.write(build_program(p, data))
    with open(os.path.join(SITE, "shindan.html"), "w", encoding="utf-8") as f:
        f.write(build_shindan(data))
    with open(os.path.join(SITE, "policy.html"), "w", encoding="utf-8") as f:
        f.write(build_policy())

    # 独自ドメイン(GitHub Pages用)
    with open(os.path.join(SITE, "CNAME"), "w", encoding="utf-8") as f:
        f.write(DOMAIN + "\n")

    # sitemap.xml / robots.txt
    pages = ["/", "/shindan.html", "/chiiki.html", "/policy.html"]
    pages += [f"/{p['id']}.html" for p in data["programs"]]
    if os.path.exists(hikaku_path):
        pages += [f"/{pg['id']}.html" for pg in json.load(open(hikaku_path, encoding="utf-8"))["pages"]]
    today = data.get("updated", "")
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in pages:
        sm.append(f"<url><loc>{BASE_URL}{u}</loc>" + (f"<lastmod>{today}</lastmod>" if today else "") + "</url>")
    sm.append("</urlset>")
    with open(os.path.join(SITE, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(sm))
    with open(os.path.join(SITE, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\n\nSitemap: {BASE_URL}/sitemap.xml\n")

    print(f"ビルド完了: {len(data['programs'])}制度 + トップ + しんだん → {SITE}")
    print(f"  CNAME({DOMAIN}) / sitemap.xml({len(pages)}URL) / robots.txt")
    if not GA4_ID:
        print("  ※GA4未設定: build.py の GA4_ID に測定IDを入れると全ページに反映されます")


if __name__ == "__main__":
    main()
