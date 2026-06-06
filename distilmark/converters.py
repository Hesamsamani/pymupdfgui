# -*- coding: utf-8 -*-
"""Conversion engines: native PyMuPDF, pdfplumber, Ollama, OpenAI, Anthropic.

Shared features handled here (engine-agnostic):
  • page range selection            (opts.page_range)
  • OCR fallback for scanned pages  (opts.ocr_enabled)
  • post-processing pipeline        (opts.pp_*)
  • pdfplumber table tuning         (opts.plumber_table_settings)
  • concurrent page processing      (opts.llm_concurrency, LLM engines only)
  • cooperative cancellation        (opts.cancel_check)
"""
from __future__ import annotations

import base64
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import datetime as _dt
import hashlib
import hmac
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pymupdf


ProgressCb = Callable[[int, int, str], None]  # (current_page, total_pages, message)


class CancelledError(Exception):
    """Raised cooperatively when the user cancels a running conversion."""


class ConversionError(Exception):
    """A user-facing conversion problem whose message is safe to show as-is.

    The GUI shows ``str(err)`` for these directly (no traceback), so the text
    must be a clear, human-readable explanation rather than a stack dump.
    """


class PdfError(ConversionError):
    """The input PDF cannot be read (password-protected, corrupt, or not a PDF)."""


def _open_pdf(pdf_path) -> "pymupdf.Document":
    """Open a PDF for reading, translating the two common failure modes into a
    friendly :class:`PdfError` instead of leaking raw PyMuPDF exceptions (which
    otherwise reach the UI as a Python traceback).

    Callers own the returned document and must close it.
    """
    name = Path(pdf_path).name
    try:
        doc = pymupdf.open(pdf_path)
    except pymupdf.FileDataError as e:
        raise PdfError(
            f"'{name}' is not a valid PDF, or the file is corrupted."
        ) from e
    except Exception as e:  # unreadable path, permissions, unknown format, …
        raise PdfError(f"Could not open '{name}': {e}") from e
    if doc.needs_pass:
        doc.close()
        raise PdfError(
            f"'{name}' is password-protected. "
            "Remove the password (or unlock the PDF) and try again."
        )
    return doc


@dataclass
class ConvertOptions:
    include_images: bool = True
    page_separator: bool = True
    image_dir: Path | None = None
    # folder name (not full path) used for relative markdown image refs
    image_dir_name: str | None = None
    # 1-based inclusive page range; None = all pages
    page_range: tuple[int, int] | None = None
    # OCR fallback for pages with no extractable text (needs Tesseract)
    ocr_enabled: bool = False
    ocr_language: str = "eng"
    # post-processing pipeline
    pp_merge_hyphens: bool = False
    pp_collapse_blanks: bool = False
    pp_strip_headers_footers: bool = False
    # pdfplumber table extraction
    plumber_tables_enabled: bool = True
    # pdfplumber table-extraction tuning (passed straight to extract_tables)
    plumber_table_settings: dict | None = None
    # number of pages processed in parallel for LLM engines (1 = sequential)
    llm_concurrency: int = 1
    # cooperative cancellation: a callable that returns True to abort
    cancel_check: Callable[[], bool] | None = None
    # custom prompt for LLM engines (empty/None = default PROMPT)
    custom_prompt: str | None = None
    # math-mode prompt augmentation (LLM engines only)
    math_mode: bool = False
    # streaming callback: stream_cb(page_index_0based, partial_text)
    stream_cb: Callable[[int, str], None] | None = None


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _check_cancel(opts: ConvertOptions) -> None:
    if opts.cancel_check and opts.cancel_check():
        raise CancelledError("Conversion cancelled by user.")


def _page_indices(total: int, page_range: tuple[int, int] | None) -> list[int]:
    """Return 0-based page indices to process for a 1-based inclusive range."""
    if not page_range:
        return list(range(total))
    start, end = page_range
    start = max(1, start or 1)
    end = min(total, end or total)
    return [i for i in range(total) if start <= i + 1 <= end]


def _ocr_page(page: pymupdf.Page, language: str = "eng", dpi: int = 200) -> str:
    """OCR a page via PyMuPDF's Tesseract integration. Raises if unavailable."""
    tp = page.get_textpage_ocr(flags=3, language=language, dpi=dpi, full=True)
    return page.get_text(textpage=tp).strip()


# ---- post-processing ----

