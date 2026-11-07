import { tg, isInTelegram } from "./telegram.js";

const KEY = "zhenya-theme"; // auto | light | dark
const HEADER_COLORS = { light: "#ffffff", dark: "#162238" };
const BG_COLORS = { light: "#f4f7fc", dark: "#0e1626" };

export function getThemePreference() {
  try {
    return localStorage.getItem(KEY) || "auto";
  } catch {
    return "auto";
  }
}

function systemTheme() {
  if (isInTelegram) return tg.colorScheme === "dark" ? "dark" : "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function applyTheme() {
  const pref = getThemePreference();
  const theme = pref === "auto" ? systemTheme() : pref;
  document.documentElement.dataset.theme = theme;
  try {
    tg.setHeaderColor(HEADER_COLORS[theme]);
    tg.setBackgroundColor(BG_COLORS[theme]);
  } catch {
    /* старые версии Telegram не умеют менять цвета */
  }
  return theme;
}

export function setThemePreference(pref) {
  try {
    localStorage.setItem(KEY, pref);
  } catch {
    /* хранилище может быть недоступно */
  }
  applyTheme();
}

export function initTheme() {
  applyTheme();
  tg.onEvent("themeChanged", applyTheme);
  window.matchMedia?.("(prefers-color-scheme: dark)").addEventListener?.("change", applyTheme);
}
