// PDF in the browser: images -> PDF (pdf-lib), PDF -> images and PDF -> text-only .docx (pdf.js).
import { PDFDocument } from "pdf-lib";
import * as pdfjs from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { t } from "../i18n.js";
import { splitName, UserError } from "../util.js";
import { toEmbeddable } from "./image.js";
import { writeDocx } from "./docx-writer.js";

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

const A4_LONG_SIDE = 842;
const MAX_CANVAS_SIDE = 8000;

export async function imageToPdf(file) {
  const doc = await PDFDocument.create();
  const { bytes, mime } = await toEmbeddable(file);
  const img = mime === "image/png" ? await doc.embedPng(bytes) : await doc.embedJpg(bytes);
  // keep the aspect ratio but cap the page at A4's long side so a 12 MP photo isn't a 4000 pt page
  const scale = Math.min(1, A4_LONG_SIDE / Math.max(img.width, img.height));
  const w = img.width * scale;
  const h = img.height * scale;
  doc.addPage([w, h]).drawImage(img, { x: 0, y: 0, width: w, height: h });
  doc.setProducer("Triton");
  return new Blob([await doc.save()], { type: "application/pdf" });
}

/** Open a PDF, run `fn(pdf)`, and always release the worker-side document afterwards. */
async function withPdf(source, fn) {
  const data = source instanceof Uint8Array ? source : new Uint8Array(await source.arrayBuffer());
  const task = pdfjs.getDocument({ data });
  let pdf;
  try {
    pdf = await task.promise;
  } catch (e) {
    await task.destroy();
    throw new UserError(t("err_pdf", { detail: e?.message ?? String(e) }));
  }
  try {
    return await fn(pdf);
  } finally {
    await task.destroy();
  }
}

/** One image per page; page 1 keeps the plain name, the rest get _2, _3 … like the desktop app. */
export function pdfToImages(file, target, onProgress) {
  const stem = splitName(file.name)[0];
  const mime = target === "png" ? "image/png" : "image/jpeg";
  return withPdf(file, async (pdf) => {
    const outputs = [];
    for (let i = 1; i <= pdf.numPages; i++) {
      const page = await pdf.getPage(i);
      const base = page.getViewport({ scale: 1 });
      // 200 dpi like the desktop app, but never a canvas the browser would refuse to allocate
      const scale = Math.min(200 / 72, MAX_CANVAS_SIDE / Math.max(base.width, base.height));
      const viewport = page.getViewport({ scale });
      const canvas = document.createElement("canvas");
      canvas.width = Math.ceil(viewport.width);
      canvas.height = Math.ceil(viewport.height);
      const ctx = canvas.getContext("2d");
      ctx.fillStyle = "#ffffff"; // PDF pages are transparent; JPEG can't be
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      // "print" intent: pdf.js paces display renders with requestAnimationFrame, which browsers freeze in a background
      // tab, so a long conversion would stall the moment the user switches away. Print renders run on promises instead.
      await page.render({ canvas, canvasContext: ctx, viewport, intent: "print" }).promise;
      const blob = await new Promise((resolve, reject) =>
        canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("encode"))), mime, 0.95),
      );
      outputs.push({ name: `${stem}${i === 1 ? "" : `_${i}`}.${target}`, blob });
      page.cleanup();
      onProgress?.(i / pdf.numPages);
    }
    return outputs;
  });
}

/** Text only: group glyph runs into lines by baseline, lines into paragraphs by spacing. */
export function pdfToDocx(file, onProgress) {
  return withPdf(file, async (pdf) => {
    const items = [];
    for (let p = 1; p <= pdf.numPages; p++) {
      const page = await pdf.getPage(p);
      const { items: raw } = await page.getTextContent();
      const lines = [];
      for (const it of raw) {
        if (!it.str || !it.str.trim()) continue;
        const y = it.transform[5];
        const line = lines.find((l) => Math.abs(l.y - y) < Math.max(2, (it.height || 10) * 0.4));
        if (line) line.parts.push(it);
        else lines.push({ y, h: it.height || 10, parts: [it] });
      }
      lines.sort((a, b) => b.y - a.y);

      let para = "";
      let prev = null;
      const flush = () => {
        if (para.trim()) items.push(para.trim());
        para = "";
      };
      for (const line of lines) {
        const text = line.parts
          .sort((a, b) => a.transform[4] - b.transform[4])
          .map((x) => x.str)
          .join(" ")
          .replace(/\s+/g, " ")
          .trim();
        if (prev && prev.y - line.y > Math.max(prev.h, line.h) * 1.7) flush(); // a gap bigger than line spacing = new paragraph
        para += (para ? " " : "") + text;
        prev = line;
      }
      flush();
      if (p < pdf.numPages) items.push({ pageBreak: true });
      page.cleanup();
      onProgress?.(p / pdf.numPages);
    }
    return writeDocx(items);
  });
}

/** Text of every page, for tests and diagnostics. */
export function pdfText(bytes) {
  return withPdf(bytes, async (pdf) => {
    let text = "";
    for (let p = 1; p <= pdf.numPages; p++) {
      const { items } = await (await pdf.getPage(p)).getTextContent();
      text += items.map((i) => i.str).join(" ") + "\n";
    }
    return { text, pages: pdf.numPages };
  });
}
