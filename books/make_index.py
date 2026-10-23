"""Make books/index.json: the list of every book folder here, for the Select-a-book page and the reader.

    python make_index.py            # scans books/*/, writes index.json, prints a line per book and every problem

A book is a folder `books/<id>/` holding ONE zip of its text files (any name) and, if wanted, a `book.json`:
    { "title": "...", "description": "...", "author": "...", "zip": "name.zip", "options": { "sections": true } }
Everything in book.json is optional: the title defaults to the folder name made readable ("my-book" → "My Book"),
description and author to "", zip to the one zip in the folder, options to {}. A folder with no zip, two zips or
a broken book.json is listed under "problems" (the page and the reader show them) and left out of "books".

A book's version is a short hash of the zip's entries (names, CRCs, sizes), so re-zipping the same text keeps the
version and nobody downloads it again; changed text changes it. "updated" is the date of the folder's last commit
(git), today when git has no record of it. GitHub Pages cannot list folders, so the Books index workflow
(.github/workflows/books-index.yml) runs this on every push that touches books/ and commits index.json.
Folders whose name starts with "." or "_" are skipped. The output has no timestamp: an unchanged shelf gives
an unchanged file, so the workflow commits nothing.
"""

import hashlib
import json
import re
import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEXT = (".md", ".txt", ".text", ".markdown")


def pretty(name):
    return " ".join(w[:1].upper() + w[1:] for w in re.split(r"[-_\s]+", name) if w)


def updated(folder):
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", str(folder)], cwd=HERE, capture_output=True, text=True, timeout=30)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return date.today().isoformat()


def scan(folder):
    """The index entry for one book folder; raises ValueError with the plain reason when it cannot be listed."""
    meta = {}
    bj = folder / "book.json"
    if bj.is_file():
        try:
            meta = json.loads(bj.read_text(encoding="utf-8"))
        except (ValueError, UnicodeDecodeError) as e:
            raise ValueError(f"book.json is not valid JSON: {e}")
        if not isinstance(meta, dict):
            raise ValueError("book.json must hold an object { ... }")
    zips = sorted(p.name for p in folder.iterdir() if p.is_file() and p.suffix.lower() in (".zip", ".epub"))
    zname = meta.get("zip")
    if zname:
        if not (folder / zname).is_file():
            raise ValueError(f'book.json names "{zname}" but the folder has no such file')
    elif len(zips) == 1:
        zname = zips[0]
    elif not zips:
        raise ValueError("no zip in the folder (a book is one zip of .md or .txt files, or one .epub)")
    else:
        raise ValueError(f"{len(zips)} zips in the folder ({', '.join(zips)}); say which in book.json: \"zip\": \"name.zip\"")
    zpath = folder / zname
    epub = zname.lower().endswith(".epub")
    kinds = (".xhtml", ".html", ".htm") if epub else TEXT
    h = hashlib.sha1()
    files = words = 0
    try:
        with zipfile.ZipFile(zpath) as z:
            for info in sorted(z.infolist(), key=lambda i: i.filename):
                if info.is_dir():
                    continue
                h.update(f"{info.filename}\0{info.CRC}\0{info.file_size}\0".encode("utf-8"))
                if info.filename.lower().endswith(kinds):
                    files += 1
                    t = z.read(info).decode("utf-8", "replace")
                    words += len((re.sub(r"<[^>]*>", " ", t) if epub else t).split())  # an EPUB's count is rough (markup stripped)
    except zipfile.BadZipFile as e:
        raise ValueError(f"{zname} is not a zip: {e}")
    if not files:
        raise ValueError(f"{zname} holds no {'XHTML page' if epub else '.md or .txt file'}")
    size = zpath.stat().st_size
    if size > 50_000_000:
        raise ValueError(f"{zname} is {size / 1e6:.1f} MB; GitHub Pages files must stay under 50 MB")
    options = meta.get("options") if isinstance(meta.get("options"), dict) else {}
    return {"id": folder.name, "title": str(meta.get("title") or pretty(folder.name)), "description": str(meta.get("description") or ""),
            "author": str(meta.get("author") or ""), "zip": f"{folder.name}/{zname}", "version": h.hexdigest()[:10],
            "updated": updated(folder), "size": size, "files": files, "words": words, "options": options}


def main():
    books, problems = [], []
    for folder in sorted(p for p in HERE.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))):
        try:
            b = scan(folder)
            books.append(b)
            print(f"{b['id']}: \"{b['title']}\", {b['files']} files, {b['words']:,} words, {b['size'] / 1e6:.1f} MB, version {b['version']}, updated {b['updated']}")
        except ValueError as e:
            problems.append({"id": folder.name, "problem": str(e)})
            print(f"{folder.name}: NOT listed: {e}", file=sys.stderr)
    out = {"format": "cool-tools-books", "books": books, "problems": problems}
    (HERE / "index.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"index.json: {len(books)} books, {len(problems)} problems")


if __name__ == "__main__":
    main()
