import { $, h } from "./dom.js";

export function renderChips(containerId, options) {
  const box = $(containerId);
  box.replaceChildren();
  options.forEach(([key, label]) => {
    const btn = h("button", "chip", label);
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
