// Turns a list of simple blocks (headings, paragraphs, lists, tables, images) into a real PDF
// with selectable text. Fonts are Noto Sans, subset to Latin + Turkish, embedded so ş ğ İ ı render.
//
// Block shapes:
//   { t: "h", level: 1..6, runs }          { t: "p", runs }
//   { t: "li", runs, ordered, n, depth }   { t: "pre", text }
//   { t: "table", rows: string[][], header: boolean }
//   { t: "img", bytes: Uint8Array, mime: "image/png" | "image/jpeg" }
//   { t: "note", text }                    { t: "pagebreak" }
// runs: [{ text, bold }]

import { PDFDocument, rgb } from "pdf-lib";
import fontkit from "@pdf-lib/fontkit";

const A4 = [595.28, 841.89];
const MARGIN = 51; // 18 mm
const HEADING_SIZE = { 1: 20, 2: 15, 3: 12.5, 4: 11.5, 5: 11, 6: 11 };
const TEXT = rgb(0.07, 0.07, 0.07);
const MUTED = rgb(0.4, 0.4, 0.4);
const GRID = rgb(0.6, 0.65, 0.63);
const HEAD_FILL = rgb(0.933, 0.949, 0.941);

let fontLoader = async (weight) => {
  const res = await fetch(`${import.meta.env?.BASE_URL ?? "/"}fonts/NotoSans-${weight}.subset.ttf`);
  if (!res.ok) throw new Error(`font ${weight} failed to load (${res.status})`);
  return res.arrayBuffer();
};
let fontCache = null;

/** Tests (no fetch/DOM) inject their own loader. */
export function setFontLoader(fn) {
  fontLoader = fn;
  fontCache = null;
}

async function loadFontBytes() {
  fontCache ??= Promise.all([fontLoader("Regular"), fontLoader("Bold")]);
  return fontCache;
}

export async function blocksToPdf(blocks, { landscape = false, title = "" } = {}) {
  const doc = await PDFDocument.create();
  doc.registerFontkit(fontkit);
  const [regular, bold] = await loadFontBytes();
  const fonts = {
    regular: await doc.embedFont(regular, { subset: true }),
    bold: await doc.embedFont(bold, { subset: true }),
  };
  const r = new Renderer(doc, fonts, landscape);
  for (const b of blocks) await r.block(b);
  doc.setProducer("Triton");
  doc.setCreator("Triton");
  if (title) doc.setTitle(title);
  return doc.save();
}

class Renderer {
  constructor(doc, fonts, landscape) {
    this.doc = doc;
    this.fonts = fonts;
    [this.pw, this.ph] = landscape ? [A4[1], A4[0]] : A4;
    this.cw = this.pw - MARGIN * 2;
    this.newPage();
  }

  newPage() {
    this.page = this.doc.addPage([this.pw, this.ph]);
    this.y = MARGIN;
  }

  room() {
    return this.ph - MARGIN - this.y;
  }

  atTop() {
    return this.y <= MARGIN + 0.5;
  }

  sanitize(s) {
    return String(s ?? "")
      .replace(/\t/g, "    ")
      .replace(/[\u0000-\u0008\u000B-\u001F\u007F]/g, " ");
  }

  width(text, bold, size) {
    return this.fonts[bold ? "bold" : "regular"].widthOfTextAtSize(text, size);
  }

