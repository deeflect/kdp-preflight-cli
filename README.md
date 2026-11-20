# KDP Preflight CLI & Rules (`kdp-preflight-cli`)

Zero-dependency Python CLI and machine-readable JSON rules (`kdp-rules.json`) for calculating **Amazon KDP paperback & hardcover spine width**, **full cover wrap size**, **minimum inside (gutter) margins**, and **300 DPI image checks** before you upload to KDP.

## Quick start

Requires Python 3.10+. No external packages.

```bash
# Paperback cover wrap + spine calculation (5.5 × 8.5 in, 174 pages, white paper)
python3 kdp_preflight.py cover --trim 5.5x8.5 --pages 174 --paper white

# Hardcover (case laminate) cover wrap (6 × 9 in, 300 pages, cream paper)
python3 kdp_preflight.py cover --trim 6x9 --pages 300 --paper cream --binding hardcover

# Preflight check on margins, page range, trim, and image resolution
python3 kdp_preflight.py check --trim 6x9 --pages 320 --paper white --inside 0.625 --outside 0.5 --image-px 1800x2700 --image-in 6x9

# JSON output for scripts or build pipelines
python3 kdp_preflight.py cover --trim 6x9 --pages 250 --paper cream --json
```

---

## Amazon KDP reference rules

### Minimum inside (gutter) margin by page count
| Pages | Minimum inside margin | Outside margin (no bleed) | Outside margin (with bleed) |
|---|---:|---:|---:|
| 24–150 | `0.375 in` | `0.25 in` | `0.375 in` |
| 151–300 | `0.500 in` | `0.25 in` | `0.375 in` |
| 301–500 | `0.625 in` | `0.25 in` | `0.375 in` |
| 501–700 | `0.750 in` | `0.25 in` | `0.375 in` |
| 701–828 | `0.875 in` | `0.25 in` | `0.375 in` |

### Spine thickness & page limits (black-and-white interior)
- **White paper:** `0.002252 in` per page · Paperback `24–828` pages
- **Cream paper:** `0.002500 in` per page · Paperback `24–776` pages
- **Spine text minimum (paperback):** `79` pages (with `0.0625 in` clearance to each fold)
- **Hardcover (case laminate):** `75–550` pages · `0.189 in` added to spine · supported trims: `5.5×8.5`, `6×9`, `6.14×9.21`, `7×10`, `8.25×11` in
- **Images:** minimum `300 dpi` at printed size

All formulas match Amazon KDP's cover calculator ([G201953020](https://kdp.amazon.com/en_US/help/topic/G201953020), [G201834180](https://kdp.amazon.com/en_US/help/topic/G201834180)).

---

## FAQ

### What is the KDP minimum inside (gutter) margin by page count?
Amazon KDP steps the minimum inside margin up with page count: `0.375 in` (24–150 pages), `0.5 in` (151–300 pages), `0.625 in` (301–500 pages), `0.75 in` (501–700 pages), and `0.875 in` (701–828 pages).

### How do I calculate Amazon KDP paperback and hardcover spine width?
Multiply your even page count by `0.002252 in` for white paper or `0.0025 in` for cream paper. For KDP case-laminate hardcovers (75–550 pages), add `0.189 in` to the paperback spine width. Run `python3 kdp_preflight.py cover --trim 5.5x8.5 --pages 174 --paper white` for exact wrap dimensions.

### What causes most KDP paperback upload rejections?
The top three triggers are inside margins too narrow for the final page count, outside text crossing the `0.25 in` (`0.375 in` with bleed) safe zone, and images below `300 dpi` at print size. [Glava](https://getglava.app) runs these KDP checks live in the browser before exporting your print PDF, cover wrap, and EPUB 3.

---

## Want automatic KDP typesetting + cover wrap in the browser?

If you want to drop in a `.docx` or Markdown manuscript and export a KDP-checked interior PDF, full cover wrap PDF, and EPUB 3 directly in your browser (Windows, Mac, Linux), check out **[Glava](https://getglava.app)**.

## License

MIT