def _strip_headers_footers(pages: list[str]) -> list[str]:
    """Drop the first/last line of each page when it repeats across most pages
    (running headers / footers / page numbers)."""
    if len(pages) < 3:
        return pages
    firsts: Counter[str] = Counter()
    lasts: Counter[str] = Counter()
    parsed: list[tuple[list[str], list[tuple[int, str]]]] = []
    for p in pages:
        lines = p.splitlines()
        non_empty = [(i, l) for i, l in enumerate(lines) if l.strip()]
        parsed.append((lines, non_empty))
        if non_empty:
            firsts[non_empty[0][1].strip()] += 1
            lasts[non_empty[-1][1].strip()] += 1
    threshold = max(2, len(pages) // 2)
    common_first = {l for l, c in firsts.items() if c >= threshold}
    common_last = {l for l, c in lasts.items() if c >= threshold}
    if not common_first and not common_last:
        return pages
    cleaned: list[str] = []
    for lines, non_empty in parsed:
        drop: set[int] = set()
        k = 0
        while k < len(non_empty) and non_empty[k][1].strip() in common_first:
            drop.add(non_empty[k][0])
            k += 1
        k = len(non_empty) - 1
        while k >= 0 and non_empty[k][1].strip() in common_last:
            drop.add(non_empty[k][0])
            k -= 1
        cleaned.append("\n".join(l for i, l in enumerate(lines) if i not in drop))
    return cleaned


def postprocess(pages: list[str], opts: ConvertOptions) -> list[str]:
    if opts.pp_strip_headers_footers:
        pages = _strip_headers_footers(pages)
    if opts.pp_merge_hyphens:
        pages = [re.sub(r"(\w)-\n(\w)", r"\1\2", p) for p in pages]
    return pages


def _assemble(pages: list[str], opts: ConvertOptions) -> str:
    parts: list[str] = []
    for k, p in enumerate(pages):
        parts.append(p)
        if opts.page_separator and k < len(pages) - 1:
            parts.append("\n---\n")
    text = "\n".join(parts)
    if opts.pp_collapse_blanks:
        text = re.sub(r"\n{3,}", "\n\n", text)
    return text


# ---------------------------------------------------------------------------
# Strikethrough detection
# ---------------------------------------------------------------------------

def _detect_strikethrough_spans(page: pymupdf.Page) -> list[str]:
    """Find substrings on this page that are visually crossed by a horizontal
    line — i.e. struck through.

    PDFs don't carry a "strikethrough" character attribute the way HTML does;
    publishers draw a thin horizontal line on top of the glyphs. We pick up
    those lines from ``page.get_drawings()`` and check whether each one passes
    through a text span's vertical middle.

    Returns the raw text of each struck span (deduplicated, longest first so
    the caller's string-replace pass can wrap the longest match before any
    contained substring)."""
    hlines: list[tuple[float, float, float]] = []   # (x0, x1, y)
    for d in page.get_drawings():
        for item in d.get("items", ()):
            kind = item[0]
            if kind == "l":                          # straight line
                p1, p2 = item[1], item[2]
                if abs(p1.y - p2.y) < 1.0 and abs(p1.x - p2.x) >= 8.0:
                    x0, x1 = sorted((p1.x, p2.x))
                    hlines.append((x0, x1, (p1.y + p2.y) / 2))
            elif kind == "re":                       # rectangle drawn as a thin bar
                r = item[1]
                if r.height < 2.0 and r.width >= 8.0:
                    hlines.append((r.x0, r.x1, (r.y0 + r.y1) / 2))
    if not hlines:
        return []

    struck: list[str] = []
    seen: set[str] = set()
    for block in page.get_text("dict").get("blocks", ()):
        if block.get("type", 0) != 0:
            continue
        for line in block.get("lines", ()):
            for span in line.get("spans", ()):
                sx0, sy0, sx1, sy1 = span["bbox"]
                height = sy1 - sy0
                ymid = (sy0 + sy1) / 2
                tol = max(2.0, height * 0.45)
                for lx0, lx1, ly in hlines:
                    if abs(ly - ymid) <= tol and lx0 < sx1 - 2 and lx1 > sx0 + 2:
                        t = span["text"].strip()
                        if t and t not in seen:
                            struck.append(t)
                            seen.add(t)
                        break
    struck.sort(key=len, reverse=True)
    return struck


def _apply_strikethrough(md: str, struck: list[str]) -> str:
    """Wrap each detected struck string in GitHub-flavoured ``~~strike~~``.

    The replacement is per-occurrence and skips strings that are already inside
    a ``~~ … ~~`` pair (idempotent on re-runs and on text that was already
    matched as a longer parent string)."""
    if not struck:
        return md
    for s in struck:
        if not s or s in ("~", "~~"):
            continue
        # ``re.escape`` is the safe way to put arbitrary text into a regex.
        pat = re.compile(rf"(?<!~){re.escape(s)}(?!~)")
        md = pat.sub(lambda m: f"~~{m.group(0)}~~", md, count=1)
    return md


# ---------------------------------------------------------------------------
# Native PyMuPDF
# ---------------------------------------------------------------------------

def _native_page_markdown(
    page: pymupdf.Page,
    image_dir: Path | None = None,
    image_dir_name: str | None = None,
) -> str | None:
    """Convert one page to Markdown via pymupdf4llm.

    When ``image_dir`` is given we let pymupdf4llm *write the page's pictures
    and vector graphics itself* (``write_images=True``). That matters for two
    reasons:

      • the image links are inserted **inline at the correct reading position**,
        so text that sits below a figure stays below it (previously every image
        was appended at the end of the page, which pushed any later text above
        the figure);
      • pymupdf4llm no longer emits its ``==> picture … intentionally omitted``
        placeholder — it only does that when images are neither written nor
        embedded.

    pymupdf4llm embeds the (absolute) path it wrote to, so we rewrite those to
    portable, URL-encoded relative refs (``./<folder>/<file>``).

    Returns ``None`` when pymupdf4llm is unavailable so the caller can fall back
    to the manual block extractor.
    """
    try:
        import pymupdf4llm  # type: ignore
    except Exception:
        return None
    kwargs: dict = {"pages": [page.number]}
    if image_dir is not None:
        image_dir.mkdir(parents=True, exist_ok=True)
        kwargs.update(
            write_images=True,
            image_path=str(image_dir),
            image_format="png",
            dpi=150,
        )
    try:
        md = pymupdf4llm.to_markdown(page.parent, **kwargs)
    except Exception:
        return None
    if image_dir is not None:
        md = _relativise_image_refs(md, image_dir, image_dir_name)
    return md


def _relativise_image_refs(
    md: str, image_dir: Path, image_dir_name: str | None
) -> str:
    """Rewrite the absolute image paths pymupdf4llm embeds into portable,
    URL-encoded relative refs so the exported .md previews everywhere
    (browsers, GitHub, Obsidian, the in-app Preview)."""
    from urllib.parse import quote
    from posixpath import basename

    def repl(m: "re.Match[str]") -> str:
        name = basename(m.group(1).replace("\\", "/"))
        if image_dir_name:
            return f"![](./{quote(image_dir_name)}/{quote(name)})"
        return f"![]({quote((image_dir / name).as_posix(), safe='/:')})"

    return re.sub(r"!\[\]\(([^)]+)\)", repl, md)


def _manual_page_markdown(page: pymupdf.Page) -> str:
    """Block-based fallback used only when pymupdf4llm is unavailable. Infers
    headings from font size and bold flags — no image handling (the caller
    appends images separately for this path)."""
    blocks = page.get_text("dict")["blocks"]
    parts: list[str] = []
    for b in blocks:
        if b.get("type", 0) != 0:
            continue
        for line in b.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            text = "".join(s["text"] for s in spans).strip()
            if not text:
                continue
            size = max((s.get("size", 0) for s in spans), default=0)
            flags = spans[0].get("flags", 0)
            bold = bool(flags & 16)
            if size >= 20:
                parts.append(f"# {text}")
            elif size >= 16:
                parts.append(f"## {text}")
            elif size >= 13:
                parts.append(f"### {text}")
            elif bold:
                parts.append(f"**{text}**")
            else:
                parts.append(text)
        parts.append("")
    return "\n".join(parts)


def convert_native(
    pdf_path: Path,
    opts: ConvertOptions,
    progress: ProgressCb | None = None,
) -> str:
    doc = _open_pdf(pdf_path)
    total = doc.page_count
    indices = _page_indices(total, opts.page_range)
    pages: list[str] = []
    for n, i in enumerate(indices):
        _check_cancel(opts)
        page = doc[i]
        if progress:
            progress(n + 1, len(indices), f"Page {i+1}/{total} (native)")
        raw = page.get_text().strip()
        img_dir = opts.image_dir if (opts.include_images and opts.image_dir is not None) else None
        if opts.ocr_enabled and len(raw) < 8:
            try:
                md = _ocr_page(page, opts.ocr_language)
            except Exception as e:  # Tesseract missing / failed — keep going
                md = f"<!-- OCR unavailable for page {i+1}: {e} -->"
            chunk = [md]
            # OCR gives no layout, so images can only be appended at the end.
            if img_dir is not None:
                _extract_images(doc, page, img_dir, opts.image_dir_name, chunk)
        else:
            md = _native_page_markdown(page, img_dir, opts.image_dir_name)
            if md is not None:
                # pymupdf4llm already inlined the images in reading order.
                chunk = [md]
            else:
                md = _manual_page_markdown(page)
                chunk = [md]
                if img_dir is not None:
                    _extract_images(doc, page, img_dir, opts.image_dir_name, chunk)
        struck = _detect_strikethrough_spans(page)
        if struck:
            chunk = [_apply_strikethrough(c, struck) for c in chunk]
        pages.append("\n".join(chunk))
    doc.close()
    pages = postprocess(pages, opts)
    return _assemble(pages, opts)


def _extract_images(
    doc: pymupdf.Document,
    page: pymupdf.Page,
    image_dir: Path,
    image_dir_name: str | None,
    out: list[str],
) -> None:
    image_dir.mkdir(parents=True, exist_ok=True)
    for img_index, info in enumerate(page.get_images(full=True)):
        xref = info[0]
        try:
            pix = pymupdf.Pixmap(doc, xref)
            if pix.n - pix.alpha >= 4:
                pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
            name = f"page{page.number+1}_img{img_index+1}.png"
            path = image_dir / name
            pix.save(str(path))
            # URL-encode each path segment so spaces / unicode / parentheses
            # in the PDF filename don't break the markdown image link in
            # downstream viewers (browsers, GitHub, Obsidian, Typora…).
            from urllib.parse import quote
            if image_dir_name:
                ref = f"./{quote(image_dir_name)}/{quote(name)}"
            else:
                ref = quote(path.as_posix(), safe="/:")
            out.append(f"\n![image]({ref})\n")
        except Exception:
            continue


# ---------------------------------------------------------------------------
# pdfplumber — offline, layout-aware extraction with table support
# ---------------------------------------------------------------------------

def _table_to_md(table: list[list[str | None]]) -> str:
    rows = [[(c or "").strip().replace("|", "\\|").replace("\n", " ") for c in row] for row in table]
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    header = rows[0]
    sep = ["---"] * width
    body = rows[1:] if len(rows) > 1 else []
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(sep) + " |",
    ]
    for r in body:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)


