import { BUDGET_OCCUPATIONS, features, ideaFor } from "../constants.js";
import { $, h, iconEl } from "../dom.js";
import { t } from "../i18n.js";
import { goTo } from "../nav.js";
import { tg } from "../telegram.js";

export function initHome() {
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

  ideas.forEach((idea) => {
    const card = h("div", "idea");
    const tile = h("div", "icon");
    tile.appendChild(iconEl(idea.ic, 24));
    card.append(tile, h("b", "", idea.title), h("small", "", idea.text));
    list.appendChild(card);
  });
}

function renderFeatures() {
  const grid = $("features");
  grid.replaceChildren();
  features().forEach((f) => {
    const tile = h("div", "tile" + (f.soon ? " is-soon" : ""));
    const box = h("div", "icon");
    box.appendChild(iconEl(f.ic, 22));
    tile.append(box, h("b", "", f.title), h("small", "", f.text));
    if (f.soon) tile.appendChild(h("span", "badge", t("common.soon")));
    grid.appendChild(tile);
  });
}
