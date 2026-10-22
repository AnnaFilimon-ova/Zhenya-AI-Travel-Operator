// Создание элементов без innerHTML: текст пользователя всегда вставляется как текст.
export function h(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}

export const $ = (id) => document.getElementById(id);
