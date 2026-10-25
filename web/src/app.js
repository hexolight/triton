import JSZip from "jszip";
import { convertJob } from "./convert/index.js";
import { ffmpegState, loadFfmpeg, onFfmpegState } from "./convert/ffmpeg.js";
import { allExtensions, targetsFor } from "./formats.js";
import { getLang, onLangChange, setLang, t, tn } from "./i18n.js";
import { hero, icon } from "./icons.js";
import { download, extOf, humanSize, splitName, uniqueName } from "./util.js";

const DESKTOP_URL = "https://github.com/hexolight/triton/releases/latest";

const $ = (sel) => document.querySelector(sel);
const els = {
  rows: $("#rows"),
  empty: $("#empty"),
  dropzone: $("#dropzone"),
  listHeader: $("#list-header"),
  summary: $("#summary"),
  bulk: $("#bulk"),
  addFiles: $("#btn-add-files"),
  addFolder: $("#btn-add-folder"),
  clear: $("#btn-clear"),
  primary: $("#btn-primary"),
  saveReady: $("#btn-save-ready"),
  fileInput: $("#file-input"),
  folderInput: $("#folder-input"),
  mainView: $("#main-view"),
  enginesView: $("#engines-view"),
  engineList: $("#engine-list"),
  back: $("#btn-back"),
  chipFfmpeg: $("#chip-ffmpeg"),
  chipDocs: $("#chip-docs"),
  dialog: $("#dialog"),
};

const state = {
  jobs: [], // every file the user added
  converting: false,
  runJobs: [],
  note: null, // [i18n key, params] so the line is re-translated when the language flips
  view: "main",
  seq: 0,
};
const rowParts = new Map(); // job.id -> the row's elements
const seen = new Set(); // "name|size|mtime" of files already in the list

const isRunnable = (j) => j.status === "pending" || j.status === "error";

// ------------------------------------------------------------------ list rows
function makeRow(job, index) {
  const li = document.createElement("li");
  li.className = "row";
  li.style.setProperty("--i", index);
  li.innerHTML = `
    <div class="row-main"><div class="name"><span class="stem"></span><span class="ext"></span></div><div class="meta"></div></div>
    ${icon("arrow_right", "arrow")}
    <select class="target"></select>
    <button class="status" type="button"></button>
    <button class="remove" type="button">${icon("close")}</button>
    <div class="progress" hidden><i></i></div>`;

  const parts = {
    li,
    name: li.querySelector(".name"),
    stem: li.querySelector(".stem"),
    ext: li.querySelector(".ext"),
    meta: li.querySelector(".meta"),
    select: li.querySelector(".target"),
    status: li.querySelector(".status"),
    remove: li.querySelector(".remove"),
    progress: li.querySelector(".progress"),
  };

  // file names are untrusted input: always textContent, never innerHTML
  const [stem, ext] = splitName(job.file.name);
  parts.stem.textContent = stem;
  parts.ext.textContent = ext ? `.${ext}` : "";
  parts.name.title = job.file.name;

  for (const target of targetsFor(job.ext)) {
    const opt = document.createElement("option");
    opt.value = opt.textContent = target;
    parts.select.append(opt);
  }
  parts.select.addEventListener("change", () => retarget(job, parts.select.value));
  parts.remove.addEventListener("click", () => removeJob(job));
  parts.status.addEventListener("click", () => {
    if (job.status === "done") saveJob(job);
    else if (job.status === "error") showDialog(t("conversion_error_title", { name: job.file.name }), job.error);
  });

  rowParts.set(job.id, parts);
  updateMeta(job);
  updateRow(job);
  return li;
}

function updateMeta(job) {
  const p = rowParts.get(job.id);
  if (!p) return;
  p.meta.textContent = [job.ext.toUpperCase(), humanSize(job.file.size, getLang())].join("  ·  ");
  p.select.setAttribute("aria-label", t("target_label", { name: job.file.name }));
  p.remove.setAttribute("aria-label", t("tooltip_remove"));
  p.remove.title = t("tooltip_remove");
}

function updateRow(job) {
  const p = rowParts.get(job.id);
  if (!p) return;
  const { status } = job;
  p.select.value = job.target;
  p.select.disabled = status === "converting";
  p.status.dataset.state = status;
  p.status.disabled = status === "pending" || status === "converting";
  p.status.title = "";
  if (status === "done") {
    p.status.innerHTML = `${icon("save")}<span>${t("status_save")}</span>`;
  } else if (status === "error") {
    p.status.innerHTML = `${icon("alert")}<span>${t("status_error")}</span>`;
    p.status.title = (job.error ?? "").split("\n")[0].slice(0, 200);
  } else if (status === "converting") {
    p.status.textContent = job.progress > 0 ? `${Math.round(job.progress * 100)}%` : t("status_converting");
  } else {
    p.status.textContent = t("status_pending");
  }
  const busy = status === "converting";
  p.progress.hidden = !busy;
  p.progress.dataset.indeterminate = String(busy && !(job.progress > 0));
  p.progress.style.setProperty("--p", job.progress || 0);
}

