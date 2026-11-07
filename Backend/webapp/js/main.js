import { applyStatic } from "./i18n.js";
import { initNav } from "./nav.js";
import { initCart } from "./pages/cart.js";
import { initHome, renderHome } from "./pages/home.js";
import { initNearby } from "./pages/nearby.js";
import { initPersona } from "./pages/persona.js";
import { initProfile } from "./pages/profile.js";
import { initSettings } from "./pages/settings.js";
import { tg } from "./telegram.js";
import { initTheme } from "./theme.js";

tg.ready();
tg.expand();

applyStatic();
initTheme();
initNav();
initSettings();
initHome();
initProfile({ onLoad: renderHome, onSave: renderHome });
initCart();
initNearby();
initPersona();

const splash = document.getElementById("splash");
const shownAt = performance.now();
const MIN_SHOW = 1100;

function hideSplash() {
  if (!splash) return;
  const wait = Math.max(0, MIN_SHOW - (performance.now() - shownAt));
  setTimeout(() => {
    splash.classList.add("hide");
    setTimeout(() => splash.remove(), 600);
  }, wait);
}

if (document.readyState === "complete") hideSplash();
else window.addEventListener("load", hideSplash, { once: true });
setTimeout(hideSplash, 6000);
