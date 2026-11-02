import { $ } from "./dom.js";

export function goTo(page) {
  document.querySelectorAll("nav button").forEach((b) => {
    b.classList.toggle("active", b.dataset.page === page);
  });
  document.querySelectorAll(".page").forEach((p) => p.classList.remove("active"));
  $("page-" + page).classList.add("active");
  window.scrollTo(0, 0);
}

export function initNav() {
  document.querySelectorAll("nav button").forEach((btn) => {
    btn.addEventListener("click", () => goTo(btn.dataset.page));
  });
}