// progress arrives far faster than the eye can use it; paint at most once per frame
const dirty = new Set();
function queueProgress(job) {
  if (!dirty.size) requestAnimationFrame(() => (dirty.forEach(updateRow), dirty.clear()));
  dirty.add(job);
}

function retarget(job, value, refresh = true) {
  job.target = value;
  // a finished/failed job's output is for the old format: back to waiting instead of saving it stale
  if (job.status === "done" || job.status === "error") {
    job.status = "pending";
    job.error = null;
    job.outputs = null;
  }
  updateRow(job);
  if (refresh) {
    state.note = null; // "7 done, 0 failed" no longer describes the list
    refreshUi();
  }
}

function removeJob(job) {
  job.removed = true;
  state.jobs = state.jobs.filter((j) => j !== job);
  seen.delete(job.key);
  rowParts.get(job.id)?.li.remove();
  rowParts.delete(job.id);
  state.note = null;
  refreshUi();
}

function clearAll() {
  for (const job of state.jobs) job.removed = true;
  state.jobs = [];
  seen.clear();
  rowParts.clear();
  els.rows.replaceChildren();
  state.note = null;
  refreshUi();
}

// ------------------------------------------------------------------ adding files
export function addFiles(files) {
  let added = 0;
  let skipped = 0;
  const fresh = document.createDocumentFragment();
  for (const file of files) {
    const ext = extOf(file.name);
    const targets = targetsFor(ext);
    const key = `${file.name}|${file.size}|${file.lastModified}`;
    if (!targets.length || seen.has(key)) {
      skipped++;
      continue;
    }
    seen.add(key);
    const job = {
      id: ++state.seq,
      key,
      file,
      ext,
      target: targets[0],
      status: "pending",
      error: null,
      outputs: null,
      progress: 0,
      removed: false,
    };
    state.jobs.push(job);
    fresh.append(makeRow(job, added));
    added++;
  }
  els.rows.append(fresh);
  state.note = skipped ? ["skipped_files", { count: skipped }] : null;
  if (added) showView("main");
  refreshUi();
  return { added, skipped };
}

async function collectDropped(dt) {
  // DataTransfer is only valid synchronously inside the event, so grab the entries first
  const entries = [...(dt.items ?? [])].map((i) => i.webkitGetAsEntry?.()).filter(Boolean);
  if (!entries.length) return [...dt.files];
  const file = (e) => new Promise((res, rej) => e.file(res, rej));
  const files = [];
  for (const entry of entries) {
    if (entry.isFile) files.push(await file(entry));
    else if (entry.isDirectory) {
      // one level deep, like the desktop app
      const reader = entry.createReader();
      let batch;
      do {
        batch = await new Promise((res, rej) => reader.readEntries(res, rej));
        for (const e of batch) if (e.isFile) files.push(await file(e));
      } while (batch.length);
    }
  }
  return files;
}

// ------------------------------------------------------------------ bulk format
function refreshBulk() {
  const values = [];
  for (const ext of new Set(state.jobs.map((j) => j.ext))) {
    for (const target of targetsFor(ext)) if (!values.includes(target)) values.push(target);
  }
  els.bulk.replaceChildren();
  const placeholder = new Option(t("bulk_placeholder"), "", true, true);
  placeholder.disabled = true;
  placeholder.hidden = true;
  els.bulk.append(placeholder, ...values.map((v) => new Option(v, v)));
}

function applyBulk(value) {
  if (!value) return;
  let applied = 0;
  for (const job of state.jobs) {
    if (targetsFor(job.ext).includes(value)) {
      if (job.target !== value || job.status === "done" || job.status === "error") retarget(job, value, false);
      applied++;
    }
  }
  state.note = ["bulk_applied", { applied, total: state.jobs.length, fmt: value }];
  refreshUi();
}

