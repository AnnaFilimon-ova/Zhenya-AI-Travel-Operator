import { $, h, iconEl } from "./dom.js";

// options: [[ключ, подпись, имя_иконки?], ...]
export function renderChips(containerId, options) {
  const box = $(containerId);
  box.replaceChildren();
  options.forEach(([key, label, iconName]) => {
    const btn = h("button", "chip");
    if (iconName) btn.appendChild(iconEl(iconName, 16));
    btn.appendChild(h("span", "", label));
    btn.type = "button";
    btn.dataset.key = key;
    btn.addEventListener("click", () => btn.classList.toggle("on"));
    box.appendChild(btn);
  });
}

export function selectedChips(containerId) {
  return Array.from(document.querySelectorAll("#" + containerId + " .chip.on")).map((b) => b.dataset.key);
}

export function setChips(containerId, keys) {
  document.querySelectorAll("#" + containerId + " .chip").forEach((b) => {
    b.classList.toggle("on", keys.includes(b.dataset.key));
  });
}