# Larger word-bounding tolerances than pdfplumber's defaults (3 / 3). Tight
# defaults cause cells whose visual text extends slightly past the detected
# bbox to truncate (e.g. "study from o" instead of "study from on..."). The
# user can still override these via opts.plumber_table_settings.
_DEFAULT_PDFPLUMBER_TABLE_SETTINGS = {
    "text_x_tolerance": 6,
    "text_y_tolerance": 6,
}


def _pdfplumber_extract_images_with_y(
    pdf_path: Path,
    page_index: int,
    image_dir: Path,
    image_dir_name: str | None,
) -> list[tuple[float, str]]:
    """Use PyMuPDF to write each embedded image on the page and return a list
    of ``(top_y, markdown_ref)`` so the caller can interleave images with text
    in reading order. pdfplumber doesn't extract raster images itself."""
    out: list[tuple[float, str]] = []
    try:
        d = pymupdf.open(str(pdf_path))
        page = d[page_index]
        image_dir.mkdir(parents=True, exist_ok=True)
        from urllib.parse import quote
        for img_index, info in enumerate(page.get_images(full=True)):
            xref = info[0]
            try:
                pix = pymupdf.Pixmap(d, xref)
                if pix.n - pix.alpha >= 4:
                    pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                name = f"page{page.number+1}_img{img_index+1}.png"
                path = image_dir / name
                pix.save(str(path))
                if image_dir_name:
                    ref = f"./{quote(image_dir_name)}/{quote(name)}"
                else:
                    ref = quote(path.as_posix(), safe="/:")
                # Find this image's position on the page (top y); fall back to
                # bottom of page so unplaceable images still land at the end.
                rects = page.get_image_rects(xref) or [pymupdf.Rect(0, page.rect.height, 0, page.rect.height)]
                top_y = float(rects[0].y0)
                out.append((top_y, f"\n![image]({ref})\n"))
            except Exception:
                continue
        d.close()
    except Exception:
        return out
    return out


def _pdfplumber_extract_tables_with_y(
    pdf_path: Path,
    page_index: int,
    table_settings: dict | None,
) -> list[str]:
    """Extract tables for a page using pdfplumber (same engine as the offline
    pdfplumber path) and return a list of ready-to-use GitHub-flavored markdown
    table blocks, sorted by their top y position on the page. Used by LLM/vision
    engines so they can place high-quality extracted tables while still using
    vision for overall understanding and surrounding text."""
    out: list[tuple[float, str]] = []
    try:
        import pdfplumber  # type: ignore
    except Exception:
        return []
    try:
        with pdfplumber.open(str(pdf_path)) as doc:
            if page_index >= len(doc.pages):
                return []
            page = doc.pages[page_index]
            ts = {**_DEFAULT_PDFPLUMBER_TABLE_SETTINGS, **(table_settings or {})}
            for tbl in (page.find_tables(table_settings=ts) or []):
                try:
                    rows = tbl.extract() or []
                    md = _table_to_md(rows)
                    if not md:
                        continue
                    bbox = getattr(tbl, "bbox", None)
                    top = float(bbox[1]) if bbox and len(bbox) > 1 else 0.0
                    out.append((top, "\n" + md + "\n"))
                except Exception:
                    continue
    except Exception:
        return []
    out.sort(key=lambda t: t[0])
    return [md for _, md in out]


