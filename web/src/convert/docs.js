// Documents in the browser. Mirrors app/converters/docs.py: read the file, build simple blocks,
// lay them out into a PDF (see ../pdf/layout.js). Content converter, not a layout engine.
import JSZip from "jszip";
import mammoth from "mammoth";
import * as XLSX from "xlsx";
import { blocksToPdf } from "../pdf/layout.js";
import { t } from "../i18n.js";
import { cellText, decodeText, parseCsv, PLAIN_NUMBER, splitName, toCsv, UserError } from "../util.js";
import { toEmbeddable } from "./image.js";
import { writeDocx } from "./docx-writer.js";

const MAX_ROWS_PER_SHEET = 5000; // a 200k-row sheet would produce a PDF nobody can open
const collapse = (s) => s.replace(/\s+/g, " ");

// ------------------------------------------------------------------ HTML -> blocks
async function dataUrlImage(src) {
  const m = /^data:(image\/[a-z+.-]+);base64,(.*)$/i.exec(src ?? "");
  if (!m) return null;
  const bytes = Uint8Array.from(atob(m[2]), (c) => c.charCodeAt(0));
  const mime = m[1].toLowerCase();
  if (mime === "image/png" || mime === "image/jpeg") return { bytes, mime };
  try {
    return await toEmbeddable(new File([bytes], "img", { type: mime }));
  } catch {
    return null; // unsupported picture type: skip it rather than fail the document
  }
}

function inlineRuns(node, bold = false, out = []) {
  for (const n of node.childNodes) {
    if (n.nodeType === 3) {
      out.push({ text: collapse(n.nodeValue), bold });
    } else if (n.nodeType === 1) {
      const tag = n.tagName.toLowerCase();
      if (tag === "br") out.push({ text: "\n", bold });
      else if (tag === "img" || tag === "ul" || tag === "ol" || tag === "table") continue;
      else inlineRuns(n, bold || tag === "strong" || tag === "b", out);
    }
  }
  return out;
}

const hasText = (runs) => runs.some((r) => r.text.trim());

async function walkHtml(el, blocks, depth = 0) {
  for (const n of el.children) {
    const tag = n.tagName.toLowerCase();
    if (/^h[1-6]$/.test(tag)) {
      const runs = inlineRuns(n);
      if (hasText(runs)) blocks.push({ t: "h", level: Number(tag[1]), runs });
    } else if (tag === "p") {
      const runs = inlineRuns(n);
      if (hasText(runs)) blocks.push({ t: "p", runs });
      for (const img of n.querySelectorAll("img")) {
        const data = await dataUrlImage(img.getAttribute("src"));
        if (data) blocks.push({ t: "img", ...data });
      }
    } else if (tag === "ul" || tag === "ol") {
      let i = 1;
      for (const li of n.children) {
        if (li.tagName.toLowerCase() !== "li") continue;
        const runs = inlineRuns(li);
        if (hasText(runs)) blocks.push({ t: "li", runs, ordered: tag === "ol", n: i++, depth });
        await walkHtml(li, blocks, depth + 1);
      }
    } else if (tag === "table") {
      const rows = [...n.querySelectorAll("tr")].map((tr) =>
        [...tr.children].map((c) => collapse(c.textContent).trim()),
      );
      if (rows.length) blocks.push({ t: "table", rows, header: false });
    } else if (tag === "img") {
      const data = await dataUrlImage(n.getAttribute("src"));
      if (data) blocks.push({ t: "img", ...data });
    } else if (tag === "pre") {
      blocks.push({ t: "pre", text: n.textContent });
    } else {
      await walkHtml(n, blocks, depth);
    }
  }
}

export async function htmlToBlocks(html) {
  const doc = new DOMParser().parseFromString(html, "text/html");
  const blocks = [];
  await walkHtml(doc.body, blocks);
  return blocks;
}

// ------------------------------------------------------------------------ readers
async function docxBlocks(file) {
  const { value } = await mammoth.convertToHtml({ arrayBuffer: await file.arrayBuffer() });
  return htmlToBlocks(value);
}

async function txtBlocks(file) {
  return [{ t: "pre", text: decodeText(await file.arrayBuffer()) }];
}

const NS_TEXT = (n) => n.nodeName;

function odtText(node) {
  let s = "";
  for (const n of node.childNodes) {
    if (n.nodeType === 3) s += n.nodeValue;
    else if (n.nodeType === 1) {
      const name = NS_TEXT(n);
      if (name === "text:s") s += " ".repeat(Number(n.getAttribute("text:c") ?? 1));
      else if (name === "text:tab") s += " ";
      else if (name === "text:line-break") s += "\n";
      else s += odtText(n);
    }
  }
  return s;
}

async function odtBlocks(file) {
  const zip = await JSZip.loadAsync(await file.arrayBuffer());
  const xml = await zip.file("content.xml").async("string");
  const doc = new DOMParser().parseFromString(xml, "application/xml");
  if (doc.querySelector("parsererror")) throw new Error("content.xml is not valid XML");
  const body = doc.getElementsByTagName("office:text")[0];
  const blocks = [];

  const images = async (node) => {
    for (const img of node.getElementsByTagName("draw:image")) {
      const href = img.getAttribute("xlink:href");
      const entry = href && zip.file(href);
      const ext = href?.split(".").pop()?.toLowerCase();
      if (!entry || !["png", "jpg", "jpeg"].includes(ext)) continue;
      blocks.push({ t: "img", bytes: await entry.async("uint8array"), mime: ext === "png" ? "image/png" : "image/jpeg" });
    }
  };

  const walk = async (parent, depth) => {
    for (const n of parent.children) {
      const name = NS_TEXT(n);
      if (name === "text:h") {
        const runs = [{ text: odtText(n) }];
        if (hasText(runs)) blocks.push({ t: "h", level: Number(n.getAttribute("text:outline-level") ?? 1), runs });
      } else if (name === "text:p") {
        const runs = [{ text: odtText(n) }];
        if (hasText(runs)) blocks.push({ t: "p", runs });
        await images(n);
      } else if (name === "text:list") {
        for (const item of n.children) {
          for (const c of item.children) {
            if (NS_TEXT(c) === "text:list") await walk(item, depth + 1);
            else blocks.push({ t: "li", runs: [{ text: odtText(c) }], ordered: false, n: 0, depth });
          }
        }
      } else if (name === "table:table") {
        const rows = [...n.getElementsByTagName("table:table-row")].map((tr) =>
          [...tr.children].filter((c) => NS_TEXT(c) === "table:table-cell").map((c) => odtText(c).trim()),
        );
        if (rows.length) blocks.push({ t: "table", rows, header: false });
      } else if (name === "text:section") {
        await walk(n, depth);
      }
    }
  };
  await walk(body, 0);
  return blocks;
}

