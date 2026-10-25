// Port of app/core/formats.py, limited to what a browser can actually do.
// Same categories and the same "what can X become" semantics as the desktop app.

export const VIDEO = ["mp4", "mkv", "avi", "mov", "webm", "flv", "wmv", "m4v", "mpg", "ts", "3gp"];
export const AUDIO = ["mp3", "wav", "flac", "aac", "ogg", "m4a", "wma", "opus", "aiff"];
// Anything a browser can decode; only these can be written back out.
export const IMAGE_IN = ["jpg", "jpeg", "png", "webp", "bmp", "gif", "ico"];
export const IMAGE_OUT = ["jpg", "png", "webp", "bmp", "ico"];

// document source -> targets (every pair here has a converter in convert/docs.js or convert/pdf.js)
const DOC_TARGETS = {
  docx: ["pdf", "txt"],
  txt: ["pdf", "docx"],
  odt: ["pdf"],
  csv: ["pdf", "xlsx"],
  xlsx: ["pdf", "csv"],
  xls: ["pdf", "csv", "xlsx"],
  ods: ["pdf", "csv", "xlsx"],
  pdf: ["docx", "png", "jpg"],
};

export function category(ext) {
  ext = ext.toLowerCase();
  if (VIDEO.includes(ext)) return "video";
  if (AUDIO.includes(ext)) return "audio";
  if (IMAGE_IN.includes(ext)) return "image";
  if (ext in DOC_TARGETS) return "document";
  return null;
}

export function targetsFor(ext) {
  ext = ext.toLowerCase();
  switch (category(ext)) {
    case "video":
      return [...VIDEO.filter((e) => e !== ext), ...AUDIO];
    case "audio":
      return AUDIO.filter((e) => e !== ext);
    case "image": {
      const same = ext === "jpeg" ? "jpg" : ext; // jpg and jpeg are one format
      return [...IMAGE_OUT.filter((e) => e !== same), "pdf"];
    }
    case "document":
      return [...DOC_TARGETS[ext]];
    default:
      return [];
  }
}

export function engineFor(src, dst) {
  const s = category(src);
  const d = category(dst) ?? (dst === "pdf" ? "document" : null);
  if ((s === "video" || s === "audio") && (d === "video" || d === "audio")) return "ffmpeg";
  if (s === "image" && dst === "pdf") return "pdf";
  if (s === "image" && d === "image") return "image";
  if (src === "pdf") return "pdf";
  if (s === "document" && d === "document") return "docs";
  return null;
}

export function allExtensions() {
  return [...VIDEO, ...AUDIO, ...IMAGE_IN, ...Object.keys(DOC_TARGETS)];
}
