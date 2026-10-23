import { BUDGET_OCCUPATIONS, FEATURES, INTEREST_IDEAS } from "../constants.js";
import { $, h } from "../dom.js";
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
  $("greeting").textContent = "Привет" + (name ? ", " + name : "") + "!";
}

function renderBudgetNote(profile) {
  const note = $("budget-note");
  const budget = BUDGET_OCCUPATIONS.includes(profile?.occupation);
  note.hidden = !budget;
  if (budget) note.textContent = "🎓 Учту, что бюджет ограничен: буду искать бюджетные варианты.";
}

function renderIdeas(profile) {
  const list = $("interest-list");
  list.replaceChildren();

  const ideas = (profile?.travel_types ?? []).map((key) => INTEREST_IDEAS[key]).filter(Boolean);

  if (ideas.length === 0) {
    const card = h("div", "idea empty");
    card.append(h("b", "", "Пока пусто"), h("small", "", "Выбери, что тебе интересно, в профиле, и здесь появятся идеи."));
    const btn = h("button", "", "Заполнить профиль");
    btn.type = "button";
    btn.addEventListener("click", () => goTo("profile"));
    card.appendChild(btn);
    list.appendChild(card);
    return;
  }

  ideas.forEach((idea) => {
    const card = h("div", "idea");
    card.append(h("div", "icon", idea.icon), h("b", "", idea.title), h("small", "", idea.text));
    list.appendChild(card);
  });
}

function renderFeatures() {
  const grid = $("features");
  grid.replaceChildren();
  FEATURES.forEach((f) => {
    const tile = h("div", "tile" + (f.soon ? " is-soon" : ""));
    tile.append(h("div", "icon", f.icon), h("b", "", f.title), h("small", "", f.text));
    if (f.soon) tile.appendChild(h("span", "badge", "скоро"));
    grid.appendChild(tile);
  });
}
