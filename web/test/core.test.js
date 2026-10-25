import { describe, expect, it } from "vitest";
import { allExtensions, category, engineFor, targetsFor } from "../src/formats.js";
import { cellText, decodeText, humanSize, parseCsv, sniffDelimiter, splitName, toCsv, uniqueName } from "../src/util.js";

describe("formats", () => {
  it("every offered target has an engine", () => {
    for (const src of allExtensions()) {
      for (const dst of targetsFor(src)) expect(engineFor(src, dst), `${src} -> ${dst}`).not.toBeNull();
    }
  });

  it("never offers a file its own format", () => {
    for (const src of allExtensions()) expect(targetsFor(src)).not.toContain(src);
  });

  it("treats jpg and jpeg as one format", () => {
    expect(targetsFor("jpeg")).not.toContain("jpg");
    expect(targetsFor("jpg")).not.toContain("jpg");
    expect(targetsFor("png")).toContain("jpg");
  });

  it("is case-insensitive and rejects unknown extensions", () => {
    expect(category("MP4")).toBe("video");
    expect(category("xyz")).toBeNull();
    expect(targetsFor("xyz")).toEqual([]);
  });

  it("routes work to the right engine", () => {
    expect(engineFor("mp4", "mp3")).toBe("ffmpeg");
    expect(engineFor("png", "jpg")).toBe("image");
    expect(engineFor("png", "pdf")).toBe("pdf");
    expect(engineFor("pdf", "png")).toBe("pdf");
    expect(engineFor("docx", "pdf")).toBe("docs");
  });
});

describe("util", () => {
  it("splits names on the last dot only", () => {
    expect(splitName("a.b.c.tar")).toEqual(["a.b.c", "tar"]);
    expect(splitName(".gitignore")).toEqual([".gitignore", ""]);
    expect(splitName("README")).toEqual(["README", ""]);
  });

  it("makes output names unique, case-insensitively", () => {
    const taken = new Set();
    expect(uniqueName("a.pdf", taken)).toBe("a.pdf");
    expect(uniqueName("A.PDF", taken)).toBe("A (2).PDF");
    expect(uniqueName("a.pdf", taken)).toBe("a (3).pdf");
  });

  it("formats sizes with the locale's decimal mark", () => {
    expect(humanSize(36_700, "tr")).toBe("35,8 KB");
    expect(humanSize(36_700, "en")).toBe("35.8 KB");
    expect(humanSize(12, "en")).toBe("12 B");
  });

  it("decodes UTF-8, UTF-16 and falls back to Turkish cp1254", () => {
    expect(decodeText(new TextEncoder().encode("şğüıİ"))).toBe("şğüıİ");
    expect(decodeText(new Uint8Array([0xff, 0xfe, 0x7e, 0x01]).buffer)).toBe("ž"); // BOM + U+017E, little endian
    expect(decodeText(new Uint8Array([0xde, 0xfd, 0xf0]).buffer)).toBe("Şığ"); // not valid UTF-8, valid cp1254
  });

  it("sniffs the CSV delimiter, ignoring delimiters inside quotes", () => {
    expect(sniffDelimiter("a;b;c\n1;2;3")).toBe(";");
    expect(sniffDelimiter("a\tb\n1\t2")).toBe("\t");
    expect(sniffDelimiter('"a,b";c\n"1,2";3')).toBe(";");
  });

  it("round-trips quoted CSV fields", () => {
    const rows = [["name", "note"], ["Ada", 'said "hi", left'], ["multi", "line\nbreak"]];
    expect(parseCsv(toCsv(rows), ",")).toEqual(rows);
  });

  it("renders spreadsheet cells like the desktop engine", () => {
    expect(cellText(null)).toBe("");
    expect(cellText(true)).toBe("TRUE");
    expect(cellText(new Date(2026, 0, 1))).toBe("01.01.2026");
    expect(cellText(new Date(2026, 0, 1, 9, 5))).toBe("01.01.2026 09:05");
  });
});
