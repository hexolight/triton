// Video/audio with FFmpeg compiled to WebAssembly. The ~30 MB core is fetched from a CDN the first
// time it's needed (not bundled), then cached by the browser. Single-threaded build: it needs no
// special cross-origin headers, at the cost of speed.
import { FFmpeg } from "@ffmpeg/ffmpeg";
import { toBlobURL } from "@ffmpeg/util";
import { AUDIO } from "../formats.js";
import { t } from "../i18n.js";
import { humanSize, UserError } from "../util.js";
import { getLang } from "../i18n.js";

const CORE_BASE = "https://cdn.jsdelivr.net/npm/@ffmpeg/core@0.12.10/dist/esm";
const MAX_BYTES = 1024 ** 3; // the wasm heap tops out near 2 GB and holds input + output at once

const MIME = {
  mp4: "video/mp4", webm: "video/webm", mkv: "video/x-matroska", mov: "video/quicktime", avi: "video/x-msvideo",
  mp3: "audio/mpeg", wav: "audio/wav", flac: "audio/flac", ogg: "audio/ogg", opus: "audio/ogg", m4a: "audio/mp4",
  aac: "audio/aac", aiff: "audio/aiff",
};

let instance = null;
let loading = null;
let state = "idle"; // idle | loading | ready | error
const listeners = new Set();

const setState = (s) => {
  state = s;
  listeners.forEach((fn) => fn(s));
};
export const ffmpegState = () => state;
export function onFfmpegState(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function loadFfmpeg() {
  if (instance) return Promise.resolve(instance);
  if (loading) return loading;
  setState("loading");
  loading = (async () => {
    const ff = new FFmpeg();
    await ff.load({
      coreURL: await toBlobURL(`${CORE_BASE}/ffmpeg-core.js`, "text/javascript"),
      wasmURL: await toBlobURL(`${CORE_BASE}/ffmpeg-core.wasm`, "application/wasm"),
    });
    instance = ff;
    setState("ready");
    return ff;
  })().catch(() => {
    loading = null;
    setState("error");
    throw new UserError(t("err_ffmpeg_load"));
  });
  return loading;
}

function reset() {
  try {
    instance?.terminate();
  } catch {
    /* already gone */
  }
  instance = null;
  loading = null;
  setState("idle");
}

/** ffmpeg's last log lines are usually stream metadata; the actual complaint is the line that says so. */
export function errorDetail(lines) {
  const cause = lines.filter((l) => /error|invalid|no streams|does not contain|unable|failed|not found|unsupported|cannot|matches no/i.test(l));
  return (cause.length ? cause.slice(-2) : lines.slice(-3)).map((l) => l.trim()).join("\n");
}

export async function convertMedia(file, srcExt, target, onProgress) {
  if (file.size > MAX_BYTES) throw new UserError(t("err_too_big", { size: humanSize(file.size, getLang()) }));
  const ff = await loadFfmpeg();
  const input = `in.${srcExt}`;
  const output = `out.${target}`;
  const tail = [];
  const onLog = ({ message }) => {
    tail.push(message);
    if (tail.length > 8) tail.shift();
  };
  const onProg = ({ progress }) => onProgress?.(Math.max(0, Math.min(1, progress)));
  ff.on("log", onLog);
  ff.on("progress", onProg);
  try {
    await ff.writeFile(input, new Uint8Array(await file.arrayBuffer()));
    const args = ["-i", input];
    if (AUDIO.includes(target)) args.push("-vn"); // audio-only target: drop the video stream
    args.push("-y", output);
    const code = await ff.exec(args);
    if (code !== 0) throw new UserError(t("err_convert", { detail: errorDetail(tail) || `ffmpeg exit ${code}` }));
    const data = await ff.readFile(output);
    return new Blob([data], { type: MIME[target] ?? "application/octet-stream" });
  } catch (e) {
    if (!(e instanceof UserError)) {
      reset(); // an aborted wasm run leaves the instance unusable; the next job reloads a fresh one
      throw new UserError(t("err_convert", { detail: e?.message ?? String(e) }));
    }
    throw e;
  } finally {
    ff.off?.("log", onLog);
    ff.off?.("progress", onProg);
    for (const f of [input, output]) {
      try {
        await ff.deleteFile(f);
      } catch {
        /* never created, or instance reset */
      }
    }
  }
}
