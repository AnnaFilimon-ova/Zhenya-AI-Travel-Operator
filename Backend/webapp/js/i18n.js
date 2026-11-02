import en from "./locales/en.js";
import ru from "./locales/ru.js";
import { tg } from "./telegram.js";

const DICTS = { ru, en };
const STORAGE_KEY = "zhenya-lang";
const RUSSIAN_LIKE = ["ru", "uk", "be", "kk"];

export function getLangPreference() {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    return v === "ru" || v === "en" ? v : "auto";
  } catch {
    return "auto";
  }
}

export function setLangPreference(pref) {
  try {
    localStorage.setItem(STORAGE_KEY, pref);
  } catch {
  }
}

export function resolveLang(pref, code) {
  if (pref === "ru" || pref === "en") return pref;
  const base = String(code || "ru").toLowerCase().split("-")[0];
  return RUSSIAN_LIKE.includes(base) ? "ru" : "en";
}

const current = resolveLang(
  getLangPreference(),
  tg.initDataUnsafe?.user?.language_code || (typeof navigator !== "undefined" ? navigator.language : "ru"),
);

export const lang = () => current;
export const locale = () => (current === "ru" ? "ru-RU" : "en-US");

export function t(key, vars) {
  const text = DICTS[current][key] ?? DICTS.ru[key] ?? key;
  return vars ? text.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m)) : text;
}

export const has = (key) => key in DICTS[current] || key in DICTS.ru;

export function plural(n, base) {
  let form = "many";
  if (current === "ru") {
    const m10 = n % 10;
    const m100 = n % 100;
    if (m10 === 1 && m100 !== 11) form = "one";
    else if ([2, 3, 4].includes(m10) && ![12, 13, 14].includes(m100)) form = "few";
  } else if (n === 1) {
    form = "one";
  }
  return t(base + "." + form);
}

export function applyStatic(root = document) {
  document.documentElement.lang = current;
  root.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  root.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  root.querySelectorAll("[data-i18n-aria]").forEach((el) => {
    el.setAttribute("aria-label", t(el.dataset.i18nAria));
  });
  root.querySelectorAll("[data-i18n-alt]").forEach((el) => {
    el.setAttribute("alt", t(el.dataset.i18nAlt));
  });
}
