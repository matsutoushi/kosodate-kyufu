"""
こども医療費助成の全市区町村データを作る。
出典: こども家庭庁「こどもに係る医療費の助成についての調査」別紙3(市区町村用)PDF
  → data/iryohi_municipalities.json

列: 都道府県 / 市区町村 / 対象年齢(通院・入院) / 所得制限(通院・入院) / 一部自己負担(通院・入院)
"""
import json
import os
import re
import urllib.request

PDF_URL = ("https://www.cfa.go.jp/assets/contents/node/basic_page/field_ref_resources/"
           "6a9b8926-411c-4044-81aa-d8c26b21aaf5/12ae0d40/"
           "20251224policies-boshihoken-kodomoiryouhityousa-r7-03.pdf")
SOURCE_PAGE = "https://www.cfa.go.jp/policies/boshihoken/kodomoiryouhityousa-r7"
SURVEY_DATE = "令和7年4月1日時点"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "iryohi_municipalities.json")
CACHE = os.path.join(ROOT, "data", "_cache_iryohi.pdf")

# 「北海道 1 札幌市 18歳年度末 18歳年度末 有 有 有 有」
ROW = re.compile(
    r"(北海道|青森県|岩手県|宮城県|秋田県|山形県|福島県|茨城県|栃木県|群馬県|埼玉県|千葉県|東京都|"
    r"神奈川県|新潟県|富山県|石川県|福井県|山梨県|長野県|岐阜県|静岡県|愛知県|三重県|滋賀県|京都府|"
    r"大阪府|兵庫県|奈良県|和歌山県|鳥取県|島根県|岡山県|広島県|山口県|徳島県|香川県|愛媛県|高知県|"
    r"福岡県|佐賀県|長崎県|熊本県|大分県|宮崎県|鹿児島県|沖縄県)"
    r"\s*(\d+)\s*([^\s\d]+?)\s*"
    r"(就学前|\d+歳年度末|\d+歳|その他)\s*"
    r"(就学前|\d+歳年度末|\d+歳|その他)\s*"
    r"(有|無)\s*(有|無)\s*(有|無)\s*(有|無)"
)


def fetch_pdf():
    if os.path.exists(CACHE) and os.path.getsize(CACHE) > 100000:
        return open(CACHE, "rb").read()
    req = urllib.request.Request(PDF_URL, headers={"User-Agent": "shien-navi/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    open(CACHE, "wb").write(raw)
    return raw


def age_rank(a):
    """並べ替え・比較用に年齢を数値化(手厚い順の判定に使う)。"""
    if "就学前" in a:
        return 6
    m = re.match(r"(\d+)歳", a)
    return int(m.group(1)) if m else 0


def main():
    import pypdf
    import io

    fetch_pdf()
    reader = pypdf.PdfReader(CACHE)
    text = "\n".join((p.extract_text() or "") for p in reader.pages)

    rows, seen = [], set()
    for m in ROW.finditer(text):
        pref, no, city, age_out, age_in, lim_out, lim_in, pay_out, pay_in = m.groups()
        # 注記記号(※)が名前に混ざる自治体があるので落とす(他データと突合するため)
        city = city.replace("※", "").strip()
        key = (pref, city)
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "pref": pref,
            "city": city,
            "age_out": age_out,          # 通院の対象年齢
            "age_in": age_in,            # 入院の対象年齢
            "limit_out": lim_out == "有",  # 所得制限(通院)
            "limit_in": lim_in == "有",
            "copay_out": pay_out == "有",  # 一部自己負担(通院)
            "copay_in": pay_in == "有",
            "rank_out": age_rank(age_out),
        })

    payload = {
        "source": "こども家庭庁「こどもに係る医療費の助成についての調査」別紙3(市区町村用)",
        "source_url": SOURCE_PAGE,
        "as_of": SURVEY_DATE,
        "count": len(rows),
        "municipalities": rows,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)

    # サマリ
    prefs = {}
    for r in rows:
        prefs.setdefault(r["pref"], 0)
        prefs[r["pref"]] += 1
    print(f"取得: {len(rows)} 市区町村 / {len(prefs)} 都道府県")
    import collections
    c = collections.Counter(r["age_out"] for r in rows)
    print("通院の対象年齢 内訳:")
    for k, v in c.most_common():
        print(f"  {k}: {v}")
    print(f"所得制限あり(通院): {sum(1 for r in rows if r['limit_out'])}")
    print(f"一部負担あり(通院): {sum(1 for r in rows if r['copay_out'])}")
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
