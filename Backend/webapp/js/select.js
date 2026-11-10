const CHEVRON =
  '<svg class="select-chevron" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" ' +
  'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>';

const valueDesc = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value");
const openBoxes = new Set();

function closeAll(except) {
  openBoxes.forEach((box) => {
    if (box !== except) box.close();
  });
}

function enhance(select) {
  if (select.dataset.enhanced) return;
  select.dataset.enhanced = "1";

  const box = document.createElement("div");
  box.className = "select";
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "select-btn";
  btn.setAttribute("aria-haspopup", "listbox");
  const label = document.createElement("span");
  btn.appendChild(label);
  btn.insertAdjacentHTML("beforeend", CHEVRON);
  const list = document.createElement("ul");
  list.className = "select-list";
  list.setAttribute("role", "listbox");
  list.hidden = true;

  select.classList.add("select-native");
  select.tabIndex = -1;
  select.after(box);
  box.append(btn, list);

  function syncLabel() {
    const opt = select.options[select.selectedIndex];
    label.textContent = opt ? opt.text : "";
  }

  function renderList() {
    list.replaceChildren();
    Array.from(select.options).forEach((opt, index) => {
      const li = document.createElement("li");
      const item = document.createElement("button");
      item.type = "button";
      item.className = "select-item" + (index === select.selectedIndex ? " selected" : "");
      item.setAttribute("role", "option");
      item.textContent = opt.text;
      item.addEventListener("click", () => {
        valueDesc.set.call(select, opt.value);
        syncLabel();
        select.dispatchEvent(new Event("change", { bubbles: true }));
        api.close();
        btn.focus();
      });
      li.appendChild(item);
      list.appendChild(li);
    });
  }

  const api = {
    close() {
      box.classList.remove("open", "up");
      list.hidden = true;
      btn.setAttribute("aria-expanded", "false");
      openBoxes.delete(api);
    },
    open() {
      closeAll(api);
      renderList();
      list.hidden = false;
      box.classList.add("open");
      btn.setAttribute("aria-expanded", "true");
      openBoxes.add(api);
      const rect = btn.getBoundingClientRect();
      const need = Math.min(list.scrollHeight, 248) + 90;
      box.classList.toggle("up", window.innerHeight - rect.bottom < need && rect.top > need);
      list.querySelector(".selected")?.scrollIntoView({ block: "nearest" });
    },
  };

  btn.addEventListener("click", () => (list.hidden ? api.open() : api.close()));

  Object.defineProperty(select, "value", {
    configurable: true,
    get() {
      return valueDesc.get.call(this);
    },
    set(v) {
      valueDesc.set.call(this, v);
      syncLabel();
    },
  });
  new MutationObserver(syncLabel).observe(select, { childList: true });
  select.addEventListener("change", syncLabel);
  syncLabel();
}

document.addEventListener("click", (e) => {
  if (!e.target.closest(".select")) closeAll();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeAll();
});

export function enhanceSelects(root = document) {
  root.querySelectorAll("select").forEach(enhance);
}

enhanceSelects();
