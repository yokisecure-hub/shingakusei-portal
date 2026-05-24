"""A8 HTMLタグ一括貼付け → config.json 自動更新ツール.

使い方:
    python update_affiliate_urls.py affiliate_links.txt --dry-run   # 確認のみ
    python update_affiliate_urls.py affiliate_links.txt             # 実適用
    python update_affiliate_urls.py --self-test                     # 内蔵テスト

入力ファイルの書き方 (affiliate_links.example.txt 参照):
    ## サービス名(config.json#services[].name と一致)
    <a href="https://px.a8.net/svt/ejp?a8mat=XXX..."><img ... alt="..." ...></a>...

    ## 別のサービス
    <a href="https://px.a8.net/svt/ejp?a8mat=YYY..."> ...

「## サービス名」を省略した場合、<img alt="..."> から自動推定する。

挙動:
- 適用前に config.json.bak を自動作成
- マッチ失敗・曖昧マッチはスキップして報告
- HTMLエンティティ(&amp; など)を URL内で正常化
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

A_HREF_RE = re.compile(r'<a\s+[^>]*?href="([^"]+)"', re.IGNORECASE)
IMG_ALT_RE = re.compile(r'<img\s+[^>]*?alt="([^"]*)"', re.IGNORECASE)
LABEL_RE = re.compile(r"^\s*##\s*(.+?)\s*$")


_LABEL_LINE_RE = re.compile(r"(?m)^\s*##\s*(.+?)\s*$")
_A_TAG_START_RE = re.compile(r"<a\s+[^>]*?href=", re.IGNORECASE)


def split_blocks(text: str) -> list[tuple[str | None, str]]:
    """各 `<a href>` を1ブロックとして抽出し、直前の `## ラベル` を継承する。

    ・ラベル無しブロックも検出される(altから推定)。
    ・同一ラベル内に複数 `<a>` がある場合は全部抽出される(後段で重複サービスは初回のみ採用)。
    """
    labels = [(m.start(), m.group(1).strip()) for m in _LABEL_LINE_RE.finditer(text)]
    a_starts = [m.start() for m in _A_TAG_START_RE.finditer(text)]
    if not a_starts:
        return []

    boundaries = sorted(set([*[p for p, _ in labels], *a_starts, len(text)]))
    blocks: list[tuple[str | None, str]] = []
    prev_a = -1
    for a_start in a_starts:
        # 直前の <a> 以降、この <a> 直前までに出現した `## label` のみ採用
        applicable = [lab for pos, lab in labels if prev_a < pos < a_start]
        label = applicable[-1] if applicable else None
        end = min(b for b in boundaries if b > a_start)
        body = text[a_start:end].strip()
        if body:
            blocks.append((label, body))
        prev_a = a_start
    return blocks


def extract_url_and_label(
    body: str, override_label: str | None
) -> tuple[str | None, str | None]:
    href_m = A_HREF_RE.search(body)
    if not href_m:
        return None, None
    url = href_m.group(1).replace("&amp;", "&").strip()
    if override_label:
        return url, override_label
    alt_m = IMG_ALT_RE.search(body)
    label = alt_m.group(1).strip() if alt_m else None
    return url, (label or None)


def normalize(s: str | None) -> str:
    if not s:
        return ""
    # 全角→半角、小文字化
    s = unicodedata.normalize("NFKC", s).lower()
    # 記号・空白を削除
    return re.sub(r"[\s\(\)（）\[\]【】「」・,.\-_/]+", "", s)


def find_match(label: str | None, services: list[dict]) -> list[dict]:
    if not label:
        return []
    nl = normalize(label)
    if not nl:
        return []
    # 1. 正規化完全一致
    exact = [s for s in services if normalize(s.get("name")) == nl]
    if exact:
        return exact
    # 2. 部分一致(双方向)
    sub = [
        s
        for s in services
        if nl in normalize(s.get("name")) or normalize(s.get("name")) in nl
    ]
    if sub:
        return sub
    # 3. difflib 類似度(0.6 以上)
    names = [s.get("name", "") for s in services]
    close = difflib.get_close_matches(label, names, n=3, cutoff=0.6)
    return [s for s in services if s.get("name") in close]


def process(
    input_text: str, config: dict
) -> tuple[list, list, list]:
    """戻り値: (updates, ambiguous, unmatched)
    updates: [(idx, name, old_url, new_url, label)]
    ambiguous: [(label, [names], url)]
    unmatched: [(label, url)]
    """
    services: list[dict] = config["services"]
    blocks = split_blocks(input_text)
    updates: list = []
    ambiguous: list = []
    unmatched: list = []
    seen_indices: set[int] = set()
    for override_label, body in blocks:
        url, label = extract_url_and_label(body, override_label)
        if not url:
            continue
        cands = find_match(label, services)
        if len(cands) == 1:
            svc = cands[0]
            idx = services.index(svc)
            if idx in seen_indices:
                # 同サービスの2件目以降(バナー+テキスト等)はスキップ
                continue
            seen_indices.add(idx)
            updates.append((idx, svc["name"], svc.get("url", ""), url, label or svc["name"]))
        elif len(cands) > 1:
            ambiguous.append((label, [s["name"] for s in cands], url))
        else:
            unmatched.append((label, url))
    return updates, ambiguous, unmatched


def report(updates, ambiguous, unmatched, n_blocks: int) -> None:
    print()
    print("=== 解析結果 ===")
    print(f"入力ブロック数 : {n_blocks}")
    print(f"マッチ(更新予定): {len(updates)}")
    print(f"曖昧(複数候補) : {len(ambiguous)}")
    print(f"未マッチ        : {len(unmatched)}")

    if updates:
        print("\n--- 更新内容 ---")
        for _, name, old, new, label in updates:
            print(f"[{name}]")
            print(f"  旧 url : {old or '(なし)'}")
            print(f"  新 url : {new}")
            if label and label != name:
                print(f"  (元ラベル: {label})")

    if ambiguous:
        print("\n--- 曖昧(スキップ) ---")
        for label, names, url in ambiguous:
            print(f'ラベル "{label}" → 候補: {", ".join(names)}')
            print(f"  URL    : {url}")
            print(f"  対処   : ## サービス名 を入力ファイルに付与")

    if unmatched:
        print("\n--- 未マッチ(スキップ) ---")
        for label, url in unmatched:
            print(f'ラベル "{label or "(なし)"}"')
            print(f"  URL    : {url}")
            print(f"  対処   : ## サービス名 を入力ファイルに付与")


def apply_updates(config: dict, updates: list, config_path: Path) -> Path:
    backup = config_path.with_suffix(".json.bak")
    shutil.copy(config_path, backup)
    services = config["services"]
    for idx, _, _, new_url, _ in updates:
        services[idx]["url"] = new_url
    config_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return backup


# ---------------- 内蔵 self-test ----------------

SELF_TEST_INPUT = """\
## GMOとくとくBB光
<a href="https://px.a8.net/svt/ejp?a8mat=GMOMAT&amp;a8ejpredirect=https%3A%2F%2Fgmobb.jp%2F"><img border="0" width="320" height="50" alt="GMO" src="https://www25.a8.net/0.gif"></a>

