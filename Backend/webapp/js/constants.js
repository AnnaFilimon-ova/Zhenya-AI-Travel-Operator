import { t } from "./i18n.js";

const TRAVEL_KEYS = ["beach", "city", "nature", "culture", "active", "relax", "gastro", "nightlife", "gothic", "aesthetic", "music", "shopping"];
const FOOD_KEYS = ["vegan", "vegetarian", "meat", "fish", "seafood", "halal"];
const OCCUPATION_KEYS = ["", "schoolchild", "student", "working", "freelancer", "entrepreneur", "retired", "other"];

export const travelTypes = () => TRAVEL_KEYS.map((k) => [k, t("travel." + k), k]);
export const foodPrefs = () => FOOD_KEYS.map((k) => [k, t("food." + k), k]);
export const occupations = () => OCCUPATION_KEYS.map((k) => [k, t("occupation." + (k || "none"))]);

export const BUDGET_OCCUPATIONS = ["schoolchild", "student"];

export const IDEA_ICONS = {
  beach: "beach", city: "city", nature: "nature", culture: "culture", active: "active", relax: "relax",
  gastro: "gastro", nightlife: "nightlife", gothic: "gothic", aesthetic: "aesthetic", music: "music", shopping: "shopping",
};
export const ideaFor = (key) =>
  IDEA_ICONS[key] ? { ic: IDEA_ICONS[key], title: t(`idea.${key}.title`), text: t(`idea.${key}.text`) } : null;

const FEATURE_DEFS = [
  ["trip", "trip", false],
  ["hotels", "hotels", false],
  ["prefs", "prefs", false],
  ["places", "places", false],
  ["events", "events", true],
  ["routes", "routes", true],
];
export const features = () =>
  FEATURE_DEFS.map(([k, ic, soon]) => ({ key: k, ic, soon, title: t(`feature.${k}.title`), text: t(`feature.${k}.text`) }));

const PERSONA_DEFS = [
  ["female", "/static/zhenya-female.webp"],
  ["male", "/static/zhenya-male.webp"],
  ["any", ""],
];
export const PERSONA_KEYS = PERSONA_DEFS.map(([k]) => k);
export const personas = () =>
  PERSONA_DEFS.map(([key, image]) => ({
    key,
    image,
    title: t(`persona.${key}.title`),
    tag: t(`persona.${key}.tag`),
    text: t(`persona.${key}.text`),
  }));
