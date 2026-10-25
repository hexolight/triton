import { engineFor } from "../formats.js";
import { t } from "../i18n.js";
import { splitName, UserError } from "../util.js";

/**
 * Convert one job. Returns [{ name, blob }]: usually one file, several for a multi-page PDF -> images.
 * Each engine is imported on demand, so the first page load doesn't pay for pdf.js, SheetJS, mammoth
 * or pdf-lib until a file actually needs them (and FFmpeg's wasm core downloads only when first used).
 */
export async function convertJob(job, onProgress) {
  const { file, ext, target } = job;
  const stem = splitName(file.name)[0];
  const one = (blob) => [{ name: `${stem}.${target}`, blob }];
  const engine = engineFor(ext, target);
  try {
    switch (engine) {
      case "ffmpeg": {
        const { convertMedia } = await import("./ffmpeg.js");
        return one(await convertMedia(file, ext, target, onProgress));
      }
      case "image": {
        const { convertImage } = await import("./image.js");
        return one(await convertImage(file, target));
      }
      case "pdf": {
        const pdf = await import("./pdf.js");
        if (ext !== "pdf") return one(await pdf.imageToPdf(file));
        if (target === "docx") return one(await pdf.pdfToDocx(file, onProgress));
        return await pdf.pdfToImages(file, target, onProgress);
      }
      case "docs": {
        const { convertDoc } = await import("./docs.js");
        return one(await convertDoc(file, ext, target));
      }
      default:
        throw new UserError(t("err_unsupported", { src: ext.toUpperCase(), dst: target.toUpperCase() }));
    }
  } catch (e) {
    if (e instanceof UserError) throw e;
    if (e?.message === "decode") throw new UserError(t("err_image"));
    throw new UserError(t(engine === "docs" || ext === "pdf" ? "err_doc" : "err_convert", { detail: e?.message ?? String(e) }));
  }
}
