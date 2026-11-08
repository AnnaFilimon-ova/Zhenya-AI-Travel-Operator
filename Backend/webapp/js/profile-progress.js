import { $, h, iconEl } from "./dom.js";
import { t } from "./i18n.js";
import { react } from "./mascot.js";

const STEPS = [
  { key: "name", icon: "profile", target: "display_name", done: (d) => d.name.trim().length > 0 },
  { key: "occupation", icon: "student", target: "occupation", done: (d) => d.occupation !== "" },
  { key: "food", icon: "gastro", target: "food_prefs", done: (d) => d.food > 0 },
  { key: "travel", icon: "aesthetic", target: "travel_types", done: (d) => d.travel > 0 },
  { key: "place", icon: "places", target: "favorite_places", done: (d) => d.place.trim().length > 0 },
];

let root = null;
let fill = null;
let pct = null;
let title = null;
let stepEls = [];
let last = -1;

function snapshot() {
  return {
    name: $("display_name").value,
    occupation: $("occupation").value,
    food: document.querySelectorAll("#food_prefs .chip.on").length,
    travel: document.querySelectorAll("#travel_types .chip.on").length,
    place: $("favorite_places").value,
  };
}

function build() {
  root = $("profile-progress");
  const top = h("div", "progress-top");
  title = h("b", "", t("progress.title"));
  pct = h("span", "progress-pct", "0%");
  top.append(title, pct);

  const track = h("div", "progress-track");
  fill = h("i");
  track.appendChild(fill);

  const steps = h("div", "progress-steps");
  stepEls = STEPS.map((s) => {
    const btn = h("button", "step");
    btn.type = "button";
    const ic = h("span", "bub-ic");
    ic.appendChild(iconEl(s.icon, 16));
    const ck = h("span", "bub-ck");
    ck.appendChild(iconEl("check", 10));
    ic.appendChild(ck);
    btn.append(ic, h("span", "bub-label", t("progress." + s.key)));
    btn.addEventListener("click", () => {
      const el = $(s.target);
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      if (el.focus && el.tagName !== "DIV") setTimeout(() => el.focus({ preventScroll: true }), 350);
    });
    steps.appendChild(btn);
    return btn;
  });

  root.append(top, track, steps, h("small", "progress-hint", t("progress.hint")));
}

export function updateProgress(announce = false) {
  if (!root) return;
  const data = snapshot();
  let done = 0;
  STEPS.forEach((s, i) => {
    const ok = s.done(data);
    if (ok) done += 1;
    const el = stepEls[i];
    if (el.classList.contains("done") !== ok) {
      el.classList.toggle("done", ok);
      if (ok && last >= 0) {
        el.classList.remove("pop");
        void el.offsetWidth;
        el.classList.add("pop");
      }
    }
  });
  const value = Math.round((done / STEPS.length) * 100);
  fill.style.width = value + "%";
  pct.textContent = value + "%";
  const complete = value === 100;
  root.classList.toggle("complete", complete);
  title.textContent = t(complete ? "progress.complete" : "progress.title");
  if (announce && complete && last < 100 && last >= 0) react("complete");
  last = value;
}

export function initProgress() {
  build();
  updateProgress();
  const page = $("page-profile");
  ["input", "change", "click"].forEach((ev) => page.addEventListener(ev, () => updateProgress(true)));
}
