import { icon } from "./icons.js";

export function h(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}

export const $ = (id) => document.getElementById(id);

export function iconEl(name, size = 22) {
  const el = document.createElement("span");
  el.className = "ico-svg";
  el.innerHTML = icon(name, size);
  return el;
}
