"""Rebuild the shelf books from Jon's manuscripts (the drop-in layout of 2026-10-22).

    python make_books.py                     # every book below, then index.json
    python make_books.py american-history    # only the books named (by id), then index.json

Writes ONLY into this folder (cool-tools/books/): books/<id>/book.zip and books/<id>/book.json (title,
description, author, options), then runs make_index.py, which lists every book folder in index.json (the
Books index workflow runs it on every push too). The sources are read, never changed. A book's version is a
hash of the zip's entries, so a rebuild with no change keeps the version.

Each book: id, title, description, author, source, how the zip is laid out, and rules for what is left out
(said at the end). Only Jon's own work goes here. A book that is not rebuilt from a manuscript needs no entry
here: drop its folder in (README.md, "How to add a book").

American History ("layout": "history", 2026-10-28) is made by the book's own Markdown build: this imports
History-Book-Project-claude/tools/build_full_book_md.py (and through it build_full_book.py's registry reader,
parser and chapter loader, with bytecode writing off so no __pycache__ lands in that project) and writes the
text build/history-book.md holds, cut into the files the Book reader needs. The reader (Projects/Walker of
Worlds/src: chapter.js group(), book.js plan(), importJob and nameChapters) makes a section per top-level
folder of the zip, in natural order of the folder names ("_" before digits, digits before letters); names a
section after the one "#" heading its files share, less a "Chapter N:" lead, else after the folder; and, as
the chapter files share their "##" era headings, cuts every file at its "##" headings: a chapter per era,
named by the era ("Exploration and Discovery: Before 1500"), with Read across time offered. So the zip holds,
in book order:
    _introduction/00-introduction.md ... 03-ten-minute-history.md     section "Introduction": the
        introduction and the front matter, a file each, in the build's order
    01 Exploration and Discovery/Chapter opening.md ... 37 Holidays/Chapter opening.md    a file per chapter
        in registry order: "# Chapter N: Title" (with a "Part N: Title" line above it in a part's first
        chapter), the opening card, then "## <era>" ten times with the span labels and story names as "###" headings,
        and the closing card after the last era. The reader makes the text before the first era heading
        (the chapter heading and the card) a chapter of its own named after the file, hence the file's
        name: the contents show "Chapter opening", then the ten eras.
    Back of the Book/01-how-we-know.md ... 07-answers.md     section "Back of the Book": the back matter
In the introduction and back matter files every heading below the "#" title goes one level down, so no "##"
is left to cut them into eras (the ten-paragraph history and the timeline use the era names as headings).
Markers, editor notes, anchors and contents links are left out; the front matter's {{tokens}} hold the
build's own numbers. The build stops if any marker or token is left, if an era heading is not shared by
two chapters (it would not be an era in the reader), or if the chapters' words differ from the book's count.
"""

import json
import re
import sys
import subprocess
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECTS = HERE.parent.parent

