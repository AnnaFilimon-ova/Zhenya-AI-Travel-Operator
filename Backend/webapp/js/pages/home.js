import { BUDGET_OCCUPATIONS, features, ideaFor } from "../constants.js";
import { $, h, iconEl } from "../dom.js";
import { t } from "../i18n.js";
import { react } from "../mascot.js";
import { goTo } from "../nav.js";
import { tg } from "../telegram.js";

function enableDragScroll(el) {
  let down = false;
  let moved = false;
  let startX = 0;
  let startLeft = 0;
  el.addEventListener(
    "wheel",
    (e) => {
      if (el.scrollWidth <= el.clientWidth || Math.abs(e.deltaX) > Math.abs(e.deltaY)) return;
      e.preventDefault();
      el.scrollLeft += e.deltaY;
    },
    { passive: false },
  );
  el.addEventListener("pointerdown", (e) => {
    if (e.pointerType !== "mouse") return;
    down = true;
    moved = false;
    startX = e.clientX;
    startLeft = el.scrollLeft;
  });
  window.addEventListener("pointermove", (e) => {
    if (!down) return;
    const dx = e.clientX - startX;
    if (Math.abs(dx) > 5) {
      moved = true;
      el.style.scrollSnapType = "none";
    }
    if (moved) el.scrollLeft = startLeft - dx;
  });
  window.addEventListener("pointerup", () => {
    if (!down) return;
    down = false;
    el.style.scrollSnapType = "";
  });
  el.addEventListener(
    "click",
    (e) => {
      if (moved) {
        e.stopPropagation();
        e.preventDefault();
        moved = false;
      }
    },
    true,
  );
}

export function initHome() {
  enableDragScroll($("interest-list"));
  renderFeatures();
  $("cta-chat").addEventListener("click", () => tg.close());
  renderHome(null);
}

// profile — данные из /api/profile (или то, что только что сохранили). null — профиль ещё не загружен.
export function renderHome(profile) {
  renderGreeting(profile);
  renderBudgetNote(profile);
  renderIdeas(profile);
}

function renderGreeting(profile) {
  const name = profile?.display_name || tg.initDataUnsafe?.user?.first_name || "";
  $("greeting").textContent = name ? t("home.helloName", { name }) : t("home.hello");
}

function renderBudgetNote(profile) {
  const note = $("budget-note");
  const budget = BUDGET_OCCUPATIONS.includes(profile?.occupation);
  note.hidden = !budget;
  note.replaceChildren();
  if (budget) {
    const line = h("span", "with-ico");
    line.append(iconEl("student", 20), t("home.budgetNote"));
    note.appendChild(line);
  }
}

function renderIdeas(profile) {
  const list = $("interest-list");
  list.replaceChildren();

  const ideas = (profile?.travel_types ?? []).map(ideaFor).filter(Boolean);

  if (ideas.length === 0) {
    const card = h("div", "idea empty");
    card.append(h("b", "", t("home.emptyTitle")), h("small", "", t("home.emptyText")));
    const btn = h("button", "", t("home.fillProfile"));
    btn.type = "button";
    btn.addEventListener("click", () => goTo("profile"));
    card.appendChild(btn);
    list.appendChild(card);
    return;
  }

  ideas.forEach((idea, i) => {
    const card = h("button", "idea v" + (i % 4));
    card.type = "button";
    card.style.setProperty("--i", i);
    const tile = h("div", "icon");
    tile.appendChild(iconEl(idea.ic, 24));
    const more = h("span", "more");
    more.append(h("span", "", t("home.ideaOpen")), iconEl("arrow", 15));
    card.append(tile, h("b", "", idea.title), h("small", "", idea.text), more);
    card.addEventListener("click", () => {
      react("ideaGo");
      goTo("nearby");
    });
    list.appendChild(card);
  });
}

const FEATURE_ACTIONS = {
  trip: () => chat("tripGo"),
  hotels: () => chat("hotelsGo"),
  prefs: () => goTo("profile"),
  places: () => goTo("nearby"),
  events: () => react("soon"),
  routes: () => react("soon"),
};

function chat(key) {
  react(key);
  setTimeout(() => tg.close(), 1500);
}

function renderFeatures() {
  const grid = $("features");
  grid.replaceChildren();
  features().forEach((f, i) => {
    const tile = h("button", "tile v" + ((Math.floor(i / 2) + i) % 2) + (f.soon ? " is-soon" : ""));
    tile.type = "button";
    tile.style.setProperty("--i", i);
    const box = h("div", "icon");
    box.appendChild(iconEl(f.ic, 22));
    tile.append(box, h("b", "", f.title), h("small", "", f.text));
    if (f.soon) {
      tile.appendChild(h("span", "badge", t("common.soon")));
    } else {
      const arrow = h("span", "arrow");
      arrow.appendChild(iconEl("arrow", 15));
      tile.appendChild(arrow);
    }
    tile.addEventListener("click", () => FEATURE_ACTIONS[f.key]?.());
    grid.appendChild(tile);
  });
}
