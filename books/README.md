# Select a book

A shelf of Jon Stokes's own books for the Book reader. Each book is one zip of Markdown files; the
page lists them from `books.json` and each **Open** button opens `../reader/?book=<id>`: the reader
downloads the zip once (with progress), keeps it in the browser with your place in it, and opens it.
Opening the same link again just opens the stored book; when the shelf has a newer version, the reader
replaces the stored copy and keeps your place. **Open the empty reader** is the reader as before, with
no book chosen (add your own).

Open it: https://jonnystokes.github.io/Cool-tools/books/

| Book | What it is |
|---|---|
| American History | Plain-language U.S. history for readers of about 8 to 15: 37 subjects, each told through the same ten eras. Imported as one book with a section per subject and a chapter per era. |
| Better Smarter Homes | A field manual for planning, building and keeping a long-life concrete home in Oregon. One chapter per file. |

## Files

- `books.json`: the catalog. Per book: `id`, `title`, `description`, `author`, `zip` (relative to this
  folder), `version` (a short hash of the zip's content: unchanged text keeps the version, so nothing
  downloads again), `updated`, `size` (bytes), `files`, `words`, `options` (import options the reader
  honours: `sections: true` = one book with a section per folder). The reader never sets "Read across
  time" from the catalog.
- `<id>.zip`: the book's files, under one folder named after the id.
- `make_books.py`: rebuilds every zip and `books.json` from the manuscript folders on Jon's PC
  (`python make_books.py`). It writes only into this folder and never changes the sources. Files it
  leaves out (an unwritten skeleton chapter, a table of contents) are printed with the reason.

Every file here stays under GitHub Pages' 50 MB limit. The reader's source is in Jon's
`Projects\Walker of Worlds` folder (`src/shelf.js` is the auto-load).
