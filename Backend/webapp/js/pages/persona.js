import { api } from "../api.js";
import { PERSONA_KEYS, personas } from "../constants.js";
import { $, h, iconEl } from "../dom.js";
import { t } from "../i18n.js";

let current = "any";
let saving = false;

export const getPersona = () => current;

export async function initPersona() {
  render();
  try {
    const data = await api("/api/settings");
    if (PERSONA_KEYS.includes(data.persona)) current = data.persona;
    render();
  } catch {
  }
}

function setStatus(text) {
  $("persona-status").textContent = text;
}

function render() {
  const root = $("persona-root");
  root.replaceChildren();
  personas().forEach((p) => {
    const on = p.key === current;
    const btn = h("button", "persona-option" + (on ? " on" : ""));
    btn.type = "button";
    btn.setAttribute("aria-pressed", String(on));

    const avatar = h("span", "persona-avatar");
    if (p.image) {
      const img = h("img");
      img.src = p.image;
      img.alt = "";
      img.width = 52;
      img.height = 52;
      avatar.appendChild(img);
    } else {
      avatar.appendChild(iconEl("persona", 26));
    }

    const body = h("span", "persona-body");
    const title = h("b", "", p.title);
    if (p.tag) title.appendChild(h("span", "persona-tag", p.tag));
    body.append(title, h("small", "", p.text));

    const mark = h("span", "persona-mark");
    if (on) mark.appendChild(iconEl("check", 18));

    btn.append(avatar, body, mark);
    btn.addEventListener("click", () => choose(p.key));
    root.appendChild(btn);
  });
}

async function choose(key) {
  if (key === current || saving) return;
  const previous = current;
  current = key;
  saving = true;
  render();
  setStatus(t("persona.saving"));
  try {
    await api("/api/settings", { method: "PUT", body: JSON.stringify({ persona: key }) });
    setStatus(t("persona.saved"));
  } catch {
    current = previous;
    render();
    setStatus(t("persona.failed"));
  } finally {
    saving = false;
  }
}