def convert_pdfplumber(
    pdf_path: Path,
    opts: ConvertOptions,
    progress: ProgressCb | None = None,
) -> str:
    try:
        import pdfplumber  # type: ignore
    except ImportError as e:
        raise ConversionError(
            "pdfplumber is not installed. Run: pip install pdfplumber"
        ) from e

    # Merge user table settings on top of our higher-tolerance defaults so the
    # user can still override anything they want.
    table_settings = {**_DEFAULT_PDFPLUMBER_TABLE_SETTINGS, **(opts.plumber_table_settings or {})}
    pages_md: list[str] = []
    # Validate via PyMuPDF first so encrypted / corrupt PDFs raise a friendly
    # PdfError instead of a raw pdfminer exception.
    _open_pdf(pdf_path).close()
    with pdfplumber.open(str(pdf_path)) as doc:
        total = len(doc.pages)
        indices = _page_indices(total, opts.page_range)
        for n, i in enumerate(indices):
            _check_cancel(opts)
            page = doc.pages[i]
            if progress:
                progress(n + 1, len(indices), f"Page {i+1}/{total} (pdfplumber)")
            # ---- Collect (top, kind, payload) blocks to interleave by Y ----
            # Each block knows its vertical position, so text, images, and
            # tables come out in actual reading order — not all-text-then-
            # all-images-then-all-tables.
            blocks: list[tuple[float, int, str]] = []   # (top, kind_order, md)
            #  kind_order: 0 = text, 1 = table, 2 = image — used as a stable
            #  secondary sort key when two blocks share the same y.

            # 1) per-line text via extract_text_lines (each line has 'top')
            #    Fall back to one big extract_text block at y=0 if unavailable.
            text_lines: list[dict] = []
            try:
                text_lines = page.extract_text_lines() or []
            except Exception:
                text_lines = []
            if text_lines:
                for ln in text_lines:
                    t = (ln.get("text") or "").strip()
                    if t:
                        blocks.append((float(ln.get("top", 0.0)), 0, t))
            else:
                whole = (page.extract_text() or "").strip()
                if whole:
                    blocks.append((0.0, 0, whole))
                elif opts.ocr_enabled:
                    try:
                        _d = pymupdf.open(str(pdf_path))
                        ocr_text = _ocr_page(_d[i], opts.ocr_language)
                        _d.close()
                        if ocr_text:
                            blocks.append((0.0, 0, ocr_text))
                    except Exception as e:
                        blocks.append((0.0, 0, f"<!-- OCR unavailable for page {i+1}: {e} -->"))

            # 2) tables (each table object knows its bbox → top y). When a
            #    table is detected, drop any plain-text lines that fall inside
            #    its bbox so the same cells don't appear twice.
            if opts.plumber_tables_enabled:
                try:
                    found = page.find_tables(table_settings=table_settings) or []
                except Exception:
                    found = []
                for tbl in found:
                    try:
                        rows = tbl.extract()
                    except Exception:
                        rows = []
                    md_table = _table_to_md(rows)
                    if not md_table:
                        continue
                    bbox = getattr(tbl, "bbox", None)  # (x0, top, x1, bottom)
                    top = float(bbox[1]) if bbox else 0.0
                    bottom = float(bbox[3]) if bbox else top + 1.0
                    blocks.append((top, 1, "\n" + md_table + "\n"))
                    # Drop any text-line blocks that sit inside this table.
                    blocks = [
                        b for b in blocks
                        if not (b[1] == 0 and top <= b[0] <= bottom)
                    ] + [(top, 1, "\n" + md_table + "\n")]  # re-add table once
                    # de-dupe the re-add above (the list-comp re-adds nothing
                    # because the table block was already excluded — keep one):
                    seen = set()
                    deduped: list[tuple[float, int, str]] = []
                    for b in blocks:
                        key = (b[0], b[1], b[2])
                        if key in seen:
                            continue
                        seen.add(key)
                        deduped.append(b)
                    blocks = deduped

            # 3) images, placed at their actual top-y position on the page
            if opts.include_images and opts.image_dir is not None:
                for top_y, ref in _pdfplumber_extract_images_with_y(
                    pdf_path, i, opts.image_dir, opts.image_dir_name
                ):
                    blocks.append((top_y, 2, ref))

            # Sort and emit
            blocks.sort(key=lambda b: (b[0], b[1]))
            page_md = "\n\n".join(b[2] for b in blocks)

            # 4) strikethrough detection (uses PyMuPDF for the drawings layer)
            try:
                _d = pymupdf.open(str(pdf_path))
                struck = _detect_strikethrough_spans(_d[i])
                _d.close()
            except Exception:
                struck = []
            if struck:
                page_md = _apply_strikethrough(page_md, struck)

            pages_md.append(page_md)
    pages_md = postprocess(pages_md, opts)
    return _assemble(pages_md, opts)


# ---------------------------------------------------------------------------
# Page rendering helper for vision-capable LLMs
# ---------------------------------------------------------------------------

def _render_page_png_b64(page: pymupdf.Page, dpi: int = 150) -> str:
    pix = page.get_pixmap(dpi=dpi)
    data = pix.tobytes("png")
    return base64.b64encode(data).decode("ascii")


PROMPT = (
    "Convert this PDF page to clean, well-structured GitHub-flavored Markdown. "
    "Preserve headings, bullet and numbered lists, tables (as proper GitHub | markdown tables with alignment), "
    "code blocks, and inline emphasis. "
    "Break the text into natural paragraphs separated by blank lines. "
    "Wrap prose lines to a readable length (roughly 70-100 characters, similar to standard A4/Letter document text) "
    "so there are no endless long lines. Code blocks and table rows may be longer. "
    "Follow the visual reading order, column flow, and layout of the provided page image. "
    "Do not add commentary, explanations, or extra text. Output ONLY the markdown."
)

