"""Rebuild the two shelf books from Jon's manuscript folders (the drop-in layout of 2026-10-22).

    python make_books.py            # writes books/<id>/book.zip and books/<id>/book.json for every book below, then index.json

Writes ONLY into this folder (cool-tools/books/). The source folders are read, never changed. Each book is a
folder `books/<id>/` with its zip and a small book.json (title, description, author, options); make_index.py
(run here at the end, and by the Books index workflow on every push) lists every such folder in index.json.
A book's version is a hash of the zip's entries, so a rebuild with no change keeps the version.

Each book: id, title, description, author, source folder, how the zip is laid out, and rules for what is
left out (said at the end). Only Jon's own work goes here. A book that is not rebuilt from a manuscript needs
no entry here: drop its folder in (README.md, "How to add a book").
"""

import json
import re
import sys
import subprocess
import zipfile
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
    for book in BOOKS:
        files, left = collect(book)
        folder = HERE / book["id"]
        folder.mkdir(exist_ok=True)
        zpath = folder / "book.zip"
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for name, data in files:
                info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))   # a fixed stamp: the same text gives the same zip
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, data)
        meta = {"title": book["title"], "description": book["description"], "author": book["author"], "options": book["options"]}
        (folder / "book.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8", newline="\n")
        words = sum(len(d.decode("utf-8").split()) for _, d in files)
        print(f"{book['id']}/book.zip: {len(files)} files, {words:,} words, {zpath.stat().st_size / 1e6:.1f} MB")
        for rel, why in left:
            print(f"  left out: {rel}: {why}")
    subprocess.run([sys.executable, str(HERE / "make_index.py")], check=True)


if __name__ == "__main__":
    main()
