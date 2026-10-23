import { initNav } from "./nav.js";
import { initHome, renderHome } from "./pages/home.js";
import { initProfile } from "./pages/profile.js";
import { initSettings } from "./pages/settings.js";
import { tg } from "./telegram.js";
import { initTheme } from "./theme.js";

tg.ready();
tg.expand();

initTheme();
initNav();
initSettings();
initHome();
initProfile({ onLoad: renderHome, onSave: renderHome });
