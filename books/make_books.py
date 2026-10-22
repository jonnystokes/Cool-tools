"""Rebuild the book shelf's zips and catalog from Jon's manuscript folders.

    python make_books.py            # writes <id>.zip for every book below and books.json, prints what went in

Writes ONLY into this folder (cool-tools/books/). The source folders are read, never changed. The reader
(reader/?book=<id>) reads books.json, fetches the zip and imports it with the title and options given here.
A book's version is a short hash of the zip's content (names and text), so a rebuild with no change keeps
the version and the reader opens its stored copy without downloading again.

Each book: id, title, description, author, source folder, how the zip is laid out, and rules for what is
left out (said at the end). Only Jon's own work goes here.
"""

import hashlib
import json
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECTS = HERE.parent.parent
NOTE = re.compile(r"<!--\s*hb-note\s*-->[\s\S]*?(?:<!--\s*/hb-note\s*-->|$)")

BOOKS = [
    {
        "id": "american-history",
        "title": "American History",
        "description": "Plain-language U.S. history for readers of about 8 to 15: 37 subjects, each told through the same ten eras, from before 1500 to today.",
        "author": "Jon Stokes, with AI",
        "source": PROJECTS / "History-Book-Project-claude" / "manuscript",
        "layout": "folders",                 # <id>/<section folder>/<file>.md: the reader makes one book, a section per folder, a chapter per era
        "options": {"sections": True},       # the import choice "one book, each sub-folder a section" (the reader's default for such a zip)
        "strip_notes": True,                 # the hb-note editor blocks go (the reader drops them at import anyway)
    },
    {
        "id": "better-smarter-homes",
        "title": "Better Smarter Homes",
        "description": "A field manual for planning, building and keeping a long-life concrete home in Oregon: land, structure, services, the legal path and the records.",
        "author": "Jon Stokes, with AI",
        "source": PROJECTS / "theBook" / "revision7" / "manuscript",
        "layout": "flat",                    # <id>/<file>.md: one book, a chapter per file in name order (g0_ front matter, g1_ chapters, g2_ appendices)
        "options": {},
        "skip": {
            "g0_fm_01_table-of-contents.md": "a table of contents (the reader has a contents panel; read aloud it is a list of headings)",
        },
        "skip_if": [("_To research and write._", "an unwritten skeleton chapter (instructions to the writing AI, no text yet)")],
    },
]


def collect(book):
    """[(zip name, bytes)] in name order, and the reasons files were left out."""
    src = book["source"]
    if not src.is_dir():
        sys.exit(f"error: the source folder is missing: {src}")
    out, left = [], []
    for p in sorted(src.rglob("*.md")):
        rel = p.relative_to(src).as_posix()
        if book["layout"] == "flat" and "/" in rel:
            continue
        text = p.read_text(encoding="utf-8")
        why = book.get("skip", {}).get(rel)
        for mark, reason in book.get("skip_if", []):
            if not why and mark in text:
                why = reason
        if why:
            left.append((rel, why))
            continue
        if book.get("strip_notes"):
            text = NOTE.sub("", text)
        out.append((f"{book['id']}/{rel}", text.encode("utf-8")))
    if not out:
        sys.exit(f"error: no .md file found under {src}")
    return out, left


def main():
    catalog = []
    for book in BOOKS:
        files, left = collect(book)
        h = hashlib.sha1()
        for name, data in files:
            h.update(name.encode("utf-8")); h.update(b"\0"); h.update(data); h.update(b"\0")
        version = h.hexdigest()[:10]
        zpath = HERE / f"{book['id']}.zip"
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for name, data in files:
                info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))   # a fixed stamp: the same text gives the same zip
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, data)
        size = zpath.stat().st_size
        if size > 50_000_000:
            sys.exit(f"error: {zpath.name} is {size / 1e6:.1f} MB; GitHub Pages files must stay under 50 MB")
        words = sum(len(d.decode('utf-8').split()) for _, d in files)
        catalog.append({"id": book["id"], "title": book["title"], "description": book["description"], "author": book["author"],
                        "zip": f"{book['id']}.zip", "version": version, "updated": datetime.now().strftime("%Y-%m-%d"),
                        "size": size, "files": len(files), "words": words, "options": book["options"]})
        print(f"{book['id']}.zip: {len(files)} files, {words:,} words, {size / 1e6:.1f} MB, version {version}")
        for rel, why in left:
            print(f"  left out: {rel}: {why}")
    # The version of the catalog as a whole is in each book; `made` says when the file was written (12-hour time).
    now = datetime.now()
    made = f"{now:%Y-%m-%d} {int(now.strftime('%I'))}:{now:%M} {now:%p}"
    (HERE / "books.json").write_text(json.dumps({"format": "cool-tools-books", "made": made, "books": catalog}, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"books.json: {len(catalog)} books, made {made}")


if __name__ == "__main__":
    main()
