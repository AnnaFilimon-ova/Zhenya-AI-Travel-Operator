import { getLangPreference, setLangPreference } from "../i18n.js";
import { getThemePreference, setThemePreference } from "../theme.js";

function bindSwitch(selector, attr, get, set) {
  const buttons = document.querySelectorAll(selector);
  const mark = () => {
    const current = get();
    buttons.forEach((b) => b.classList.toggle("active", b.dataset[attr] === current));
  };
  buttons.forEach((b) => {
    b.addEventListener("click", () => {
      if (b.dataset[attr] === get()) return;
      set(b.dataset[attr]);
      mark();
    });
  });
  mark();
}

export function initSettings() {
  bindSwitch("[data-theme-choice]", "themeChoice", getThemePreference, setThemePreference);
  bindSwitch("[data-lang-choice]", "langChoice", getLangPreference, (pref) => {
    setLangPreference(pref);
    location.reload();
  });
}
