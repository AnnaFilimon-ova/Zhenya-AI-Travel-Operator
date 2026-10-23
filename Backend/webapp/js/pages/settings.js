import { getThemePreference, setThemePreference } from "../theme.js";

export function initSettings() {
  const buttons = document.querySelectorAll("[data-theme-choice]");

  const mark = () => {
    const current = getThemePreference();
    buttons.forEach((b) => b.classList.toggle("active", b.dataset.themeChoice === current));
  };

  buttons.forEach((b) => {
    b.addEventListener("click", () => {
      setThemePreference(b.dataset.themeChoice);
      mark();
    });
  });
  mark();
}
