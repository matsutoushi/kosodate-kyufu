"""
保育所等の待機児童数(市区町村別)を作る。
出典: こども家庭庁「保育所等関連状況取りまとめ(令和7年4月1日)」
      (参考)定員・申込者の状況 xlsx
  → data/taiki_municipalities.json

年齢別に取れるのが重要。育休明けの1歳児がどれだけ入りにくいかが分かる。
"""
import json
import os
import urllib.request

XLSX_URL = ("https://www.cfa.go.jp/assets/contents/node/basic_page/field_ref_resources/"
            "b0a8057b-34bf-4c20-84fb-ae592708ca9b/1aa96453/"
            "20250828_policies_hoiku_torimatome_r7_04.xlsx")
SOURCE_PAGE = "https://www.cfa.go.jp/policies/hoiku/torimatome/r7"
AS_OF = "令和7年4月1日時点"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "taiki_municipalities.json")
CACHE = os.path.join(ROOT, "data", "_cache_taiki.xlsx")

# 列位置(0始まり)。ヘッダ構造は上記xlsxの「申込者の状況」シート。
C_PREF, C_CITY = 2, 3
C_APPLY, C_WAIT = 4, 15
C_WAIT_AGE = {"0": 27, "1": 39, "2": 51, "3+": 63}


def fetch():
    if os.path.exists(CACHE) and os.path.getsize(CACHE) > 500000:
        return
    req = urllib.request.Request(XLSX_URL, headers={"User-Agent": "shien-navi/0.1"})
    with urllib.request.urlopen(req, timeout=90) as r:
        raw = r.read()
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    open(CACHE, "wb").write(raw)


def num(v):
    if v is None or v == "":
        return 0
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def main():
    import openpyxl

    fetch()
    wb = openpyxl.load_workbook(CACHE, read_only=True, data_only=True)
    ws = wb["申込者の状況"]

    rows = []
    for row in ws.iter_rows(min_row=10, values_only=True):
        if len(row) <= C_WAIT:
            continue
        pref, city = row[C_PREF], row[C_CITY]
        if not pref or not city:
            continue
        pref, city = str(pref).strip(), str(city).strip()
        if pref in ("都道府県", "合計") or city in ("市区町村",):
            continue
        rows.append({
            "pref": pref,
            "city": city,
            "apply": num(row[C_APPLY]),
            "wait": num(row[C_WAIT]),
            "wait_age": {k: num(row[i]) for k, i in C_WAIT_AGE.items() if i < len(row)},
        })

    payload = {
        "source": "こども家庭庁「保育所等関連状況取りまとめ」(参考)定員・申込者の状況",
        "source_url": SOURCE_PAGE,
        "as_of": AS_OF,
        "count": len(rows),
        "municipalities": rows,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)

    total_wait = sum(r["wait"] for r in rows)
    zero = sum(1 for r in rows if r["wait"] == 0)
    print(f"取得: {len(rows)} 市区町村")
    print(f"  待機児童 合計: {total_wait:,}人")
    print(f"  待機児童ゼロの自治体: {zero} ({zero/len(rows)*100:.0f}%)")
    print("  年齢別合計:", {k: sum(r['wait_age'].get(k, 0) for r in rows) for k in C_WAIT_AGE})
    top = sorted(rows, key=lambda r: -r["wait"])[:10]
    print("  待機児童が多い自治体:")
    for r in top:
        print(f"    {r['pref']}{r['city']}: {r['wait']}人")
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
