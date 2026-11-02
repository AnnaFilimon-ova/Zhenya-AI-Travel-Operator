import { api } from "../api.js";
import { renderChips, selectedChips, setChips } from "../chips.js";
import { foodPrefs, occupations, travelTypes } from "../constants.js";
import { $, h } from "../dom.js";
import { t } from "../i18n.js";

// onLoad / onSave вызываются с данными профиля, чтобы главная страница могла обновиться.
export function initProfile({ onLoad, onSave }) {
  renderChips("travel_types", travelTypes());
  renderChips("food_prefs", foodPrefs());
  fillOccupations();

  $("save").addEventListener("click", () => save(onSave));
  load(onLoad);
}

function fillOccupations() {
  const select = $("occupation");
  select.replaceChildren();
  occupations().forEach(([value, label]) => {
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
    $("status").textContent = t("profile.openInTelegram");
  }
}

async function save(onSave) {
  const button = $("save");
  const status = $("status");
  button.disabled = true;
  status.textContent = t("profile.saving");
  try {
    const data = collect();
    await api("/api/profile", { method: "PUT", body: JSON.stringify(data) });
    status.textContent = t("profile.saved");
    onSave?.(data);
  } catch {
    status.textContent = t("profile.saveFailed");
  } finally {
    button.disabled = false;
  }
}
