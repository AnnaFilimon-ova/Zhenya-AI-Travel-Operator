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