// ------------------------------------------------------------------ conversion
async function startConversion() {
  if (state.converting) return;
  const runnable = state.jobs.filter(isRunnable);
  if (!runnable.length) return;
  for (const job of runnable) {
    job.status = "pending";
    job.error = null;
    job.progress = 0;
    updateRow(job);
  }
  state.runJobs = runnable;
  state.converting = true;
  state.note = null;
  refreshUi();

  let done = 0;
  let failed = 0;
  for (const job of runnable) {
    if (job.removed) continue;
    job.status = "converting";
    job.progress = 0;
    updateRow(job);
    refreshFooter();
    try {
      job.outputs = await convertJob(job, (p) => {
        job.progress = p;
        queueProgress(job);
      });
      job.status = "done";
      done++;
    } catch (e) {
      job.status = "error";
      job.error = e?.message ?? String(e);
      failed++;
    }
    job.progress = 0;
    dirty.delete(job);
    updateRow(job);
    refreshFooter();
    await new Promise((r) => setTimeout(r)); // let the browser paint between files
  }
  state.converting = false;
  state.note = ["summary_result", { done, failed }];
  refreshUi();
}

// ------------------------------------------------------------------ saving
async function saveFiles(files, zipName) {
  if (files.length === 1) return download(files[0].blob, files[0].name);
  const zip = new JSZip();
  for (const f of files) zip.file(f.name, f.blob);
  // media is already compressed; STORE keeps the zip fast and light on memory
  download(await zip.generateAsync({ type: "blob", compression: "STORE" }), zipName);
}

function saveJob(job) {
  if (job.status === "done" && job.outputs?.length) {
    saveFiles(job.outputs, `${splitName(job.file.name)[0]}.zip`);
  }
}

function saveAll() {
  const taken = new Set();
  const files = [];
  for (const job of state.jobs) {
    if (job.status !== "done") continue;
    for (const out of job.outputs ?? []) files.push({ name: uniqueName(out.name, taken), blob: out.blob });
  }
  if (files.length) saveFiles(files, t("zip_name"));
}

// ------------------------------------------------------------------ state -> DOM
function refreshFooter() {
  const runnable = state.jobs.filter(isRunnable);
  const done = state.jobs.filter((j) => j.status === "done");
  const { primary, saveReady } = els;
  let showSecondary = false;

  primary.onclick = null;
  if (state.converting) {
    const live = state.runJobs.filter((j) => !j.removed);
    const finished = live.filter((j) => j.status === "done" || j.status === "error").length;
    primary.disabled = true;
    primary.textContent = t("converting_progress", { done: finished, total: live.length });
  } else if (!state.jobs.length) {
    primary.disabled = true;
    primary.textContent = t("convert");
  } else if (runnable.length) {
    primary.disabled = false;
    primary.textContent = t("convert_n", { count: runnable.length });
    primary.onclick = startConversion;
    showSecondary = done.length > 0;
  } else {
    primary.disabled = false;
    primary.textContent = t("save_all", { count: done.length });
    primary.onclick = saveAll;
  }
  saveReady.hidden = !showSecondary;
  if (showSecondary) saveReady.textContent = t("save_ready", { count: done.length });
}

function refreshUi() {
  const has = state.jobs.length > 0;
  els.addFiles.classList.toggle("btn-primary", !has);
  els.clear.hidden = !has;
  els.listHeader.hidden = !has;
  els.empty.hidden = has;
  els.rows.hidden = !has;
  els.summary.textContent = tn("file_count", state.jobs.length) + (state.note ? `  ·  ${t(...state.note)}` : "");
  refreshBulk();
  refreshFooter();
}

function renderEmpty() {
  els.empty.innerHTML = `${hero()}<h2>${t("empty_title")}</h2><p>${t("empty_hint")}</p><p class="formats">${t("empty_formats")}</p>`;
}

// ------------------------------------------------------------------ engines screen
function renderEngines() {
  const ff = ffmpegState();
  const ffLabel = { idle: "engine_state_idle", loading: "engine_state_loading", ready: "engine_state_ready", error: "engine_state_error" }[ff];
  const ffTone = ff === "ready" ? "ready" : ff === "error" ? "warn" : "";
  els.engineList.innerHTML = `
    <li class="engine">
      <h3>${t("engine_ffmpeg_name")}</h3>
      <div class="state" data-tone="${ffTone}"><span class="dot" data-state="${ff}"></span>${t(ffLabel)}</div>
      <p>${t("engine_ffmpeg_desc")}</p>
      ${ff === "ready" || ff === "loading" ? "" : `<button class="btn" id="btn-load-ffmpeg" type="button">${t(ff === "error" ? "engine_retry" : "engine_load")}</button>`}
    </li>
    <li class="engine">
      <h3>${t("engine_docs_name")}</h3>
      <div class="state" data-tone="ready"><span class="dot" data-state="ready"></span>${t("engine_docs_status")}</div>
      <p>${t("engine_docs_desc")}</p>
    </li>
    <li class="engine">
      <h3>${t("engine_desktop_name")}</h3>
      <p>${t("engine_desktop_desc")}</p>
      <a class="btn" href="${DESKTOP_URL}" target="_blank" rel="noopener">${t("engine_desktop_btn")}</a>
    </li>`;
  $("#btn-load-ffmpeg")?.addEventListener("click", () => loadFfmpeg().catch(() => {}));
}

