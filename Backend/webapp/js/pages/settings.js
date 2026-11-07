import { getLangPreference, setLangPreference } from "../i18n.js";
import { getThemePreference, setThemePreference } from "../theme.js";

function bindSwitch(selector, attr, get, set, delay = 0) {
  const buttons = document.querySelectorAll(selector);
  if (buttons.length === 0) return;
  const box = buttons[0].parentElement;
  const pill = document.createElement("span");
  pill.className = "seg-pill instant";
  box.classList.add("has-pill");
  box.prepend(pill);

  const place = (animate) => {
    const active = box.querySelector("button.active");
    if (!active || active.offsetWidth === 0) return;
    pill.classList.toggle("instant", !animate);
    pill.style.width = active.offsetWidth + "px";
    pill.style.transform = "translateX(" + active.offsetLeft + "px)";
  };

  const mark = (animate) => {
    const current = get();
    buttons.forEach((b) => b.classList.toggle("active", b.dataset[attr] === current));
    place(animate);
  };

  buttons.forEach((b) => {
    b.addEventListener("click", () => {
      if (b.dataset[attr] === get()) return;
      mark(true);
      b.classList.add("active");
      buttons.forEach((o) => o !== b && o.classList.remove("active"));
      place(true);
      setTimeout(() => set(b.dataset[attr]), delay);
    });
  });
  mark(false);
  new ResizeObserver(() => place(false)).observe(box);
  document.fonts?.ready.then(() => place(false));
}

export function initSettings() {
  bindSwitch("[data-theme-choice]", "themeChoice", getThemePreference, setThemePreference);
  bindSwitch(
    "[data-lang-choice]",
    "langChoice",
    getLangPreference,
    (pref) => {
      setLangPreference(pref);
      location.reload();
    },
    450,
  );
}