# Front-loaded instructions for vision LLM engines. These go *before* the
# main task so the model treats placement, tables, and formatting as hard
# requirements rather than after-thoughts (prevents "everything at the end"
# and endless lines).
LLM_STRUCTURE_INSTRUCTIONS = (
    "Follow these strict rules for layout fidelity and readability:\n"
    "1. IMAGE PLACEMENT (critical): The page contains precisely extracted individual figures/images (not full pages). "
    "You will be given their exact markdown links below. You MUST insert each one **inline inside the running text** "
    "at the exact visual/narrative location where the figure appears on the screenshot (right after the sentence or "
    "paragraph that refers to it). NEVER collect images at the top or very end of the page output. Interleave them.\n"
    "2. TABLE PLACEMENT (critical): You will also be given high-quality pre-extracted GitHub-flavored markdown tables "
    "(from structural pdfplumber analysis). Insert each entire table block where the table visually sits on the page. "
    "Do not move tables to the end.\n"
    "3. FORMATTING: Produce natural paragraphs separated by blank lines. Wrap ordinary text lines to ~70-100 characters "
    "so the result looks like clean A4/Letter document text (no endless long lines on any page). Code and table rows can be longer. "
    "Respect columns and reading order visible in the page image.\n"
    "4. Only improve alt text in image links (keep paths 100% identical). Output ONLY the final markdown for the page.\n\n"
)

MATH_PROMPT_ADDITION = (
    " Preserve mathematical formulas: wrap inline math with single dollar signs "
    "($x = a + b$) and display equations with double dollar signs ($$...$$). "
    "Use proper LaTeX notation."
)


def _resolve_prompt(opts: ConvertOptions) -> str:
    p = (opts.custom_prompt or "").strip() or PROMPT
    if opts.math_mode and MATH_PROMPT_ADDITION not in p:
        p = p + MATH_PROMPT_ADDITION
    return p


def is_likely_scanned(pdf_path: Path, sample_pages: int = 3, threshold: int = 50) -> bool:
    """Heuristic: very little extractable text per sampled page → probably scanned."""
    try:
        doc = pymupdf.open(pdf_path)
        n = min(sample_pages, doc.page_count)
        if n == 0:
            return False
        total = 0
        for i in range(n):
            total += len(doc[i].get_text().strip())
        doc.close()
        return total < threshold * n
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Generic LLM page runner (sequential or concurrent)
# ---------------------------------------------------------------------------

PageFn = Callable[[int, str, list[str], list[str]], str]  # (idx, b64, image_refs, table_md_blocks) -> markdown


def _run_llm(
    pdf_path: Path,
    opts: ConvertOptions,
    progress: ProgressCb | None,
    label: str,
    page_fn: PageFn,
) -> str:
    doc = _open_pdf(pdf_path)
    total = doc.page_count
    indices = _page_indices(total, opts.page_range)
    # Render all needed pages up front — PyMuPDF docs are not thread-safe, so
    # the parallel workers only ever touch the already-encoded PNG bytes.
    images: dict[int, str] = {}
    for i in indices:
        _check_cancel(opts)
        images[i] = _render_page_png_b64(doc[i])

    # For LLM/vision engines we render the full page **only** to send to the VLM
    # (so it can understand complex diagrams, layout, and reading order).
    # When include_images is on we:
    #   * Create the images/ sibling folder (matching native behavior)
    #   * Extract + save only the *precise individual embedded images* (pageNNN_imgM.png)
    #     using the same _extract_images path as the native/pdfplumber engines.
    #   * Do NOT save or reference full-page screenshots in the output .md
    #     (user explicitly does not want "the whole page image").
    #   * Pass the list of exact image markdown refs + any pre-extracted tables
    #     to the per-page call so the vision model can embed them at the visually
    #     correct positions (this + the safety post-correction below gives layout
    #     fidelity close to the original PDF and the native/pdfplumber engines).
    extracted_per_page: dict[int, list[str]] = {}
    if opts.include_images and opts.image_dir is not None:
        opts.image_dir.mkdir(parents=True, exist_ok=True)
        for page_idx in indices:
            page = doc[page_idx]
            extracted_list: list[str] = []
            _extract_images(doc, page, opts.image_dir, opts.image_dir_name, extracted_list)
            extracted_per_page[page_idx] = extracted_list

    doc.close()

    # Also extract high-quality tables via pdfplumber (when the option is enabled).
    # This lets "online" (LLM/vision) engines benefit from the same excellent
    # structural table extraction that the offline pdfplumber engine uses, while
    # the vision model still provides the overall transcription, surrounding text,
    # and placement decisions ("use the online engine" for understanding + "offline
    # pdfplumber remains" for table quality).
    tables_per_page: dict[int, list[str]] = {}
    if getattr(opts, "plumber_tables_enabled", True):
        ts = getattr(opts, "plumber_table_settings", None) or {}
        for page_idx in indices:
            try:
                tables_per_page[page_idx] = _pdfplumber_extract_tables_with_y(
                    pdf_path, page_idx, ts
                )
            except Exception:
                tables_per_page[page_idx] = []

    n_total = len(indices)
    results: dict[int, str] = {}
    concurrency = max(1, opts.llm_concurrency)

    if concurrency == 1:
        for n, i in enumerate(indices):
            _check_cancel(opts)
            if progress:
                progress(n + 1, n_total, f"Page {i+1}/{total} ({label})")
            refs = extracted_per_page.get(i, [])
            tabs = tables_per_page.get(i, [])
            results[i] = page_fn(i, images[i], refs, tabs)
    else:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        done = 0
        with ThreadPoolExecutor(max_workers=concurrency) as ex:
            futs = {
                ex.submit(page_fn, i, images[i], extracted_per_page.get(i, []), tables_per_page.get(i, [])): i
                for i in indices
            }
            try:
                for fut in as_completed(futs):
                    _check_cancel(opts)
                    results[futs[fut]] = fut.result()
                    done += 1
                    if progress:
                        progress(done, n_total, f"Page {done}/{n_total} ({label}, ×{concurrency})")
            except BaseException:
                for f in futs:
                    f.cancel()
                raise

    pages = [results[i] for i in indices]

    # No more auto-wrapping with full page images.
    # The model is given precise assets + strong rules. As a safety net for
    # "images/tables still at the very end", if none of the provided structural
    # assets appear in the LLM output we force-insert them after the first
    # paragraph so the final .md has them in the body (much better fidelity
    # than leaving everything collected at the end of a page section).
    if any(extracted_per_page.get(i) or tables_per_page.get(i) for i in indices):
        corrected: list[str] = []
        for n, i in enumerate(indices):
            text = pages[n]
            img_list = extracted_per_page.get(i, []) or []
            tbl_list = tables_per_page.get(i, []) or []
            all_assets = img_list + tbl_list
            if not all_assets:
                corrected.append(text)
                continue
            # Heuristic presence check: look for image filenames or table markers.
            present = False
            for a in all_assets:
                if ".png" in a and ("page" in a or "img" in a):
                    # crude but effective: does a path-like token from the ref appear?
                    token = a.split("(")[-1].split(")")[0] if "(" in a else a[:40]
                    if token and token in text:
                        present = True
                        break
                elif "|" in a and ("---" in a or "---|" in a):
                    if a[:30] in text or a[-30:] in text:
                        present = True
                        break
            if not present:
                # Force the precise assets into the body (after first para when possible).
                assets_joined = "\n\n" + "\n\n".join(all_assets)
                parts = re.split(r'(\n{2,})', (text or "").strip())
                if len(parts) >= 3:
                    text = parts[0] + parts[1] + assets_joined + "".join(parts[2:])
                else:
                    text = ((text or "").rstrip() + assets_joined)
            corrected.append(text)
        pages = corrected

    # The model (when given the precise refs + strong placement rules) is responsible
    # for putting assets at the right spots. The post-correction above guarantees
    # they are not stranded at the absolute end when the VLM ignores instructions.
    # Using the same structural extraction (fitz for images, pdfplumber for tables)
    # as the native/pdfplumber engines is what delivers the position/accuracy the
    # user requires.

    pages = postprocess(pages, opts)
    return _assemble(pages, opts)


