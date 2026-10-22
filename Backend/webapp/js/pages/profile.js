import { api } from "../api.js";
import { renderChips, selectedChips, setChips } from "../chips.js";
import { FOOD_PREFS, OCCUPATIONS, TRAVEL_TYPES } from "../constants.js";
import { $, h } from "../dom.js";

// onLoad / onSave вызываются с данными профиля, чтобы главная страница могла обновиться.
export function initProfile({ onLoad, onSave }) {
  renderChips("travel_types", TRAVEL_TYPES);
  renderChips("food_prefs", FOOD_PREFS);
  fillOccupations();

  $("save").addEventListener("click", () => save(onSave));
  load(onLoad);
}

function fillOccupations() {
  const select = $("occupation");
  select.replaceChildren();
  OCCUPATIONS.forEach(([value, label]) => {
    const option = h("option", "", label);
    option.value = value;
    select.appendChild(option);
  });
}

function collect() {
  return {
    display_name: $("display_name").value,
    gender: $("gender").value,
    occupation: $("occupation").value,
    with_pets: $("with_pets").checked,
    accessible: $("accessible").checked,
    travel_types: selectedChips("travel_types"),
    food_prefs: selectedChips("food_prefs"),
    favorite_places: $("favorite_places").value,
  };
}

function fill(p) {
  $("display_name").value = p.display_name;
  $("gender").value = p.gender;
  $("occupation").value = p.occupation;
  $("with_pets").checked = p.with_pets;
  $("accessible").checked = p.accessible;
  $("favorite_places").value = p.favorite_places;
  setChips("travel_types", p.travel_types);
  setChips("food_prefs", p.food_prefs);
}

async function load(onLoad) {
  try {
    const profile = await api("/api/profile");
    fill(profile);
    onLoad?.(profile);
  } catch {
    $("status").textContent = "Открой приложение из Telegram, чтобы сохранять профиль.";
  }
}

async function save(onSave) {
  const button = $("save");
  const status = $("status");
  button.disabled = true;
  status.textContent = "Сохраняю...";
  try {
    const data = collect();
    await api("/api/profile", { method: "PUT", body: JSON.stringify(data) });
    status.textContent = "Сохранено ✅ Женя запомнила";
    onSave?.(data);
  } catch {
    status.textContent = "Не удалось сохранить. Попробуй ещё раз.";
  } finally {
    button.disabled = false;
  }
}
