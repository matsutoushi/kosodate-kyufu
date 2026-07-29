"""
こども医療費助成の【都道府県分】を作る。
出典: こども家庭庁「こどもに係る医療費の助成についての調査」別紙2(都道府県用)
  → data/iryohi_prefectures.json

市区町村の助成に都道府県の助成が上乗せされる構造なので、両方見えると実態がわかる。
"""
import json
import os
import re
import urllib.request

PDF_URL = ("https://www.cfa.go.jp/assets/contents/node/basic_page/field_ref_resources/"
           "6a9b8926-411c-4044-81aa-d8c26b21aaf5/e6ac7b84/"
           "20251224policies-boshihoken-kodomoiryouhityousa-r7-02.pdf")
SOURCE_PAGE = "https://www.cfa.go.jp/policies/boshihoken/kodomoiryouhityousa-r7"
AS_OF = "令和7年4月1日時点"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "iryohi_prefectures.json")
CACHE = os.path.join(ROOT, "data", "_cache_iryohi_pref.pdf")

PREFS = ("北海道|青森県|岩手県|宮城県|秋田県|山形県|福島県|茨城県|栃木県|群馬県|埼玉県|千葉県|東京都|"
         "神奈川県|新潟県|富山県|石川県|福井県|山梨県|長野県|岐阜県|静岡県|愛知県|三重県|滋賀県|京都府|"
         "大阪府|兵庫県|奈良県|和歌山県|鳥取県|島根県|岡山県|広島県|山口県|徳島県|香川県|愛媛県|高知県|"
         "福岡県|佐賀県|長崎県|熊本県|大分県|宮崎県|鹿児島県|沖縄県")

AGE = r"(就学前|\d+歳年度末|\d+歳未満|ー|－|-)"
ROW = re.compile(rf"({PREFS})\s*{AGE}\s*{AGE}\s*([有無ー－-])\s*([有無ー－-])\s*([有無ー－-])\s*([有無ー－-])")


def fetch():
    if os.path.exists(CACHE) and os.path.getsize(CACHE) > 100000:
        return
    req = urllib.request.Request(PDF_URL, headers={"User-Agent": "shien-navi/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
    open(CACHE, "wb").write(raw)


def flag(v):
    """有/無/未実施(ー) を返す。都道府県によっては制度自体が無い。"""
    if v == "有":
        return True
    if v == "無":
        return False
    return None


def main():
    import pypdf

    fetch()
    text = "\n".join((p.extract_text() or "") for p in pypdf.PdfReader(CACHE).pages)

    rows, seen = [], set()
    for m in ROW.finditer(text):
        pref, a_out, a_in, l_out, l_in, p_out, p_in = m.groups()
        if pref in seen:
            continue
        seen.add(pref)
        none = a_out in ("ー", "－", "-")
        rows.append({
            "pref": pref,
            "has_program": not none,
            "age_out": None if none else a_out,
            "age_in": None if none else a_in,
            "limit_out": flag(l_out),
            "copay_out": flag(p_out),
        })

    payload = {
        "source": "こども家庭庁「こどもに係る医療費の助成についての調査」別紙2(都道府県用)",
        "source_url": SOURCE_PAGE,
        "as_of": AS_OF,
        "count": len(rows),
        "prefectures": rows,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    print(f"取得: {len(rows)} 都道府県")
    noprog = [r["pref"] for r in rows if not r["has_program"]]
    if noprog:
        print("  県独自の助成なし:", noprog)
    import collections
    c = collections.Counter(r["age_out"] for r in rows if r["age_out"])
    print("  通院の対象年齢:", dict(c))
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
