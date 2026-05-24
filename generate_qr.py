"""チラシ印刷/メール/LINE 配信向け QR コード生成スクリプト.

使い方:
    python generate_qr.py                                           # 既定URL(PORTAL_URL) + channel=qr
    python generate_qr.py https://your.site/                        # URLを引数で指定
    python generate_qr.py https://your.site/ --channel email        # 流入元タグ付与(URL末尾に ?src=email)
    python generate_qr.py https://your.site/ --channel qr --output flyer_qr.png
    python generate_qr.py --all https://your.site/                  # qr/email/line/web の4種を一括生成

URL末尾の `?src=<channel>` は app.js が utm_source/medium/campaign に変換し、
契約書類同封のチラシ(qr)・入居案内メール(email)・LINE通知(line)の流入別に
申込み実績を計測可能にする。

依存:
    pip install "qrcode[pil]"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

import qrcode
from qrcode.constants import ERROR_CORRECT_H

PORTAL_URL = "https://yokisecure-hub.github.io/shingakusei-portal/"
CHANNELS = ("qr", "email", "line", "web")
BOX_SIZE = 20  # 1モジュールあたりpx
BORDER = 4     # モジュール余白(最小4)


def append_channel(url: str, channel: str) -> str:
    """URL に ?src=<channel> を付与(既存のクエリは保持)。"""
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["src"] = channel
    new_query = urlencode(query)
    return urlunparse(parsed._replace(query=new_query))


def generate(url: str, output: Path) -> Path:
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_H,
        box_size=BOX_SIZE,
        border=BORDER,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    out_path = output.resolve()
    img.save(out_path)
    return out_path


def emit(url: str, channel: str, output: Path) -> None:
    decorated = append_channel(url, channel)
    path = generate(decorated, output)
    size = path.stat().st_size
    print(f"[OK] channel={channel:<5} url={decorated}")
    print(f"     -> {path}  ({size:,} bytes)")


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="QRコード/流入元タグ付きURL 生成器")
    p.add_argument("url", nargs="?", default=PORTAL_URL, help=f"ポータルURL (既定: {PORTAL_URL})")
    p.add_argument(
        "--channel",
        choices=CHANNELS,
        default="qr",
        help="流入元タグ (qr/email/line/web). チラシ用は qr (既定)",
    )
    p.add_argument(
        "--output",
        default=None,
        help="出力ファイル名 (既定: qr_<channel>.png)",
    )
    p.add_argument(
        "--all",
        action="store_true",
        help="qr/email/line/web の4種を一括生成 (--channel/--output は無視)",
    )
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    if args.all:
        for ch in CHANNELS:
            emit(args.url, ch, Path(f"qr_{ch}.png"))
        # 印刷チラシ(flyer.html) が既定で参照する qr_code.png は qr チャネルを採用
        emit(args.url, "qr", Path("qr_code.png"))
        print("\nチラシ(flyer.html)は qr_code.png を表示します。")
        return 0

    output = Path(args.output) if args.output else Path(f"qr_{args.channel}.png")
    emit(args.url, args.channel, output)
    # チラシ(flyer.html)用の既定名にもコピー(qr チャネル時のみ)
    if args.channel == "qr" and args.output is None:
        emit(args.url, "qr", Path("qr_code.png"))
    print("\nチラシ(flyer.html)へ貼付け、または入居案内メール/LINEへ画像を添付してください。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
