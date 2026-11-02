import { api } from "../api.js";
import { $, h, iconEl } from "../dom.js";
import { has, lang, t } from "../i18n.js";
import { tg } from "../telegram.js";

const FALLBACK_CATEGORIES = ["food", "sights", "culture", "nature", "evening"].map((key) => ({ key, suggested: false }));
const categoryLabel = (c) => (has("cat." + c.key) ? t("cat." + c.key) : c.label || c.key);
const CATEGORY_ICONS = {
  food: "gastro", sights: "aesthetic", culture: "culture", nature: "nature", evening: "nightlife",
  gothic: "gothic", beach: "beach", active: "active", relax: "relax", music: "music", shopping: "shopping",
};
const radii = () => [
  [500, "500 " + t("unit.m")],
  [1000, "1 " + t("unit.km")],
  [2000, "2 " + t("unit.km")],
];

const state = { category: "food", radius: 1000, lat: null, lon: null, city: "", loaded: false };
let requestId = 0;

export function initNearby() {
  buildChips("nearby-cats", toOptions(FALLBACK_CATEGORIES), "category");
  buildChips("nearby-radius", radii(), "radius");
  loadCategories();

  $("nearby-locate").addEventListener("click", locate);
  $("nearby-city").addEventListener("change", () => {
    const city = $("nearby-city").value;
    if (!city) return;
    state.city = city;
    state.lat = state.lon = null;
    setStatus(t("nearby.searchingCity", { city: has("city." + city) ? t("city." + city) : city }));
    load();
  });
  document.querySelector('nav button[data-page="nearby"]').addEventListener("click", () => {
    if (!state.loaded && state.lat === null && !state.city) showHint();
  });
  showHint();
}

const toOptions = (list) => list.map((c) => [c.key, categoryLabel(c), CATEGORY_ICONS[c.key], c.suggested]);

async function loadCategories() {
  try {
    const { categories } = await api("/api/nearby/categories");
    if (!Array.isArray(categories) || categories.length === 0) return;
    const first = categories.find((c) => c.suggested);
    if (first && !state.loaded) state.category = first.key;
    buildChips("nearby-cats", toOptions(categories), "category");
  } catch {
  }
}

function buildChips(id, options, key) {
  const box = $(id);
  box.replaceChildren();
  options.forEach(([value, label, iconName, suggested]) => {
    const btn = h("button", "chip" + (state[key] === value ? " on" : "") + (suggested ? " suggested" : ""));
    if (iconName) btn.appendChild(iconEl(iconName, 16));
    btn.appendChild(h("span", "", label));
    btn.type = "button";
    btn.addEventListener("click", () => {
      state[key] = value;
      box.querySelectorAll(".chip").forEach((c) => c.classList.toggle("on", c === btn));
      if (hasPlace()) load();
    });
    box.appendChild(btn);
  });
}

const hasPlace = () => state.lat !== null || Boolean(state.city);

function setStatus(text) {
  $("nearby-status").textContent = text;
}

function showHint() {
  $("nearby-root").replaceChildren(
    card(t("nearby.hintTitle"), t("nearby.hintText")),
  );
}

function card(title, text) {
  const c = h("div", "card cart-empty");
  c.append(h("b", "", title), h("small", "", text));
  return c;
}

function locate() {
  if (!navigator.geolocation) {
    setStatus(t("nearby.noGeo"));
    return;
  }
  setStatus(t("nearby.locating"));
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const { latitude: lat, longitude: lon } = pos.coords;
      if (lat < 41 || lat > 82 || lon < 19 || lon > 180) {
        setStatus(t("nearby.notRussia"));
        return;
      }
      state.lat = lat;
      state.lon = lon;
      state.city = "";
      $("nearby-city").value = "";
      setStatus(t("nearby.showingNear"));
      load();
    },
    () => setStatus(t("nearby.geoFailed")),
    { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 },
  );
}

async function load() {
  const id = ++requestId;
  const root = $("nearby-root");
  root.replaceChildren(card(t("nearby.loadingTitle"), t("nearby.loadingText")));
  const params = new URLSearchParams({ category: state.category, radius: String(state.radius) });
  if (state.city) params.set("city", state.city);
  else {
    params.set("lat", String(state.lat));
    params.set("lon", String(state.lon));
  }
  try {
    const data = await api("/api/nearby?" + params.toString());
    if (id !== requestId) return;
    state.loaded = true;
    render(data);
  } catch {
    if (id !== requestId) return;
    root.replaceChildren(card(t("nearby.errorTitle"), t("nearby.errorText")));
  }
}

const distance = (m) =>
  m < 1000 ? m + " " + t("unit.m") : (m / 1000).toFixed(1).replace(".", lang() === "ru" ? "," : ".") + " " + t("unit.km");

function openLink(url) {
  if (typeof tg.openLink === "function") tg.openLink(url);
  else window.open(url, "_blank", "noopener");
}

function render(data) {
  const root = $("nearby-root");
  root.replaceChildren();
  if (data.items.length === 0) {
    root.appendChild(card(t("nearby.emptyTitle"), t("nearby.emptyText")));
  }
  data.items.forEach((p) => root.appendChild(renderPlace(p)));
  if (data.total > data.items.length) {
    root.appendChild(h("small", "cart-note", t("nearby.shown", { shown: data.items.length, total: data.total })));
  }
  root.appendChild(h("small", "cart-note", t("nearby.note") + (data.offline ? " " + t("nearby.offlineNote") : "")));
}

function renderPlace(p) {
  const c = h("div", "card place");
  const head = h("div", "cart-head");
  const title = h("div", "cart-title");
  const kind = p.kind_key && has("kind." + p.kind_key) ? t("kind." + p.kind_key) : p.kind;
  const cuisine = Array.isArray(p.cuisine_keys)
    ? p.cuisine_keys.filter((k) => has("cuisine." + k)).map((k) => t("cuisine." + k)).join(", ")
    : p.cuisine;
  const meta = [kind, cuisine, p.address].filter(Boolean).join(" · ");
  title.append(h("b", "", p.name), h("small", "", meta));
  head.append(title, h("b", "place-dist", distance(p.distance_m)));
  c.appendChild(head);

  if (p.badges.length) {
    const row = h("div", "place-badges");
    p.badges.forEach((b) => row.appendChild(h("span", "tag" + (b.match ? " match" : ""), b.key && has("badge." + b.key) ? t("badge." + b.key) : b.text)));
    c.appendChild(row);
  }
  if (p.opening_hours) c.appendChild(h("small", "cart-note", t("nearby.hours", { hours: p.opening_hours })));

  const links = h("div", "place-links");
  const map = h("button", "idea-btn", t("nearby.onMap"));
  map.type = "button";
  map.addEventListener("click", () =>
    openLink(`https://yandex.ru/maps/?pt=${p.lon},${p.lat}&z=17&l=map`),
  );
  links.appendChild(map);
  if (/^https?:\/\//.test(p.website)) {
    const site = h("button", "idea-btn", t("nearby.site"));
    site.type = "button";
    site.addEventListener("click", () => openLink(p.website));
    links.appendChild(site);
  }
  c.appendChild(links);
  return c;
}