# ---------------------------------------------------------------------------
# Ollama (local, offline)
# ---------------------------------------------------------------------------

def convert_ollama(
    pdf_path: Path,
    url: str,
    model: str,
    opts: ConvertOptions,
    progress: ProgressCb | None = None,
) -> str:
    base_prompt = _resolve_prompt(opts)
    streaming = opts.stream_cb is not None

    def page_fn(idx: int, img_b64: str, image_refs: list[str], table_mds: list[str]) -> str:
        p = base_prompt
        prefix = LLM_STRUCTURE_INSTRUCTIONS
        if table_mds:
            prefix += "Pre-extracted tables (insert these exact blocks where the tables appear visually):\n\n" + "\n\n".join(table_mds) + "\n\n"
        if image_refs:
            prefix += "Precise image assets (insert the links inline at the exact visual locations, improve only the [] alt text, keep (path) identical):\n\n" + "\n".join(image_refs) + "\n\n"
        if prefix.strip():
            p = prefix + base_prompt
        payload = {
            "model": model, "prompt": p,
            "images": [img_b64], "stream": streaming,
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url.rstrip("/") + "/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        if not streaming:
            with urllib.request.urlopen(req, timeout=600) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data.get("response", "")
        # Streaming: Ollama sends NDJSON lines
        out = []
        with urllib.request.urlopen(req, timeout=600) as resp:
            for raw in resp:
                if not raw.strip():
                    continue
                try:
                    d = json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    continue
                chunk = d.get("response", "")
                if chunk:
                    out.append(chunk)
                    if opts.stream_cb:
                        opts.stream_cb(idx, chunk)
                if d.get("done"):
                    break
        return "".join(out)

    return _run_llm(pdf_path, opts, progress, f"ollama:{model}", page_fn)


# ---------------------------------------------------------------------------
# OpenAI / OpenAI-compatible
# ---------------------------------------------------------------------------

def _extract_openai_content(data: dict) -> str:
    """Pull the assistant text out of a chat-completions response.

    OpenAI-compatible gateways in front of AWS Bedrock (LiteLLM, the Bedrock
    Access Gateway, etc.) do not all return an identical JSON shape, and on
    failure they often return an ``error`` object with NO ``choices`` key at
    all. Blindly indexing ``data["choices"][0]…`` then blows up with an opaque
    ``KeyError: 'choices'``. Here we surface the backend's real error message
    and accept the most common non-OpenAI shapes instead.
    """
    if not isinstance(data, dict):
        raise ConversionError(f"Unexpected response from backend: {data!r}")

    # 1) Explicit error object -> show the backend's own message.
    err = data.get("error")
    if err:
        msg = err.get("message") if isinstance(err, dict) else err
        raise ConversionError(f"Backend returned an error: {msg}")
    if "message" in data and "choices" not in data and isinstance(data.get("message"), str):
        # Some gateways return a bare {"message": "...", "code": ...} on auth/quota errors.
        raise ConversionError(f"Backend returned an error: {data['message']}")

    # 2) Standard OpenAI chat-completions shape.
    choices = data.get("choices")
    if choices:
        msg = choices[0].get("message", {})
        content = msg.get("content")
        if isinstance(content, list):  # some servers send content parts
            content = "".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        if content is not None:
            return content

    # 3) Native AWS Bedrock Converse shape: {"output":{"message":{"content":[{"text":..}]}}}
    output = data.get("output")
    if isinstance(output, dict):
        parts = output.get("message", {}).get("content", [])
        text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
        if text:
            return text

    # 4) Anthropic-on-Bedrock shape: {"content":[{"type":"text","text":..}]}
    if isinstance(data.get("content"), list):
        text = "".join(
            p.get("text", "") for p in data["content"] if isinstance(p, dict)
        )
        if text:
            return text

    # Nothing matched — show a trimmed body so the user can see what came back.
    snippet = json.dumps(data)[:500]
    raise ConversionError(
        "Could not find generated text in the backend response. "
        f"Is this really an OpenAI-compatible endpoint? Response was: {snippet}"
    )


def convert_openai_compatible(
    pdf_path: Path,
    base_url: str,
    api_key: str,
    model: str,
    opts: ConvertOptions,
    progress: ProgressCb | None = None,
) -> str:
    base_prompt = _resolve_prompt(opts)
    streaming = opts.stream_cb is not None

    def page_fn(idx: int, img_b64: str, image_refs: list[str], table_mds: list[str]) -> str:
        p = base_prompt
        prefix = LLM_STRUCTURE_INSTRUCTIONS
        if table_mds:
            prefix += "Pre-extracted tables (insert these exact blocks where the tables appear visually):\n\n" + "\n\n".join(table_mds) + "\n\n"
        if image_refs:
            prefix += "Precise image assets (insert the links inline at the exact visual locations, improve only the [] alt text, keep (path) identical):\n\n" + "\n".join(image_refs) + "\n\n"
        if prefix.strip():
            p = prefix + base_prompt
        payload = {
            "model": model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": p},
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                ],
            }],
        }
        if streaming:
            payload["stream"] = True
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            base_url.rstrip("/") + "/chat/completions",
            data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {api_key}"},
        )
        if not streaming:
            try:
                with urllib.request.urlopen(req, timeout=600) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                # Auth/quota/model errors arrive as 4xx/5xx with the real
                # message in the body — read it instead of a bare HTTP code.
                detail = e.read().decode("utf-8", "ignore")[:500]
                raise ConversionError(
                    f"Backend returned HTTP {e.code}: {detail or e.reason}"
                ) from None
            return _extract_openai_content(data)
        # Streaming: SSE — lines beginning with "data: " carry JSON deltas
        out = []
        with urllib.request.urlopen(req, timeout=600) as resp:
            for raw in resp:
                line = raw.decode("utf-8", "ignore").strip()
                if not line.startswith("data:"):
                    continue
                payload_str = line[5:].strip()
                if payload_str == "[DONE]":
                    break
                try:
                    d = json.loads(payload_str)
                except json.JSONDecodeError:
                    continue
                try:
                    chunk = d["choices"][0]["delta"].get("content", "")
                except (KeyError, IndexError):
                    chunk = ""
                if chunk:
                    out.append(chunk)
                    if opts.stream_cb:
                        opts.stream_cb(idx, chunk)
        return "".join(out)

    return _run_llm(pdf_path, opts, progress, model, page_fn)


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------

