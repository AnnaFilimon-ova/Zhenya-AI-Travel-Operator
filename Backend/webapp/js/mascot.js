import { h } from "./dom.js";
import { lang } from "./i18n.js";
import reactions from "./locales/reactions.js";
import { getPersona } from "./pages/persona.js";

const SHOW_MS = 4400;
const HEADS = { female: "/static/zhenya-female.webp", male: "/static/zhenya-male.webp", any: "/static/zhenya-female.webp" };

let root = null;
let head = null;
let text = null;
let timer = 0;

function build() {
  root = h("div", "mascot");
  root.id = "mascot";
  root.setAttribute("role", "status");
  root.setAttribute("aria-live", "polite");
  head = h("img", "mascot-head");
  head.alt = "";
  head.width = 64;
  head.height = 56;
  const bubble = h("div", "mascot-bubble");
  text = h("p", "mascot-text");
  bubble.appendChild(text);
  root.append(head, bubble);
  root.addEventListener("click", hide);
  document.body.appendChild(root);
}

export function hide() {
  clearTimeout(timer);
  root?.classList.remove("show");
}

export function say(message, persona = getPersona()) {
  if (!root) build();
  head.src = HEADS[persona] || HEADS.any;
  text.textContent = message;
  root.classList.remove("show");
  void root.offsetWidth;
  root.classList.add("show");
  clearTimeout(timer);
  timer = setTimeout(hide, SHOW_MS);
}

export function react(key) {
  const set = reactions[lang()]?.[key] || reactions.ru[key];
  if (!set) return;
  const persona = getPersona();
  const message = persona === "male" ? set[2] : set[Math.floor(Math.random() * 2)];
  say(message, persona);
}