  /** Word-wrap runs into lines of tokens that each fit in maxW. */
  wrap(runs, size, maxW) {
    const tokens = [];
    for (const run of runs) {
      for (const part of this.sanitize(run.text).split(/(\n|[  ]+)/)) {
        if (part === "") continue;
        if (part === "\n") tokens.push({ nl: true });
        else if (/^[  ]+$/.test(part)) tokens.push({ text: " ", bold: !!run.bold, space: true });
        else tokens.push({ text: part, bold: !!run.bold, space: false });
      }
    }

    const lines = [];
    let cur = [];
    let curW = 0;
    const flush = () => {
      while (cur.length && cur[cur.length - 1].space) cur.pop();
      lines.push(cur);
      cur = [];
      curW = 0;
    };

    for (const tok of tokens) {
      if (tok.nl) {
        flush();
        continue;
      }
      const w = this.width(tok.text, tok.bold, size);
      if (tok.space) {
        if (cur.length) {
          cur.push({ ...tok, w });
          curW += w;
        }
        continue;
      }
      if (curW + w <= maxW) {
        cur.push({ ...tok, w });
        curW += w;
        continue;
      }
      if (cur.length) flush();
      if (w <= maxW) {
        cur.push({ ...tok, w });
        curW = w;
        continue;
      }
      // one word wider than the whole line (a URL, a long id): split by characters
      let chunk = "";
      for (const ch of tok.text) {
        if (chunk && this.width(chunk + ch, tok.bold, size) > maxW) {
          cur.push({ text: chunk, bold: tok.bold, w: this.width(chunk, tok.bold, size) });
          flush();
          chunk = ch;
        } else chunk += ch;
      }
      if (chunk) {
        const cw = this.width(chunk, tok.bold, size);
        cur.push({ text: chunk, bold: tok.bold, w: cw });
        curW = cw;
      }
    }
    if (cur.length || !lines.length) flush();
    return lines;
  }

  /** Draw one wrapped line with its top edge at `top` (distance from the page top). */
  drawLine(line, x, top, size, color = TEXT) {
    const baseline = this.ph - (top + size * 1.09);
    let cx = x;
    let buf = "";
    let bufBold = null;
    let bufX = x;
    const emit = () => {
      if (buf) {
        this.page.drawText(buf, { x: bufX, y: baseline, size, font: this.fonts[bufBold ? "bold" : "regular"], color });
      }
      buf = "";
    };
    for (const tok of line) {
      if (bufBold !== null && tok.bold !== bufBold) emit();
      if (!buf) {
        bufBold = tok.bold;
        bufX = cx;
      }
      buf += tok.text;
      cx += tok.w;
    }
    emit();
  }

  paragraph(runs, size, { before = 0, after = 6, indent = 0, marker = "", color = TEXT, keep = 0 } = {}) {
    const lh = size * 1.4;
    const lines = this.wrap(runs, size, this.cw - indent);
    if (keep) this.ensureRoom(Math.min(lh * (lines.length || 1), lh * keep) + before);
    if (!this.atTop()) this.y += before;
    lines.forEach((line, i) => {
      if (this.y + lh > this.ph - MARGIN) this.newPage();
      if (i === 0 && marker) {
        this.page.drawText(marker, {
          x: MARGIN + indent - this.width(marker, false, size) - 5,
          y: this.ph - (this.y + size * 1.09),
          size,
          font: this.fonts.regular,
          color,
        });
      }
      this.drawLine(line, MARGIN + indent, this.y, size, color);
      this.y += lh;
    });
    this.y += after;
  }

  ensureRoom(h) {
    if (h > this.room() && !this.atTop()) this.newPage();
  }

  async block(b) {
    switch (b.t) {
      case "h": {
        const size = HEADING_SIZE[b.level] ?? 11;
        this.paragraph((b.runs ?? []).map((r) => ({ ...r, bold: true })), size, {
          before: size * 0.9,
          after: size * 0.35,
          keep: 3,
        });
        break;
      }
      case "p":
        this.paragraph(b.runs ?? [], 11, { after: 7 });
        break;
      case "li":
        this.paragraph(b.runs ?? [], 11, {
          indent: 18 + (b.depth ?? 0) * 18,
          marker: b.ordered ? `${b.n}.` : "•",
          after: 3,
        });
        break;
      case "note":
        this.paragraph([{ text: b.text }], 9, { color: MUTED, after: 6 });
        break;
      case "pre": {
        const lines = this.wrap([{ text: b.text }], 10, this.cw);
        const lh = 14;
        for (const line of lines) {
          if (this.y + lh > this.ph - MARGIN) this.newPage();
          this.drawLine(line, MARGIN, this.y, 10);
          this.y += lh;
        }
        this.y += 6;
        break;
      }
      case "table":
        this.table(b);
        break;
      case "img":
        await this.image(b);
        break;
      case "pagebreak":
        if (!this.atTop()) this.newPage();
        break;
      default:
        break;
    }
  }

