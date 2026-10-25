// Image <-> image in the browser. Decode with the browser, encode through a canvas
// (png / jpeg / webp) or by hand (bmp, ico). Mirrors app/converters/image.py.

const MIME = { png: "image/png", jpg: "image/jpeg", jpeg: "image/jpeg", webp: "image/webp" };

export async function decode(file) {
  try {
    return await createImageBitmap(file);
  } catch {
    throw new Error("decode");
  }
}

function canvasOf(bitmap, { background = null, size = null } = {}) {
  const w = size ?? bitmap.width;
  const h = size ?? bitmap.height;
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  if (background) {
    ctx.fillStyle = background;
    ctx.fillRect(0, 0, w, h);
  }
  if (size) {
    // letterbox into a square, keep the aspect ratio
    const s = Math.min(size / bitmap.width, size / bitmap.height);
    const dw = bitmap.width * s;
    const dh = bitmap.height * s;
    ctx.drawImage(bitmap, (size - dw) / 2, (size - dh) / 2, dw, dh);
  } else {
    ctx.drawImage(bitmap, 0, 0);
  }
  return canvas;
}

const toBlob = (canvas, type, quality) =>
  new Promise((resolve, reject) =>
    canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("encode"))), type, quality),
  );

/** 24-bit BMP, rows bottom-up and padded to 4 bytes. */
export function encodeBmp(imageData) {
  const { width, height, data } = imageData;
  const rowSize = Math.ceil((width * 3) / 4) * 4;
  const pixels = rowSize * height;
  const buf = new ArrayBuffer(54 + pixels);
  const v = new DataView(buf);
  v.setUint8(0, 0x42);
  v.setUint8(1, 0x4d);
  v.setUint32(2, 54 + pixels, true);
  v.setUint32(10, 54, true);
  v.setUint32(14, 40, true);
  v.setInt32(18, width, true);
  v.setInt32(22, height, true);
  v.setUint16(26, 1, true);
  v.setUint16(28, 24, true);
  v.setUint32(34, pixels, true);
  v.setInt32(38, 2835, true);
  v.setInt32(42, 2835, true);
  const out = new Uint8Array(buf);
  for (let y = 0; y < height; y++) {
    let o = 54 + (height - 1 - y) * rowSize;
    for (let x = 0; x < width; x++) {
      const i = (y * width + x) * 4;
      out[o++] = data[i + 2];
      out[o++] = data[i + 1];
      out[o++] = data[i];
    }
  }
  return new Blob([buf], { type: "image/bmp" });
}

/** ICO holding PNG images (supported since Vista), one per size. */
export async function encodeIco(bitmap) {
  const sizes = [16, 32, 48, 64, 128, 256];
  const pngs = [];
  for (const s of sizes) {
    const blob = await toBlob(canvasOf(bitmap, { size: s }), "image/png");
    pngs.push(new Uint8Array(await blob.arrayBuffer()));
  }
  const head = 6 + 16 * pngs.length;
  const buf = new ArrayBuffer(head + pngs.reduce((n, p) => n + p.length, 0));
  const v = new DataView(buf);
  v.setUint16(2, 1, true);
  v.setUint16(4, pngs.length, true);
  const out = new Uint8Array(buf);
  let offset = head;
  pngs.forEach((png, i) => {
    const e = 6 + i * 16;
    v.setUint8(e, sizes[i] === 256 ? 0 : sizes[i]);
    v.setUint8(e + 1, sizes[i] === 256 ? 0 : sizes[i]);
    v.setUint16(e + 4, 1, true);
    v.setUint16(e + 6, 32, true);
    v.setUint32(e + 8, png.length, true);
    v.setUint32(e + 12, offset, true);
    out.set(png, offset);
    offset += png.length;
  });
  return new Blob([buf], { type: "image/x-icon" });
}

export async function convertImage(file, target) {
  const bitmap = await decode(file);
  try {
    if (target === "ico") return await encodeIco(bitmap);
    // jpeg and bmp have no alpha: flatten transparency onto white, as the desktop app does
    const flat = target === "jpg" || target === "jpeg" || target === "bmp";
    const canvas = canvasOf(bitmap, { background: flat ? "#ffffff" : null });
    if (target === "bmp") {
      return encodeBmp(canvas.getContext("2d").getImageData(0, 0, canvas.width, canvas.height));
    }
    return await toBlob(canvas, MIME[target], 0.95);
  } finally {
    bitmap.close?.();
  }
}

/** Any browser-decodable image -> PNG or JPEG bytes that pdf-lib can embed. */
export async function toEmbeddable(file) {
  const type = file.type;
  if (type === "image/png" || type === "image/jpeg") {
    return { bytes: new Uint8Array(await file.arrayBuffer()), mime: type };
  }
  const bitmap = await decode(file);
  try {
    const blob = await toBlob(canvasOf(bitmap), "image/png");
    return { bytes: new Uint8Array(await blob.arrayBuffer()), mime: "image/png" };
  } finally {
    bitmap.close?.();
  }
}
