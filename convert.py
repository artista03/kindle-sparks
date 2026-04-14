#!/usr/bin/env python3
"""
Kindle Highlights Converter
Obsidian/Kindle_Library/*.md -> highlights.json, books.json, sessions.json
"""
import os, re, json
from pathlib import Path

KINDLE_DIR   = Path.home() / "Documents/Obsidian/Kindle_Library"
SESSIONS_DIR = Path.home() / "Documents/Obsidian/wiki/topics"
OUT_DIR      = Path(__file__).parent

def parse_frontmatter(text):
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if not m:
        return {}, text
    fm_text = m.group(1)
    data = {}
    for line in fm_text.splitlines():
        kv = re.match(r'^(\w+):\s*(.+)', line)
        if kv:
            data[kv.group(1).strip()] = kv.group(2).strip().strip('"\'')
    return data, text[m.end():]

def extract_highlights(body):
    highlights = []
    # 「---\n## この本の投資への活用法」以降を除外
    cutoff = re.search(r'\n---\n', body)
    if cutoff:
        body = body[:cutoff.start()]
    for line in body.splitlines():
        line = line.strip()
        if line.startswith('> ') and len(line) > 4:
            h = line[2:].strip()
            if h:
                highlights.append(h)
    return highlights

def convert_kindle():
    books = []
    highlights = []
    skip_count = 0

    md_files = sorted(KINDLE_DIR.glob("*.md"))
    print(f"処理中: {len(md_files)} ファイル...")

    for i, path in enumerate(md_files):
        try:
            text = path.read_text(encoding='utf-8')
        except Exception:
            skip_count += 1
            continue

        fm, body = parse_frontmatter(text)
        title  = fm.get('title', path.stem)
        author = fm.get('author', '不明')

        hl_list = extract_highlights(body)
        if not hl_list:
            skip_count += 1
            continue

        book_id = len(books)
        books.append({"id": book_id, "title": title, "author": author})
        for h in hl_list:
            highlights.append({"b": book_id, "h": h})

    print(f"  完了: {len(books)} 冊 / {len(highlights)} ハイライト / {skip_count} スキップ")
    return books, highlights

def convert_sessions(books):
    sessions = []
    title_to_id = {b['title']: b['id'] for b in books}

    session_files = sorted(SESSIONS_DIR.glob("ハイライト壁打ち_*.md"))
    for path in session_files:
        try:
            text = path.read_text(encoding='utf-8')
        except Exception:
            continue

        fm, body = parse_frontmatter(text)
        tags  = []
        if 'tags' in fm:
            raw = fm['tags'].strip('[]')
            tags = [t.strip() for t in raw.split(',') if t.strip()]

        created = fm.get('created', '')
        session = fm.get('session', path.stem)

        # 「使用ハイライト：」行から本のタイトルを抽出
        book_ids = []
        use_line = re.search(r'使用ハイライト[：:]\s*(.+)', body)
        if use_line:
            raw_books = use_line.group(1)
            # 『』や「」で囲まれた書名、または読点区切りの書名を探す
            titles_found = re.findall(r'[『「]([^』」]+)[』」]', raw_books)
            if not titles_found:
                titles_found = [t.strip() for t in re.split(r'[、,，]', raw_books) if t.strip()]
            for t in titles_found:
                if t in title_to_id:
                    book_ids.append(title_to_id[t])

        # 壁打ち内で引用された「> 」テキストも抽出
        quotes = []
        for line in body.splitlines():
            line = line.strip()
            if line.startswith('> ') and len(line) > 4:
                quotes.append(line[2:].strip())

        sessions.append({
            "date":     created,
            "session":  session,
            "tags":     tags,
            "book_ids": book_ids,
            "quotes":   quotes[:10]  # 最大10件
        })

    print(f"  壁打ちセッション: {len(sessions)} 件")
    return sessions

def main():
    print("=== Kindle Highlights 変換 ===")

    books, highlights = convert_kindle()
    sessions = convert_sessions(books)

    # 出力
    (OUT_DIR / "books.json").write_text(
        json.dumps(books, ensure_ascii=False, separators=(',', ':')),
        encoding='utf-8'
    )
    (OUT_DIR / "highlights.json").write_text(
        json.dumps(highlights, ensure_ascii=False, separators=(',', ':')),
        encoding='utf-8'
    )
    (OUT_DIR / "sessions.json").write_text(
        json.dumps(sessions, ensure_ascii=False, separators=(',', ':')),
        encoding='utf-8'
    )

    hl_size = (OUT_DIR / "highlights.json").stat().st_size / 1024 / 1024
    print(f"  highlights.json: {hl_size:.1f} MB")
    print("=== 完了 ===")

if __name__ == '__main__':
    main()