## 引越し侍(一括見積もり)
<a href="https://px.a8.net/svt/ejp?a8mat=ZAMURAI&amp;a8ejpredirect=https%3A%2F%2Fhikkoshizamurai.jp%2F"><img alt="hikkoshi-zamurai" src="x"></a>

## 楽天カード
<a href="https://px.a8.net/svt/ejp?a8mat=RAKCARD"><img alt="楽天カード" src="x"></a>

<a href="https://px.a8.net/svt/ejp?a8mat=NOLABEL_AHAMO"><img alt="ahamo" src="x"></a>

## 存在しないサービス
<a href="https://px.a8.net/svt/ejp?a8mat=NEVER"><img alt="ghost" src="x"></a>
"""


def self_test() -> int:
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        print("[self-test] config.json が見つかりません", file=sys.stderr)
        return 1
    config = json.loads(config_path.read_text(encoding="utf-8"))
    services = config["services"]

    # split_blocks
    blocks = split_blocks(SELF_TEST_INPUT)
    assert len(blocks) == 5, f"blocks={len(blocks)}"
    print("[OK] split_blocks → 5 blocks")

    # normalize
    assert normalize("GMOとくとくBB光") == normalize("ＧＭＯとくとくBB光"), "NFKC"
    assert normalize("三井住友カード(NL)") == normalize("三井住友カード（NL）"), "全角括弧"
    assert normalize("引越し侍 (一括見積もり)") == normalize("引越し侍(一括見積もり)"), "空白"
    print("[OK] normalize → 全角半角・記号差を吸収")

    # find_match
    gmo = find_match("GMOとくとくBB光", services)
    assert len(gmo) == 1 and gmo[0]["name"] == "GMOとくとくBB光", gmo
    print("[OK] find_match(完全) → GMOとくとくBB光")

    sub = find_match("ahamo", services)
    assert len(sub) == 1 and sub[0]["name"] == "ahamo(ドコモ)", sub
    print("[OK] find_match(部分) → ahamo(ドコモ)")

    fuzzy = find_match("hikkoshi-zamurai", services)
    # 英字ラベル→日本語名は通常マッチしない。仕様として未マッチを許容
    print(f"[OK] find_match(英字ラベル) → matches={[s['name'] for s in fuzzy]} (未マッチ許容)")

    ghost = find_match("ghost", services)
    assert ghost == [], ghost
    print("[OK] find_match(未存在) → []")

    # process
    updates, ambiguous, unmatched = process(SELF_TEST_INPUT, config)
    print(f"[OK] process → updates={len(updates)} ambiguous={len(ambiguous)} unmatched={len(unmatched)}")
    update_names = [u[1] for u in updates]
    assert "GMOとくとくBB光" in update_names
    assert "引越し侍(一括見積もり)" in update_names
    assert "楽天カード" in update_names
    assert "ahamo(ドコモ)" in update_names
    print("[OK] process → GMO/引越し侍/楽天カード/ahamo 全てマッチ")

    # URL正規化 (&amp; → &)
    gmo_url = [u[3] for u in updates if u[1] == "GMOとくとくBB光"][0]
    assert "&amp;" not in gmo_url and "a8mat=GMOMAT" in gmo_url
    print(f"[OK] URL normalized: {gmo_url[:80]}...")

    print("\n[self-test PASS]")
    return 0


# ---------------- CLI entry ----------------

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="A8 HTMLタグ一括貼付け → config.json 自動更新")
    ap.add_argument("input_file", nargs="?", help="A8 HTMLタグ貼付けファイル")
    ap.add_argument("--config", default="config.json", help="更新対象 config.json")
    ap.add_argument("--dry-run", action="store_true", help="ファイル更新せず内容のみ表示")
    ap.add_argument("--self-test", action="store_true", help="内蔵テストを実行")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    if not args.input_file:
        ap.error("input_file が必要です(--self-test 指定時を除く)")

    input_path = Path(args.input_file)
    config_path = Path(args.config)
    if not input_path.exists():
        print(f"[err] 入力ファイルが見つかりません: {input_path}", file=sys.stderr)
        return 1
    if not config_path.exists():
        print(f"[err] config.json が見つかりません: {config_path}", file=sys.stderr)
        return 1

    text = input_path.read_text(encoding="utf-8")
    config = json.loads(config_path.read_text(encoding="utf-8"))

    updates, ambiguous, unmatched = process(text, config)
    n_blocks = len(split_blocks(text))
    report(updates, ambiguous, unmatched, n_blocks)

    if args.dry_run:
        print("\n[dry-run] config.json は更新していません")
        return 0
    if not updates:
        print("\n更新対象なし。終了。")
        return 0

    backup = apply_updates(config, updates, config_path)
    print(f"\nバックアップ作成: {backup}")
    print(f"config.json を更新しました ({len(updates)}件)")
    print("\n次のステップ:")
    print("  git diff config.json")
    print('  git add config.json && git commit -m "Update affiliate URLs" && git push')
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