def convert_anthropic(
    pdf_path: Path,
    api_key: str,
    model: str,
    opts: ConvertOptions,
    progress: ProgressCb | None = None,
) -> str:
    base_prompt = _resolve_prompt(opts)
    streaming = opts.stream_cb is not None

    def page_fn(idx: int, img_b64: str, image_refs: list[str], table_mds: list[str]) -> str:
        p = base_prompt
        prefix = LLM_STRUCTURE_INSTRUCTIONS
        if table_mds:
            prefix += "Pre-extracted tables (insert these exact blocks where the tables appear visually):\n\n" + "\n\n".join(table_mds) + "\n\n"
        if image_refs:
            prefix += "Precise image assets (insert the links inline at the exact visual locations, improve only the [] alt text, keep (path) identical):\n\n" + "\n".join(image_refs) + "\n\n"
        if prefix.strip():
            p = prefix + base_prompt
        payload = {
            "model": model, "max_tokens": 4096,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image",
                     "source": {"type": "base64", "media_type": "image/png", "data": img_b64}},
                    {"type": "text", "text": p},
                ],
            }],
        }
        if streaming:
            payload["stream"] = True
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={"Content-Type": "application/json",
                     "x-api-key": api_key,
                     "anthropic-version": "2023-06-01"},
        )
        if not streaming:
            with urllib.request.urlopen(req, timeout=600) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            text_parts = [b.get("text", "")
                          for b in data.get("content", [])
                          if b.get("type") == "text"]
            return "".join(text_parts)
        # Streaming via SSE: content_block_delta events carry text_delta
        out = []
        with urllib.request.urlopen(req, timeout=600) as resp:
            for raw in resp:
                line = raw.decode("utf-8", "ignore").strip()
                if not line.startswith("data:"):
                    continue
                try:
                    d = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    continue
                if d.get("type") == "content_block_delta":
                    delta = d.get("delta", {})
                    if delta.get("type") == "text_delta":
                        chunk = delta.get("text", "")
                        if chunk:
                            out.append(chunk)
                            if opts.stream_cb:
                                opts.stream_cb(idx, chunk)
                if d.get("type") == "message_stop":
                    break
        return "".join(out)

    return _run_llm(pdf_path, opts, progress, model, page_fn)


# ---------------------------------------------------------------------------
# AWS Bedrock (native — talks to bedrock-runtime directly, no boto3)
# ---------------------------------------------------------------------------
#
# Uses the Bedrock *Converse* API, whose request/response shape is identical
# across model families (Claude, Nova, Llama-vision, …) so a single code path
# covers every vision model the user might pick. Authentication is AWS
# Signature Version 4, implemented here with the standard library (hmac +
# hashlib) so Distilmark stays dependency-free — no boto3 required.

_BEDROCK_SERVICE = "bedrock"


def _sigv4_sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _sigv4_signing_key(secret: str, date_stamp: str, region: str, service: str) -> bytes:
    k_date = _sigv4_sign(("AWS4" + secret).encode("utf-8"), date_stamp)
    k_region = _sigv4_sign(k_date, region)
    k_service = _sigv4_sign(k_region, service)
    return _sigv4_sign(k_service, "aws4_request")