// ------------------------------------------------------------------ spreadsheets
async function readSheets(file, ext) {
  const buffer = await file.arrayBuffer();
  if (ext === "csv") return [{ name: splitName(file.name)[0], rows: parseCsv(decodeText(buffer)) }];
  const wb = XLSX.read(buffer, { type: "array", cellDates: true });
  return wb.SheetNames.map((name) => ({
    name,
    rows: XLSX.utils.sheet_to_json(wb.Sheets[name], { header: 1, raw: true, defval: null }),
  }));
}

/** Drop empty trailing rows/columns (spreadsheets report huge "used" ranges). */
export function trimRows(rows) {
  const filled = (c) => c !== null && c !== undefined && c !== "";
  let end = rows.length;
  while (end > 0 && !rows[end - 1].some(filled)) end--;
  const kept = rows.slice(0, end);
  let width = 0;
  for (const r of kept) for (let i = r.length - 1; i >= width; i--) if (filled(r[i])) { width = i + 1; break; }
  return kept.map((r) => Array.from({ length: width }, (_, i) => r[i] ?? null));
}

async function sheetsToPdf(file, ext) {
  const sheets = await readSheets(file, ext);
  const blocks = [];
  let widest = 0;
  sheets.forEach((sheet, i) => {
    let rows = trimRows(sheet.rows);
    const hidden = Math.max(0, rows.length - MAX_ROWS_PER_SHEET);
    rows = rows.slice(0, MAX_ROWS_PER_SHEET);
    widest = Math.max(widest, ...rows.map((r) => r.length), 0);
    if (i > 0) blocks.push({ t: "pagebreak" });
    if (sheets.length > 1) blocks.push({ t: "h", level: 2, runs: [{ text: sheet.name }] });
    if (rows.length) blocks.push({ t: "table", rows: rows.map((r) => r.map(cellText)), header: true });
    if (hidden) blocks.push({ t: "note", text: t("docs_rows_hidden", { count: hidden }) });
  });
  return blocksToPdf(blocks, { landscape: widest > 6, title: splitName(file.name)[0] });
}

async function sheetsToCsv(file, ext) {
  const [first] = await readSheets(file, ext);
  const text = toCsv(trimRows(first.rows).map((r) => r.map(cellText)));
  return new Blob(["﻿", text], { type: "text/csv;charset=utf-8" });
}

async function sheetsToXlsx(file, ext) {
  const wb = XLSX.utils.book_new();
  const used = new Set();
  for (const { name, rows } of await readSheets(file, ext)) {
    // only unambiguous numbers become numbers: "0532..." and "00123" must stay text
    const aoa = rows.map((r) => r.map((c) => (typeof c === "string" && PLAIN_NUMBER.test(c) ? Number(c) : c)));
    let sheetName = name.replace(/[\\/*?:[\]]/g, "_").slice(0, 31) || "Sheet";
    while (used.has(sheetName.toLowerCase())) sheetName = `${sheetName.slice(0, 28)}_${used.size}`;
    used.add(sheetName.toLowerCase());
    XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(aoa), sheetName);
  }
  const data = XLSX.write(wb, { type: "array", bookType: "xlsx" });
  return new Blob([data], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
}

// ------------------------------------------------------------------------- entry
const pdfBlob = (bytes) => new Blob([bytes], { type: "application/pdf" });

export async function convertDoc(file, src, target) {
  const title = splitName(file.name)[0];
  const key = `${src}>${target}`;
  switch (key) {
    case "docx>pdf":
      return pdfBlob(await blocksToPdf(await docxBlocks(file), { title }));
    case "docx>txt": {
      const { value } = await mammoth.extractRawText({ arrayBuffer: await file.arrayBuffer() });
      return new Blob([value], { type: "text/plain;charset=utf-8" });
    }
    case "txt>pdf":
      return pdfBlob(await blocksToPdf(await txtBlocks(file), { title }));
    case "txt>docx": {
      const lines = decodeText(await file.arrayBuffer()).split(/\r?\n/);
      return writeDocx(lines);
    }
    case "odt>pdf":
      return pdfBlob(await blocksToPdf(await odtBlocks(file), { title }));
    case "csv>pdf":
    case "xlsx>pdf":
    case "xls>pdf":
    case "ods>pdf":
      return pdfBlob(await sheetsToPdf(file, src));
    case "xlsx>csv":
    case "xls>csv":
    case "ods>csv":
      return sheetsToCsv(file, src);
    case "csv>xlsx":
    case "xls>xlsx":
    case "ods>xlsx":
      return sheetsToXlsx(file, src);
    default:
      throw new UserError(t("err_unsupported", { src: src.toUpperCase(), dst: target.toUpperCase() }));
  }
}
