#!/usr/bin/env python3
"""Zero-dependency Amazon KDP spine, cover-wrap, margin, and preflight CLI.

Matches Amazon KDP paperback and hardcover (case laminate) specifications:
- https://kdp.amazon.com/en_US/help/topic/G201953020
- https://kdp.amazon.com/en_US/help/topic/G201834180

Usage:
  kdp-preflight pdf manuscript.pdf --paper white
  kdp-preflight cover --trim 5.5x8.5 --pages 174 --paper white
  kdp-preflight cover --trim 6x9 --pages 300 --paper cream --binding hardcover
  kdp-preflight check --trim 6x9 --pages 320 --paper white --inside 0.5 --outside 0.5
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zlib
from pathlib import Path
from typing import Any

MM_TO_IN = 1.0 / 25.4
PAPER = {"white": 0.002252, "cream": 0.0025}
BLEED = 0.125
SPINE_TEXT_MIN_PAPERBACK = 79
CASE = {
    "wrap": 15 * MM_TO_IN,
    "side": 5 * MM_TO_IN,
    "top": 3 * MM_TO_IN,
    "hinge": 10 * MM_TO_IN,
    "spine": 0.189,
    "clear": 0.125,
    "min_pages": 75,
    "max_pages": 550,
}
CASE_TRIMS = [(5.5, 8.5), (6.0, 9.0), (6.14, 9.21), (7.0, 10.0), (8.25, 11.0)]
MIN_DPI = 300


def parse_pair(val: str) -> tuple[float, float]:
    cleaned = val.lower().replace("×", "x").replace(" ", "")
    parts = cleaned.split("x")
    if len(parts) != 2:
        raise ValueError(f"Expected WxH (e.g. 6x9), got: {val}")
    return float(parts[0]), float(parts[1])


def kdp_inside_min(pages: int) -> float:
    if pages <= 150:
        return 0.375
    if pages <= 300:
        return 0.5
    if pages <= 500:
        return 0.625
    if pages <= 700:
        return 0.75
    return 0.875


def kdp_page_range(paper: str, binding: str) -> tuple[int, int]:
    if binding == "hardcover":
        return CASE["min_pages"], CASE["max_pages"]
    return 24, 776 if paper == "cream" else 828


def compute_cover(trim_w: float, trim_h: float, pages: int, paper: str = "white", binding: str = "paperback") -> dict[str, Any]:
    if paper not in PAPER:
        raise ValueError(f"paper must be 'white' or 'cream', got {paper}")
    if binding not in {"paperback", "hardcover"}:
        raise ValueError(f"binding must be 'paperback' or 'hardcover', got {binding}")

    even_pages = pages + (pages % 2)
    hard = binding == "hardcover"
    spine = even_pages * PAPER[paper] + (CASE["spine"] if hard else 0.0)
    edge = CASE["wrap"] if hard else BLEED
    pw = trim_w + CASE["side"] if hard else trim_w
    ph = trim_h + 2 * CASE["top"] if hard else trim_h
    wrap_w = 2 * (pw + edge) + spine
    wrap_h = ph + 2 * edge
    spine_text_allowed = True if hard else even_pages >= SPINE_TEXT_MIN_PAPERBACK

    return {
        "binding": binding,
        "paper": paper,
        "trim_in": [round(trim_w, 3), round(trim_h, 3)],
        "pages_input": pages,
        "pages_even": even_pages,
        "spine_in": round(spine, 3),
        "wrap_width_in": round(wrap_w, 3),
        "wrap_height_in": round(wrap_h, 3),
        "spine_text_allowed": spine_text_allowed,
        "min_inside_margin_in": kdp_inside_min(even_pages),
        "page_range": list(kdp_page_range(paper, binding)),
    }


def run_preflight(
    trim_w: float,
    trim_h: float,
    pages: int,
    paper: str = "white",
    binding: str = "paperback",
    inside: float | None = None,
    outside: float | None = None,
    bleed: bool = False,
    image_px: tuple[float, float] | None = None,
    image_in: tuple[float, float] | None = None,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    min_p, max_p = kdp_page_range(paper, binding)
    checks.append(
        {
            "id": "page-count",
            "ok": min_p <= pages <= max_p,
            "message": f"{pages} pages is within KDP {binding} ({paper}) range {min_p}-{max_p}."
            if min_p <= pages <= max_p
            else f"{pages} pages is outside KDP {binding} ({paper}) range {min_p}-{max_p}.",
        }
    )

    if binding == "hardcover":
        trim_ok = any(abs(trim_w - w) < 1e-3 and abs(trim_h - h) < 1e-3 for w, h in CASE_TRIMS)
        checks.append(
            {
                "id": "hardcover-trim",
                "ok": trim_ok,
                "message": f"{trim_w}x{trim_h} in is a supported KDP hardcover trim."
                if trim_ok
                else f"KDP hardcover only supports: {', '.join(f'{w}x{h}' for w, h in CASE_TRIMS)} in.",
            }
        )
    else:
        trim_ok = 4.0 <= trim_w <= 8.5 and 6.0 <= trim_h <= 11.69
        checks.append(
            {
                "id": "paperback-trim",
                "ok": trim_ok,
                "message": f"{trim_w}x{trim_h} in is within KDP paperback bounds (4-8.5 x 6-11.69 in)."
                if trim_ok
                else f"{trim_w}x{trim_h} in is outside KDP paperback bounds (4-8.5 x 6-11.69 in).",
            }
        )

    req_in = kdp_inside_min(pages)
    if inside is not None:
        checks.append(
            {
                "id": "inside-margin",
                "ok": inside >= req_in,
                "message": f"Inside margin {inside} in meets KDP minimum {req_in} in for {pages} pages."
                if inside >= req_in
                else f"Inside margin {inside} in is below KDP minimum {req_in} in for {pages} pages.",
            }
        )

    req_out = 0.375 if bleed else 0.25
    if outside is not None:
        checks.append(
            {
                "id": "outside-margin",
                "ok": outside >= req_out,
                "message": f"Outside margin {outside} in meets KDP minimum {req_out} in ({'bleed' if bleed else 'no bleed'})."
                if outside >= req_out
                else f"Outside margin {outside} in is below KDP minimum {req_out} in ({'bleed' if bleed else 'no bleed'}).",
            }
        )

    if image_px and image_in:
        dpi = round(min(image_px[0] / image_in[0], image_px[1] / image_in[1]))
        checks.append(
            {
                "id": "image-dpi",
                "ok": dpi >= MIN_DPI,
                "message": f"Image prints at {dpi} dpi (minimum {MIN_DPI} dpi)."
                if dpi >= MIN_DPI
                else f"Image prints at {dpi} dpi; KDP requires at least {MIN_DPI} dpi.",
            }
        )

    return checks


_PDF_BOX_RE = re.compile(rb"/(TrimBox|MediaBox)\s*\[\s*([+-]?\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)\s*\]")
_PDF_PAGES_COUNT_RE = re.compile(rb"/Type\s*/Pages\b[^>]*?/Count\s+(\d+)|/Count\s+(\d+)[^>]*?/Type\s*/Pages\b", re.S)
_PDF_PAGE_LEAF_RE = re.compile(rb"/Type\s*/Page(?![A-Za-z])")
_PDF_OBJSTM_RE = re.compile(rb"<<([^>]*/Type\s*/ObjStm[^>]*)>>\s*stream\r?\n(.*?)\r?\nendstream", re.S)


def _extract_pdf_text_blobs(raw: bytes) -> list[bytes]:
    blobs = [raw]
    for m in _PDF_OBJSTM_RE.finditer(raw):
        dict_bytes, stream_bytes = m.group(1), m.group(2)
        if b"/FlateDecode" in dict_bytes:
            try:
                blobs.append(zlib.decompress(stream_bytes))
            except zlib.error:
                continue
        else:
            blobs.append(stream_bytes)
    return blobs


def inspect_pdf(path: Path) -> dict[str, Any]:
    """Read page count and page trim dimensions (inches) from a PDF with zero third-party deps."""
    raw = path.read_bytes()
    if not raw.startswith(b"%PDF-"):
        raise ValueError(f"Not a valid PDF file: {path}")

    blobs = _extract_pdf_text_blobs(raw)
    combined = b"\n".join(blobs)

    counts = [int(m.group(1) or m.group(2)) for m in _PDF_PAGES_COUNT_RE.finditer(combined)]
    leaf_pages = len(_PDF_PAGE_LEAF_RE.findall(combined))
    pages = max(counts) if counts else leaf_pages
    if pages <= 0:
        raise ValueError(f"Could not determine page count in {path} (encrypted or unsupported PDF).")

    trim_boxes: list[tuple[float, float]] = []
    media_boxes: list[tuple[float, float]] = []
    for m in _PDF_BOX_RE.finditer(combined):
        kind = m.group(1)
        x0, y0, x1, y1 = (float(m.group(i)) for i in (2, 3, 4, 5))
        w_in = round(abs(x1 - x0) / 72.0, 3)
        h_in = round(abs(y1 - y0) / 72.0, 3)
        if w_in > 0 and h_in > 0:
            (trim_boxes if kind == b"TrimBox" else media_boxes).append((w_in, h_in))

    boxes = trim_boxes or media_boxes
    if not boxes:
        raise ValueError(f"Could not determine MediaBox/TrimBox dimensions in {path}.")

    unique_sizes = sorted(set(boxes))
    primary_w, primary_h = boxes[0]
    return {
        "file": str(path),
        "pages": pages,
        "box_source": "TrimBox" if trim_boxes else "MediaBox",
        "size_in": [primary_w, primary_h],
        "mixed_page_sizes": len(unique_sizes) > 1,
        "unique_sizes_in": [[w, h] for w, h in unique_sizes],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Amazon KDP spine, cover wrap, PDF inspector, and preflight CLI.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_pdf = sub.add_parser("pdf", help="Inspect a real PDF file for page count, trim size, KDP cover wrap, and preflight checks.")
    p_pdf.add_argument("file", type=Path, help="Path to interior PDF manuscript.")
    p_pdf.add_argument("--paper", choices=["white", "cream"], default="white")
    p_pdf.add_argument("--binding", choices=["paperback", "hardcover"], default="paperback")
    p_pdf.add_argument("--bleed", action="store_true", help="PDF includes KDP bleed (+0.125 in width, +0.25 in height); subtracts bleed to infer trim size.")
    p_pdf.add_argument("--json", action="store_true")

    p_cov = sub.add_parser("cover", help="Calculate KDP spine width, wrap dimensions, and minimum inside margin.")
    p_cov.add_argument("--trim", required=True, help="Trim size in inches, e.g. 5.5x8.5 or 6x9.")
    p_cov.add_argument("--pages", type=int, required=True, help="Interior page count.")
    p_cov.add_argument("--paper", choices=["white", "cream"], default="white")
    p_cov.add_argument("--binding", choices=["paperback", "hardcover"], default="paperback")
    p_cov.add_argument("--json", action="store_true")

    p_chk = sub.add_parser("check", help="Validate KDP page count, trim, margins, and image DPI.")
    p_chk.add_argument("--trim", required=True, help="Trim size in inches, e.g. 6x9.")
    p_chk.add_argument("--pages", type=int, required=True, help="Interior page count.")
    p_chk.add_argument("--paper", choices=["white", "cream"], default="white")
    p_chk.add_argument("--binding", choices=["paperback", "hardcover"], default="paperback")
    p_chk.add_argument("--inside", type=float, help="Inside (gutter) margin in inches.")
    p_chk.add_argument("--outside", type=float, help="Outside margin in inches.")
    p_chk.add_argument("--bleed", action="store_true", help="Interior uses bleed (raises outside margin min to 0.375 in).")
    p_chk.add_argument("--image-px", help="Image pixel dimensions WxH, e.g. 1800x2700.")
    p_chk.add_argument("--image-in", help="Printed image size in inches WxH, e.g. 6x9.")
    p_chk.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)

    if args.cmd == "pdf":
        info = inspect_pdf(args.file)
        raw_w, raw_h = info["size_in"]
        tw = round(raw_w - (BLEED if args.bleed else 0.0), 3)
        th = round(raw_h - (2 * BLEED if args.bleed else 0.0), 3)
        cover = compute_cover(tw, th, info["pages"], args.paper, args.binding)
        checks = run_preflight(tw, th, info["pages"], args.paper, args.binding, bleed=args.bleed)
        if info["mixed_page_sizes"]:
            checks.append({
                "id": "uniform-page-size",
                "ok": False,
                "message": f"Mixed page sizes found in PDF: {info['unique_sizes_in']} in (KDP requires uniform trim).",
            })
        else:
            checks.append({
                "id": "uniform-page-size",
                "ok": True,
                "message": f"All pages share uniform {info['box_source']} size {raw_w} x {raw_h} in.",
            })
        if args.json:
            print(json.dumps({"pdf": info, "cover": cover, "checks": checks}, indent=2))
        else:
            print(f"PDF:            {info['file']}")
            print(f"Detected:       {info['pages']} pages · {raw_w} x {raw_h} in ({info['box_source']})")
            print(f"Trim inferred:  {tw} x {th} in ({'bleed subtracted' if args.bleed else 'no bleed'})")
            print(f"Spine width:    {cover['spine_in']:.3f} in ({args.binding}, {args.paper})")
            print(f"Full cover:     {cover['wrap_width_in']:.3f} x {cover['wrap_height_in']:.3f} in")
            print(f"Min inside mgn: {cover['min_inside_margin_in']} in")
            for c in checks:
                print(f"[{'PASS' if c['ok'] else 'FAIL'}] {c['id']}: {c['message']}")
        return 0 if all(c["ok"] for c in checks) else 1

    tw, th = parse_pair(args.trim)

    if args.cmd == "cover":
        res = compute_cover(tw, th, args.pages, args.paper, args.binding)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"Binding:        {res['binding']} ({res['paper']} paper)")
            print(f"Trim:           {res['trim_in'][0]} x {res['trim_in'][1]} in")
            print(f"Pages (even):   {res['pages_even']} (allowed {res['page_range'][0]}-{res['page_range'][1]})")
            print(f"Spine width:    {res['spine_in']:.3f} in")
            print(f"Full cover:     {res['wrap_width_in']:.3f} x {res['wrap_height_in']:.3f} in")
            print(f"Spine text:     {'allowed' if res['spine_text_allowed'] else 'not allowed (<79 pages)'}")
            print(f"Min inside mgn: {res['min_inside_margin_in']} in")
        return 0

    img_px = parse_pair(args.image_px) if args.image_px else None
    img_in = parse_pair(args.image_in) if args.image_in else None
    checks = run_preflight(tw, th, args.pages, args.paper, args.binding, args.inside, args.outside, args.bleed, img_px, img_in)
    if args.json:
        print(json.dumps(checks, indent=2))
    else:
        for c in checks:
            tag = "PASS" if c["ok"] else "FAIL"
            print(f"[{tag}] {c['id']}: {c['message']}")
    return 0 if all(c["ok"] for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
