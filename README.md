# 新生活セットアップ・ポータル

学生向けアパート入居者向け、ゼロサブスクリプション型 紹介リンク・ポータル。

## 構成

| ファイル | 役割 |
| --- | --- |
| `index.html` | エントリーポイント (モバイル最適化) |
| `style.css` | デザイン (スマホ→タブレット2カラム対応) |
| `app.js` | `config.json` をフェッチしてカード描画 |
| `config.json` | 掲載サービス・カテゴリーの一元管理 |
| `generate_qr.py` | チラシ印刷用 QR コード生成 (`--channel` で流入元タグ付与) |
| `flyer.html` | A4 印刷用チラシ (契約書類同封用) |
| `templates/onboarding_email.md` | 入居案内メール テンプレート |
| `templates/onboarding_line.md` | 入居案内 LINE テンプレート |
| `OPERATOR_GUIDE.md` | 運用ガイド (ハブ登録→埋込→オプトインの3ステップ) |
| `.github/workflows/deploy.yml` | GitHub Pages 自動デプロイ |

## ローカル動作確認

```powershell
cd C:\Claude\ALL\TenantPortal
python -m http.server 8000
```

ブラウザで http://localhost:8000/ を開く。スマホ実機で確認する場合は、PC の LAN 内 IP に置き換える (例: http://192.168.x.x:8000/)。

## GitHub Pages へのデプロイ

### 1. リポジトリ作成 & 初回 push

```powershell
cd C:\Claude\ALL\TenantPortal
git init -b main
git add .
git commit -m "Initial: tenant portal MVP"

# GitHub CLI でリポジトリ作成 (Public 想定)
gh repo create tenant-portal --public --source=. --remote=origin --push
```

`gh` 未導入の場合は、GitHub Web 上で空リポジトリを作って:

```powershell
git remote add origin https://github.com/<your-user>/tenant-portal.git
git push -u origin main
```

### 2. Pages を有効化

リポジトリの **Settings → Pages → Build and deployment** で `Source` を **GitHub Actions** に変更。`.github/workflows/deploy.yml` が初回 push で自動実行され、Pages にデプロイされる。

### 3. 公開 URL の確認

デプロイ完了後、URL は `https://<your-user>.github.io/tenant-portal/` で固定。`Actions` タブの最新ワークフロー成功ログ末尾にも URL が出力される。

### 4. 掲載内容の更新

`config.json` の `services` 配列を編集 → commit & push のみで反映 (HTML/JS の変更は不要)。

```powershell
git add config.json
git commit -m "Update services"
git push
```

数十秒〜数分でサイトが更新される。

## QR コード生成 (チラシ用)

```powershell
pip install "qrcode[pil]"
python generate_qr.py https://<your-user>.github.io/tenant-portal/
```

`qr_code.png` がカレントに出力される。チラシに貼って印刷。

## 自動化された代理店スキーム(3ステップ)

不動産オーナー向けの収益化運用は **OPERATOR_GUIDE.md** に集約しました。要点は以下:

1. **ハブ登録** — A8.net 等のアフィリエイトASP(無料) に登録し、1つのダッシュボードから全カテゴリの紹介URLを発行
2. **オンボーディング埋込** — 契約書類に `flyer.html` 印刷チラシを同封 / 入居案内メール・LINE に `templates/` のテンプレで案内
3. **オプトイン提示** — 「1回で完了します」「お申込みは任意です」と入居者メリットのみを提示

ポータルは `?src=qr/email/line/web` を読み取り、各サービスへの遷移URLに `utm_source/medium/campaign` を自動付与するため、ハブのレポートで流入チャネル別の成果を計測できます。

詳細手順・文言ガイドライン・収益レンジ目安は [OPERATOR_GUIDE.md](./OPERATOR_GUIDE.md) を参照。

## アフィリエイト URL への差し替え

`config.json` の各サービス `url` は、現状は公式サイトを指している。各事業者の紹介プログラム審査後に、発行された紹介 URL へ置き換える。

| サービス | 紹介プログラム例 |
| --- | --- |
| GMO とくとくBB 光 | A8.net / バリューコマース |
| 楽天モバイル / 楽天銀行 | 楽天アフィリエイト |
| Amazon Prime Student | Amazon アソシエイト |
| CLAS / subsclife | A8.net |
| 引越し侍 / SUUMO引越し | A8.net / afb |

差し替え後も `app.js` の HTML 生成は `rel="noopener noreferrer sponsored"` で sponsored 属性を自動付与するため、検索エンジンガイドラインに準拠。