function renderChips() {
  els.chipFfmpeg.querySelector(".dot").dataset.state = ffmpegState();
}

export function showView(name) {
  state.view = name;
  els.mainView.hidden = name !== "main";
  els.enginesView.hidden = name !== "engines";
  if (name === "engines") {
    renderEngines();
    els.back.focus({ preventScroll: true });
  }
}

function showDialog(title, body) {
  $("#dialog-title").textContent = title;
  $("#dialog-body").textContent = body ?? "";
  els.dialog.showModal();
}

function applyStaticText() {
  for (const el of document.querySelectorAll("[data-i18n]")) el.textContent = t(el.dataset.i18n);
  for (const el of document.querySelectorAll("[data-i18n-label]")) el.setAttribute("aria-label", t(el.dataset.i18nLabel));
  els.back.innerHTML = `${icon("chevron_left")}<span>${t("back")}</span>`;
  for (const b of document.querySelectorAll("[data-lang]")) b.setAttribute("aria-pressed", String(b.dataset.lang === getLang()));
  renderEmpty();
}

// ------------------------------------------------------------------ boot
export function boot() {
  const accept = allExtensions().map((e) => `.${e}`).join(",");
  els.fileInput.accept = accept;

  els.addFiles.addEventListener("click", () => els.fileInput.click());
  els.addFolder.addEventListener("click", () => els.folderInput.click());
  els.clear.addEventListener("click", clearAll);
  els.saveReady.addEventListener("click", saveAll);
  els.bulk.addEventListener("change", () => applyBulk(els.bulk.value));
  els.back.addEventListener("click", () => showView("main"));
  els.chipFfmpeg.addEventListener("click", () => showView("engines"));
  els.chipDocs.addEventListener("click", () => showView("engines"));
  $("#dialog-close").addEventListener("click", () => els.dialog.close());
  els.dialog.addEventListener("click", (e) => e.target === els.dialog && els.dialog.close());

  els.fileInput.addEventListener("change", () => {
    addFiles([...els.fileInput.files]);
    els.fileInput.value = "";
  });
  els.folderInput.addEventListener("change", () => {
    // top level of the chosen folder only, like the desktop app
    addFiles([...els.folderInput.files].filter((f) => f.webkitRelativePath.split("/").length === 2));
    els.folderInput.value = "";
  });

  for (const b of document.querySelectorAll("[data-lang]")) {
    b.addEventListener("click", () => setLang(b.dataset.lang));
  }

  // drag & drop anywhere on the page; the zone's border shows where it will land
  let depth = 0;
  const hasFiles = (e) => e.dataTransfer?.types?.includes("Files");
  document.addEventListener("dragenter", (e) => {
    if (!hasFiles(e)) return;
    e.preventDefault();
    depth++;
    els.dropzone.dataset.over = "true";
  });
  document.addEventListener("dragover", (e) => hasFiles(e) && e.preventDefault());
  document.addEventListener("dragleave", (e) => {
    if (!hasFiles(e)) return;
    if (--depth <= 0) {
      depth = 0;
      els.dropzone.dataset.over = "false";
    }
  });
  document.addEventListener("drop", async (e) => {
    if (!hasFiles(e)) return;
    e.preventDefault();
    depth = 0;
    els.dropzone.dataset.over = "false";
    addFiles(await collectDropped(e.dataTransfer));
  });

  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "o") {
      e.preventDefault();
      els.fileInput.click();
    } else if (e.key === "Escape" && state.view === "engines" && !els.dialog.open) {
      showView("main");
    }
  });

  onFfmpegState(() => {
    renderChips();
    if (state.view === "engines") renderEngines();
  });
  onLangChange(() => {
    applyStaticText();
    for (const job of state.jobs) {
      updateMeta(job);
      updateRow(job);
    }
    refreshUi();
    if (state.view === "engines") renderEngines();
  });

  applyStaticText();
  renderChips();
  refreshUi();

  // a handle for tests and debugging
  window.triton = {
    state, addFiles, startConversion, saveAll, convertJob, retarget, applyBulk,
    pdfText: (bytes) => import("./convert/pdf.js").then((m) => m.pdfText(bytes)),
  };
}
