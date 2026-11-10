import { api } from "../api.js";
import { renderChips, selectedChips, setChips } from "../chips.js";
import { foodPrefs, occupations, travelTypes } from "../constants.js";
import { $, h } from "../dom.js";
import { t } from "../i18n.js";
import { react } from "../mascot.js";
import { initProgress, updateProgress } from "../profile-progress.js";

// onLoad / onSave вызываются с данными профиля, чтобы главная страница могла обновиться.
export function initProfile({ onLoad, onSave }) {
  renderChips("travel_types", travelTypes(), react);
  renderChips("food_prefs", foodPrefs(), react);
  fillOccupations();
  initProgress();
  $("with_pets").addEventListener("change", (e) => e.target.checked && react("pets"));
  $("accessible").addEventListener("change", (e) => e.target.checked && react("accessible"));

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
    home_city: $("home_city").value,
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
  $("home_city").value = p.home_city || "";
  $("with_pets").checked = p.with_pets;
  $("accessible").checked = p.accessible;
  $("favorite_places").value = p.favorite_places;
  setChips("travel_types", p.travel_types);
  setChips("food_prefs", p.food_prefs);
  updateProgress();
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
    react("saved");
  } catch {
    status.textContent = t("profile.saveFailed");
  } finally {
    button.disabled = false;
  }
}
