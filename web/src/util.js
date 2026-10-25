/** An error whose message is already written for the user (localised); everything else gets wrapped. */
export class UserError extends Error {}

export function splitName(name) {
  const i = name.lastIndexOf(".");
  return i > 0 ? [name.slice(0, i), name.slice(i + 1)] : [name, ""];
}

export const extOf = (name) => splitName(name)[1].toLowerCase();

export function humanSize(bytes, lang = "en") {
  let v = bytes;
  for (const unit of ["B", "KB", "MB", "GB"]) {
    if (v < 1024 || unit === "GB") {
      const s = unit === "B" ? String(Math.round(v)) : v.toFixed(1);
      return `${lang === "tr" ? s.replace(".", ",") : s} ${unit}`;
    }
    v /= 1024;
  }
  return "";
}

/** "a.jpg" taken -> "a (2).jpg". Case-insensitive, like a Windows folder. */
export function uniqueName(name, taken) {
  const [stem, ext] = splitName(name);
  const make = (n) => (n === 1 ? name : `${stem} (${n})${ext ? "." + ext : ""}`);
  let n = 1;
  while (taken.has(make(n).toLowerCase())) n++;
  const out = make(n);
  taken.add(out.toLowerCase());
  return out;
}

/** UTF-8 first; Turkish Windows files are often cp1254, so fall back to that. */
export function decodeText(buffer) {
  const bytes = new Uint8Array(buffer);
  if (bytes[0] === 0xff && bytes[1] === 0xfe) return new TextDecoder("utf-16le").decode(bytes.subarray(2));
  if (bytes[0] === 0xfe && bytes[1] === 0xff) return new TextDecoder("utf-16be").decode(bytes.subarray(2));
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(bytes).replace(/^﻿/, "");
  } catch {
    return new TextDecoder("windows-1254").decode(bytes);
  }
}

const DELIMITERS = [",", ";", "\t", "|"];

/** Pick the delimiter that splits the first lines consistently (";" is common in Turkish exports). */
export function sniffDelimiter(text) {
  const lines = text.split(/\r?\n/).filter((l) => l.trim()).slice(0, 6);
  let best = ",";
  let bestScore = 0;
  for (const d of DELIMITERS) {
    const counts = lines.map((l) => {
      let n = 0;
      let inQuotes = false;
      for (const ch of l) {
        if (ch === '"') inQuotes = !inQuotes;
        else if (ch === d && !inQuotes) n++;
      }
      return n;
    });
    const score = counts.length ? Math.min(...counts) : 0; // must appear on every sampled line
    if (score > bestScore) {
      best = d;
      bestScore = score;
    }
  }
  return best;
}

export function parseCsv(text, delimiter = sniffDelimiter(text)) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (inQuotes) {
      if (ch === '"' && text[i + 1] === '"') {
        field += '"';
        i++;
      } else if (ch === '"') inQuotes = false;
      else field += ch;
    } else if (ch === '"') inQuotes = true;
    else if (ch === delimiter) {
      row.push(field);
      field = "";
    } else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && text[i + 1] === "\n") i++;
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else field += ch;
  }
  if (field !== "" || row.length) {
    row.push(field);
    rows.push(row);
  }
  return rows;
}

export function toCsv(rows) {
  const q = (v) => {
    const s = v == null ? "" : String(v);
    return /[",\r\n;]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return rows.map((r) => r.map(q).join(",")).join("\r\n") + "\r\n";
}

/** Spreadsheet cell -> display text, same rules as the desktop engine. */
export function cellText(v) {
  if (v == null) return "";
  if (typeof v === "boolean") return v ? "TRUE" : "FALSE";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : String(v);
  if (v instanceof Date) {
    // SheetJS hands back dates at *local* midnight, so read local fields; UTC getters would show the day before east of Greenwich
    const p = (n) => String(n).padStart(2, "0");
    const date = `${p(v.getDate())}.${p(v.getMonth() + 1)}.${v.getFullYear()}`;
    return v.getHours() || v.getMinutes() ? `${date} ${p(v.getHours())}:${p(v.getMinutes())}` : date;
  }
  return String(v);
}

export const PLAIN_NUMBER = /^-?(0|[1-9]\d*)(\.\d+)?$/;

export function download(blob, name) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30_000);
}