BOOKS = [
    {
        "id": "american-history",
        "title": "American History",
        "description": "Plain-language U.S. history for readers of about 8 to 15: 37 subjects, each told through the same ten eras, from before 1500 to today.",
        "author": "Jon Stokes, with AI",
        "source": PROJECTS / "History-Book-Project-claude",
        "layout": "history",                 # the book's own Markdown build, cut a file per chapter (see above)
        "options": {"sections": True},       # the import choice "one book, each sub-folder a section" (the reader's default for such a zip)
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
    """[(zip name, bytes)] in book order, and the reasons files were left out."""
    if book["layout"] == "history":
        return history(book), []
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
        out.append((f"{book['id']}/{rel}", text.encode("utf-8")))
    if not out:
        sys.exit(f"error: no .md file found under {src}")
    return out, left


# ---- American History: the book's Markdown build, a file per chapter (see the docstring) ----------------
INTRO, BACK, OPENING = "_introduction", "Back of the Book", "Chapter opening.md"
UP = re.compile(r"^#(#{1,5}[ \t])")          # a heading one level up: the build's chapter is "##", here "#"
DOWN = re.compile(r"^(#{2,5}[ \t])")         # a heading one level down: no "##" in a front or back matter file
ANCHOR = re.compile(r'^<a id="[^"]*"></a>$')
RECORD = re.compile(r"(?m)^(>.*)\n(?=> \*\*)")
LEFTOVER = re.compile(r"<!--|-->|\bhb-[a-z]|\{\{|\}\}|\]\(#")   # markers, notes, tokens, contents links


def history_build(root):
    """The book's Markdown build module; its .B is build_full_book.py."""
    tools = root / "tools"
    if not (tools / "build_full_book_md.py").is_file():
        sys.exit(f"error: the history book's Markdown build is missing: {tools / 'build_full_book_md.py'}")
    sys.path.insert(0, str(tools))
    keep, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        import build_full_book_md
    finally:
        sys.dont_write_bytecode = keep
    return build_full_book_md


def history(book):
    M = history_build(book["source"])
    B = M.B
    chapters, parts, before, after = B.prepare_book()
    for w in B.warnings:
        print(f"  the book's build warns: {w}")
    out = []

    def put(path, lines):
        text = "\n".join(M.tidy([l for l in lines if not ANCHOR.match(l)])) + "\n"
        text = RECORD.sub(r"\1\n>\n", text)            # each record line its own paragraph, as in the build
        bad = LEFTOVER.search(text)
        if bad:
            sys.exit(f"error: {path} line {text.count(chr(10), 0, bad.start()) + 1} still holds {bad.group(0)!r}")
        out.append((f"{book['id']}/{path}", text.encode("utf-8")))
        return text

    up = lambda lines: [UP.sub(r"\1", l) for l in lines]
    matter = lambda m: [DOWN.sub(r"#\1", l) for l in M.body(m["lines"], 0)]
    name = lambda m: re.sub(r"^(?:front|back)-\d\d-", "", m["id"])
    for k, m in enumerate(before):
        put(f"{INTRO}/{k:02d}-{name(m)}.md", matter(m))
    eras, words, part = {}, 0, None
    for c in chapters:
        md, part_line = [], None
        if c["part"] != part:
            part = c["part"]
            part_line = f"**Part {part}: {parts.get(part, '')}**"
            md += [part_line, ""]
        md += [f"# Chapter {int(c['num'])}: {c['title']}", ""]
        if c["opening"]:
            md += up(M.zoom(c["opening"][1], c["opening"][2]))
        for e in c["eras"]:
            md += [f"## {e['heading'] or e['label']}", ""]
            for kind, attrs, lines in e["blocks"]:
                md += up(M.story(attrs, lines) if kind == "story" else M.zoom(attrs, lines))
        if c["closing"]:
            md += up(M.zoom(c["closing"][1], c["closing"][2]))
        folder = f"{int(c['num']):02d} {c['title']}"
        if re.search(r"[./\\]", c["title"]):
            sys.exit(f"error: chapter {c['num']}'s title {c['title']!r} cannot be a folder name (the reader cuts names at a dot)")
        text = put(f"{folder}/{OPENING}", md)
        for h in re.findall(r"(?m)^## (.+)$", text):
            eras.setdefault(h, []).append(folder)
        words += B.block_words([l for l in text.splitlines() if l != part_line])   # the build's word rule
    for k, m in enumerate(after, 1):
        put(f"{BACK}/{k:02d}-{name(m)}.md", matter(m))

    alone = [f'"{h}" ({f[0]})' for h, f in eras.items() if len(f) < 2]
    if alone:
        sys.exit(f"error: an era heading only one chapter has would not be an era in the reader: {', '.join(alone)}")
    book_words = sum(c["words"] for c in chapters)
    if words != book_words:
        sys.exit(f"error: the chapters hold {words:,} words by the build's rule, the book {book_words:,}")
    print(f"  sections: Introduction ({len(before)} files), {len(chapters)} chapters with {len(eras)} eras each shared, "
          f"Back of the Book ({len(after)} files); the chapters' {words:,} words are the book's own count")
    return out


def build(book):
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


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")      # a warning with a character the console lacks must not stop the build
    if argv[:1] in (["-h"], ["--help"]):
        print(__doc__)
        return
    ids = [b["id"] for b in BOOKS]
    unknown = [a for a in argv if a not in ids]
    if unknown:
        sys.exit(f"error: no book {', '.join(unknown)} here; the books are {', '.join(ids)}")
    for book in BOOKS:
        if not argv or book["id"] in argv:
            build(book)
    sys.stdout.flush()                                 # this script's lines before make_index.py's
    subprocess.run([sys.executable, str(HERE / "make_index.py")], check=True)


if __name__ == "__main__":
    main(sys.argv[1:])
