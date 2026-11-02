import { icon } from "./icons.js";

// Создание элементов без innerHTML: текст пользователя всегда вставляется как текст.
export function h(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}

export const $ = (id) => document.getElementById(id);

// Иконка как элемент. Единственное место, где используется innerHTML:
// в него попадает только наш собственный SVG из icons.js, пользовательского текста тут нет.
export function iconEl(name, size = 22) {
  const el = document.createElement("span");
  el.className = "ico-svg";
  el.innerHTML = icon(name, size);
  return el;
}
