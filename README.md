# 入居者専用・生活支援ポータル

学生向けアパート(4部屋)の入居者向け、ゼロサブスクリプション型 生活支援ポータル。
**入居時の手続きから、在学中の暮らし、就活、卒業時の引越しまで** をワンページでカバーする LTV(ライフタイムバリュー)型構成。

🌐 **公開URL: https://yokisecure-hub.github.io/shingakusei-portal/**

📘 **はじめての方は [BEGINNER_MANUAL.md](./BEGINNER_MANUAL.md) を最初に読んでください**(IT・アフィリエイト初心者向け、A8.net登録から最初の報酬まで全手順)

## 構成

| ファイル | 役割 |
| --- | --- |
| `index.html` | エントリーポイント (モバイル最適化) |
| `style.css` | デザイン (スマホ→タブレット2カラム対応) |
| `app.js` | `config.json` をフェッチしてカード描画 / `?src=` を utm に変換 |
| `config.json` | 掲載サービス・カテゴリーの一元管理 |
| `generate_qr.py` | QR生成 (`--channel qr/poster/email/line/web`) |
| `flyer.html` | A4 印刷用チラシ (契約書類同封用 / `?src=qr`) |
| `flyer_room.html` | A4 部屋常設ポスター (ブレーカー横/掲示板 / `?src=poster`) |
| `templates/onboarding_email.md` | 入居案内メール テンプレート |
| `templates/onboarding_line.md` | 入居案内 LINE テンプレート |
| `BEGINNER_MANUAL.md` | 完全初心者向けマニュアル (A8.net登録〜報酬振込まで全手順) |
| `OPERATOR_GUIDE.md` | 運用ガイド (A8.net 主軸 + LTV最大化・熟達者向け) |
| `.github/workflows/deploy.yml` | GitHub Pages 自動デプロイ |

## ローカル動作確認

```powershell
cd C:\Claude\ALL\TenantPortal
python -m http.server 8000
```

ブラウザで http://localhost:8000/ を開く。スマホ実機で確認する場合は、PC の LAN 内 IP に置き換える (例: http://192.168.x.x:8000/)。

`/flyer.html` (契約書類同封チラシ) と `/flyer_room.html` (部屋常設ポスター) も同じサーバから印刷プレビュー可能。

## GitHub Pages へのデプロイ

リポジトリは既に作成済み(`yokisecure-hub/shingakusei-portal`、Public、Pages = GitHub Actions Source)。
`config.json` や HTML を編集して push すれば 1〜2 分後に反映されます。

```powershell
git add config.json
git commit -m "Update: replace XXX url with A8 affiliate link"
git push
```

## QR コード生成

流入元別の QR を発行できます(`?src=` パラメータ付与):

```powershell
pip install "qrcode[pil]"

# 契約書類同封チラシ用
python generate_qr.py --channel qr        # qr_qr.png + qr_code.png (flyer.html が参照)

# 部屋常設ポスター用
python generate_qr.py --channel poster    # qr_poster.png (flyer_room.html が参照)

# 4種一括
python generate_qr.py --all               # qr/poster/email/line/web + qr_code.png
```

## 運用方針(超要約)

詳細は [OPERATOR_GUIDE.md](./OPERATOR_GUIDE.md) 参照。

### 主軸: A8.net (個別ASP / セルフサービス型)

- ハブ企業(B2B一括取次)は 4部屋規模では先方の採算が合わず審査困難 → **A8.net 一択**
- **即時提携** プログラムから順に提携 → 発行されたリンクURL(`<a href="...">` の中身だけ) を `config.json` の `services[].url` に貼付
- 5棟以上に拡大したらハブ企業へのパートナー申請を再検討(`config.json#hub` に意思記録済み)

### LTV 最大化 — 4年間ずっと使われる導線

| 配置 | 配布物 | utm_medium |
| --- | --- | --- |
| 契約書類への同封 | `flyer.html` 印刷 | `print-qr` |
| ブレーカー横 / 玄関裏 / 掲示板 | `flyer_room.html` 印刷 (各部屋常設) | `room-poster` |
| 入居案内メール | `templates/onboarding_email.md` | `email` |
| 入居案内 LINE | `templates/onboarding_line.md` | `line` |

`app.js` が `?src=<channel>` を読んで各サービスへの遷移URLに `utm_source=tenant-portal & utm_medium=<channel-medium> & utm_campaign=<property_name>` を自動付与するため、A8.net 管理画面で **どの導線が稼いだか** が見える。

### 掲載カテゴリ (11)

入居時(move-in) / 在学中(in-school) / 就活期(junior-senior) / 卒業期(graduation) のライフサイクル別:

- `internet` / `mobile` / `moving` / `utility` / `furniture` / `daily` / `finance` / `insurance` / `career` / `graduation` / `student`

### 想定収益(4部屋規模)

年間 4〜10件 / 2.5〜11万円 (サーバー代0円 × 加盟金0円 → **赤字リスク0**)
