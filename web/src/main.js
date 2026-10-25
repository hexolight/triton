import "./style.css";
import { boot } from "./app.js";
import { detectLang, setLang } from "./i18n.js";

setLang(detectLang(), { persist: false });
boot();