  async image(b) {
    let img;
    try {
      img = b.mime === "image/png" ? await this.doc.embedPng(b.bytes) : await this.doc.embedJpg(b.bytes);
    } catch {
      return; // a damaged picture shouldn't sink the whole document
    }
    const maxH = (this.ph - MARGIN * 2) * 0.9;
    const scale = Math.min(1, this.cw / (img.width * 0.75), maxH / (img.height * 0.75));
    const w = img.width * 0.75 * scale;
    const h = img.height * 0.75 * scale;
    this.ensureRoom(h + 6);
    if (h > this.room()) this.newPage();
    this.page.drawImage(img, { x: MARGIN, y: this.ph - (this.y + h), width: w, height: h });
    this.y += h + 8;
  }

  table(b) {
    const rows = b.rows.filter((r) => r.length);
    if (!rows.length) return;
    const ncol = Math.max(...rows.map((r) => r.length));
    const size = b.size ?? (ncol > 8 ? 8 : ncol > 5 ? 9 : 10);
    const padX = 4;
    const padY = 3;
    const lh = size * 1.35;

    const minW = Array(ncol).fill(20);
    const prefW = Array(ncol).fill(0);
    rows.forEach((row, ri) => {
      const bold = !!b.header && ri === 0;
      for (let c = 0; c < ncol; c++) {
        const text = this.sanitize(row[c] ?? "");
        prefW[c] = Math.max(prefW[c], this.width(text.replace(/\n/g, " "), bold, size));
        const longest = Math.max(0, ...text.split(/\s+/).map((w) => this.width(w, bold, size)));
        minW[c] = Math.max(minW[c], Math.min(longest, 110));
      }
    });

    const sum = (a) => a.reduce((x, y) => x + y, 0);
    let widths = prefW.map((p, i) => Math.max(minW[i], p) + padX * 2);
    const total = sum(widths);
    if (total > this.cw) {
      const floor = minW.map((m) => m + padX * 2);
      const flex = widths.map((w, i) => w - floor[i]);
      const over = total - this.cw;
      widths = sum(flex) >= over && sum(flex) > 0
        ? widths.map((w, i) => w - (over * flex[i]) / sum(flex))
        : floor.map((w) => (w * this.cw) / sum(floor));
    } else {
      const extra = this.cw - total;
      const basis = sum(prefW) || 1;
      widths = widths.map((w, i) => w + (extra * prefW[i]) / basis);
    }

    const layoutRow = (row, ri) => {
      const bold = !!b.header && ri === 0;
      const cells = widths.map((w, c) => this.wrap([{ text: row[c] ?? "", bold }], size, w - padX * 2));
      const maxLines = Math.max(1, Math.floor((this.ph - MARGIN * 2 - padY * 2) / lh));
      const lines = Math.min(maxLines, Math.max(...cells.map((l) => l.length)));
      return { cells, height: lines * lh + padY * 2, bold, lines };
    };

    const drawRow = (row, ri, laid) => {
      let x = MARGIN;
      laid.cells.forEach((lines, c) => {
        this.page.drawRectangle({
          x,
          y: this.ph - (this.y + laid.height),
          width: widths[c],
          height: laid.height,
          borderColor: GRID,
          borderWidth: 0.5,
          ...(laid.bold ? { color: HEAD_FILL } : {}),
        });
        lines.slice(0, laid.lines).forEach((line, i) => this.drawLine(line, x + padX, this.y + padY + i * lh, size));
        x += widths[c];
      });
      this.y += laid.height;
    };

    rows.forEach((row, ri) => {
      const laid = layoutRow(row, ri);
      if (laid.height > this.room() && !this.atTop()) {
        this.newPage();
        if (b.header && ri > 0) drawRow(rows[0], 0, layoutRow(rows[0], 0)); // repeat the header row
      }
      drawRow(row, ri, laid);
    });
    this.y += 10;
  }
}
