"""
支援制度データ取得パイプライン(東京都オープンデータ / ユニバーサルメニュー標準)
- 東京都CKANカタログから「支援制度（給付金）情報」データセットを全件検索
- 各自治体のCSV(85列・共通スキーマ)を取得・正規化してJSONに統合
標準ライブラリのみ(pip不要)。
"""
import csv
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

CKAN = "https://catalog.data.metro.tokyo.lg.jp/api/3/action"
STD_TITLE = "支援制度（給付金）情報"  # ユニバーサルメニュー推奨データセット
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# 抽出したいキー項目(CSVヘッダ名の部分一致で拾う)。共通スキーマだが表記ゆれに備える。
FIELD_MAP = {
    "municipality": ["地方公共団体の名称"],
    "title": ["タイトル（制度名）", "タイトル"],
    "subtitle": ["サブタイトル（通称名）", "サブタイトル"],
    "kind": ["支援制度種別"],
    "target": ["対象者"],
    "purpose": ["用途・対象費"],
    "summary": ["制度概要"],
    "content": ["内容"],
    "amount": ["給付金額"],
    "subsidy_rate": ["補助率"],
    "start": ["受付開始日"],
    "end": ["受付終了日"],
    "method": ["利用・申請方法"],
    "keyword": ["キーワード"],
    "lifestage": ["【人生の制度】ライフステージ分類", "ライフステージ分類"],
    "url": ["URL"],
    "detail_url": ["申請方法URL", "詳細参照先"],
    "contact": ["問い合わせ先", "連絡先名称"],
    "tel": ["連絡先電話番号"],
    "published": ["公開日"],
}


def ckan(action, **params):
    url = CKAN + "/" + action + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r)


def find_datasets():
    """標準タイトルで全データセットをページング取得。"""
    rows, start = [], 0
    while True:
        d = ckan("package_search", q=STD_TITLE, rows=100, start=start)
        res = d["result"]
        got = res.get("results", [])
        rows += got
        total = res.get("count", 0)
        print(f"  package_search start={start} 取得={len(got)} / total={total}")
        if not got or start + len(got) >= total:
            break
        start += len(got)
        time.sleep(0.3)
    return rows


def pick_csv(ds):
    csvs = [r.get("url", "") for r in ds.get("resources", []) if (r.get("url") or "").lower().endswith(".csv")]
    for u in csvs:
        if "support_system" in u.lower():
            return u
    return csvs[0] if csvs else None


def decode(raw):
    for enc in ("utf-8-sig", "cp932", "utf-8"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", "replace")


def col_index(header):
    """ヘッダ名 → 出力キー のインデックスを部分一致で構築。"""
    idx = {}
    for out_key, names in FIELD_MAP.items():
        for i, h in enumerate(header):
            hn = (h or "").strip()
            if any(n in hn for n in names):
                idx[out_key] = i
                break
    return idx


def parse_csv(url):
    req = urllib.request.Request(url, headers={"User-Agent": "shien-navi/0.1"})
    with urllib.request.urlopen(req, timeout=45) as r:
        raw = r.read()
    rows = list(csv.reader(io.StringIO(decode(raw))))
    if not rows:
        return []
    header = rows[0]
    idx = col_index(header)
    out = []
    for row in rows[1:]:
        if not any(c.strip() for c in row):
            continue
        rec = {}
        for k, i in idx.items():
            if i < len(row):
                v = (row[i] or "").strip()
                if v:
                    rec[k] = v
        if rec.get("title"):
            out.append(rec)
    return out


def main():
    print("[1] 標準タイトルでデータセット検索…")
    datasets = find_datasets()
    print(f"  → {len(datasets)} データセット")

    print("[2] 各CSVを取得・正規化…")
    all_recs, municipalities, failed = [], set(), []
    for ds in datasets:
        url = pick_csv(ds)
        if not url:
            continue
        try:
            recs = parse_csv(url)
        except Exception as e:
            failed.append((url, str(e)[:60]))
            continue
        for rec in recs:
            rec["source_csv"] = url
            m = rec.get("municipality")
            if m:
                municipalities.add(m)
        all_recs += recs
        print(f"    {url.split('/')[-2]:20s} {len(recs):4d}件")
        time.sleep(0.2)

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, "support_programs.json")
    payload = {
        "source": "東京都オープンデータ(ユニバーサルメニュー標準)",
        "catalog": CKAN,
        "count": len(all_recs),
        "municipalities": sorted(municipalities),
        "records": all_recs,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    print("\n=== 結果 ===")
    print(f"  制度件数: {len(all_recs)}")
    print(f"  自治体数: {len(municipalities)}")
    print(f"  失敗: {len(failed)}")
    if failed:
        for u, e in failed[:5]:
            print(f"    - {u} : {e}")
    print(f"  出力: {out_path}")


if __name__ == "__main__":
    main()
