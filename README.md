# こそだて給付ナビ

子育て世帯が「もらえるお金」を、人生の場面から引けるガイドサイト。
https://kosodate-kyufu.com

## 構成

```
data/programs.json    制度データ(15制度・公式検証済み)
data/enrich.json      制度ごとの読み物(背景/解説/モデルケース/コツ/失敗/FAQ)
data/hikaku.json      比較ページ(収益導線)のデータ
data/iryohi_municipalities.json  全1,740市区町村の子ども医療費助成
build.py              静的サイトビルダー(標準ライブラリのみ)
pipeline/parse_iryohi.py  こども家庭庁PDF → 市区町村データ(手動更新用)
site/                 生成物(gitignore。CIで毎回生成)
docs/                 設計書・収益シミュレーター(非公開)
```

## ビルド

```bash
python build.py
```

`site/` に出力されます。CNAME・sitemap.xml・robots.txt も自動生成。

## デプロイ

`main` にpushすると GitHub Actions が自動でビルド&公開します。
毎月1日にも自動で再ビルドします。

## データ更新

### 子ども医療費助成(年1回・こども家庭庁の調査公表後)

```bash
pip install pypdf
python pipeline/parse_iryohi.py
```

新しい年度のPDF URLを `pipeline/parse_iryohi.py` の `PDF_URL` に設定してから実行。

### 制度データ

`data/programs.json` と `data/enrich.json` を編集。
**金額・条件は必ず公式ページで検証してから更新すること。**

## 設定

`build.py` 冒頭:

- `GA4_ID` … Google Analytics の測定ID(未設定ならタグを出力しない)
- `DOMAIN` … 独自ドメイン(CNAME・canonical・sitemapに反映)

## 方針

- **正確性が最優先。** 公的な金額・条件を扱うため、必ず出典リンクと更新日を併記する
- 制度ページには広告を詰め込まない。収益は比較ページで取る
- 比較ページには必ずPR表記を入れる