def _bedrock_invoke(
    region: str,
    access_key: str,
    secret_key: str,
    session_token: str,
    model: str,
    body: bytes,
    timeout: int = 600,
) -> dict:
    """POST a Converse request to bedrock-runtime, SigV4-signed. Returns parsed JSON."""
    host = f"bedrock-runtime.{region}.amazonaws.com"
    # The model id can contain characters that must be percent-encoded in the
    # URL path (notably ':' in "...-v1:0" and '.' is left as-is). The path put
    # on the wire is single-encoded; SigV4 canonicalisation for non-S3 services
    # requires the path to be URI-encoded *again* (double-encoded), so e.g.
    # ':' -> '%3A' on the wire but '%253A' in the string-to-sign. Without the
    # second pass the computed signature never matches AWS's and you get
    # HTTP 403 "signature ... does not match".
    encoded_model = urllib.parse.quote(model, safe="")
    request_uri = "/model/" + encoded_model + "/converse"
    canonical_uri = "/model/" + urllib.parse.quote(encoded_model, safe="") + "/converse"
    endpoint = f"https://{host}{request_uri}"

    now = _dt.datetime.now(_dt.timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")
    payload_hash = hashlib.sha256(body).hexdigest()

    canonical_headers = (
        "content-type:application/json\n"
        f"host:{host}\n"
        f"x-amz-date:{amz_date}\n"
    )
    signed_headers = "content-type;host;x-amz-date"
    if session_token:
        canonical_headers += f"x-amz-security-token:{session_token}\n"
        signed_headers += ";x-amz-security-token"

    canonical_request = (
        "POST\n" + canonical_uri + "\n" + "\n"
        + canonical_headers + "\n" + signed_headers + "\n" + payload_hash
    )

    algorithm = "AWS4-HMAC-SHA256"
    credential_scope = f"{date_stamp}/{region}/{_BEDROCK_SERVICE}/aws4_request"
    string_to_sign = (
        algorithm + "\n" + amz_date + "\n" + credential_scope + "\n"
        + hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    )
    signing_key = _sigv4_signing_key(secret_key, date_stamp, region, _BEDROCK_SERVICE)
    signature = hmac.new(
        signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    authorization = (
        f"{algorithm} Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Amz-Date": amz_date,
        "Authorization": authorization,
    }
    if session_token:
        headers["X-Amz-Security-Token"] = session_token

    req = urllib.request.Request(endpoint, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:1000]
        msg = f"AWS Bedrock returned HTTP {e.code}: {detail or e.reason}"
        if e.code in (401, 403) and canonical_request:
            # Include what we actually signed for easier debugging of SigV4 issues.
            # (The secret key itself is never in the canonical string.)
            msg += "\n\n[App debug] Canonical request we calculated:\n" + canonical_request
            # Also show the string-to-sign and the signature *we* produced (for comparison).
            # This helps distinguish "bad canonical" vs "bad secret key".
            string_to_sign = (
                "AWS4-HMAC-SHA256\n" + amz_date + "\n" + credential_scope + "\n"
                + hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
            )
            our_signature = hmac.new(
                signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
            ).hexdigest()
            msg += "\n[App debug] String-to-Sign we used:\n" + string_to_sign
            msg += "\n[App debug] Signature we calculated: " + our_signature
        raise ConversionError(msg) from None


def convert_bedrock(
    pdf_path: Path,
    region: str,
    access_key: str,
    secret_key: str,
    model: str,
    opts: ConvertOptions,
    progress: ProgressCb | None = None,
    session_token: str = "",
) -> str:
    base_prompt = _resolve_prompt(opts)
    if not (region and access_key and secret_key and model):
        raise ConversionError(
            "AWS Bedrock needs Region, Access key, Secret key and a Model id. "
            "Fill them in under Settings → AWS Bedrock."
        )

    def page_fn(idx: int, img_b64: str, image_refs: list[str], table_mds: list[str]) -> str:
        p = base_prompt
        prefix = LLM_STRUCTURE_INSTRUCTIONS
        if table_mds:
            prefix += "Pre-extracted tables (insert these exact blocks where the tables appear visually):\n\n" + "\n\n".join(table_mds) + "\n\n"
        if image_refs:
            prefix += "Precise image assets (insert the links inline at the exact visual locations, improve only the [] alt text, keep (path) identical):\n\n" + "\n".join(image_refs) + "\n\n"
        if prefix.strip():
            p = prefix + base_prompt
        payload = {
            "messages": [{
                "role": "user",
                "content": [
                    {"image": {"format": "png", "source": {"bytes": img_b64}}},
                    {"text": p},
                ],
            }],
            "inferenceConfig": {"maxTokens": 4096},
        }
        body = json.dumps(payload).encode("utf-8")
        data = _bedrock_invoke(
            region, access_key, secret_key, session_token, model, body
        )
        parts = data.get("output", {}).get("message", {}).get("content", [])
        text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
        if not text:
            snippet = json.dumps(data)[:500]
            raise ConversionError(f"Bedrock returned no text. Response: {snippet}")
        return text

    # Bedrock streaming uses the binary event-stream protocol; not supported here.
    return _run_llm(pdf_path, opts, progress, f"bedrock:{model}", page_fn)


# ---------------------------------------------------------------------------
# Cost estimation (rough — for hosted LLM engines only)
# ---------------------------------------------------------------------------

# Approximate USD prices per 1K tokens: (input, output). Matched by substring.
LLM_PRICES: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4o": (0.0025, 0.01),
    "gpt-4.1-mini": (0.0004, 0.0016),
    "gpt-4.1": (0.002, 0.008),
    "claude-haiku": (0.0008, 0.004),
    "claude-sonnet": (0.003, 0.015),
    "claude-opus": (0.015, 0.075),
    # Bedrock model ids embed the family name differently (e.g.
    # anthropic.claude-3-5-sonnet-…, amazon.nova-pro-…) — match on the family.
    "haiku": (0.0008, 0.004),
    "sonnet": (0.003, 0.015),
    "opus": (0.015, 0.075),
    "nova-micro": (0.000035, 0.00014),
    "nova-lite": (0.00006, 0.00024),
    "nova-pro": (0.0008, 0.0032),
}

# rough vision tokens consumed by one rendered page image, plus typical output
_IMG_TOKENS = 1100
_AVG_OUTPUT_TOKENS = 700


def _price_for(model: str) -> tuple[float, float]:
    m = (model or "").lower()
    for key, price in LLM_PRICES.items():
        if key in m:
            return price
    return (0.001, 0.004)  # generic fallback


def estimate_cost(engine: str, model: str, total_pages: int) -> float | None:
    """Return a rough USD estimate, or None for free/offline engines."""
    if engine in ("native", "pdfplumber", "compare", "ollama"):
        return None
    inp, out = _price_for(model)
    return total_pages * (_IMG_TOKENS / 1000 * inp + _AVG_OUTPUT_TOKENS / 1000 * out)


def count_pages(pdf_path: Path) -> int:
    try:
        doc = pymupdf.open(pdf_path)
        n = doc.page_count
        doc.close()
        return n
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Ollama helpers
# ---------------------------------------------------------------------------

def list_ollama_models(url: str) -> list[str]:
    try:
        req = urllib.request.Request(url.rstrip("/") + "/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return [m["name"] for m in data.get("models", [])]
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return []


PullProgressCb = Callable[[str, int, int], None]  # (status, total, completed)


def pull_ollama_model(
    url: str,
    model: str,
    progress_cb: PullProgressCb,
) -> None:
    """Stream-pull an Ollama model. Calls progress_cb for each progress line."""
    payload = {"name": model, "stream": True}
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url.rstrip("/") + "/api/pull",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=7200) as resp:
        for raw in resp:
            raw = raw.strip()
            if not raw:
                continue
            try:
                d = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                continue
            progress_cb(
                d.get("status", ""),
                d.get("total", 0),
                d.get("completed", 0),
            )
