import { api } from "../api.js";
import { $, h, iconEl } from "../dom.js";
import { has, locale, plural, t } from "../i18n.js";
import { openLink, tg } from "../telegram.js";

const money = (n) => Number(n).toLocaleString(locale()) + " ₽";
const nightsWord = (n) => plural(n, "nights");
const kindLabel = (item) => (item.kind && has("hotelkind." + item.kind) ? t("hotelkind." + item.kind) : item.kind_label);

let busy = false;
let lastOrder = null; // только что оформленный заказ, чтобы показать его код
let payMessage = ""; // сообщение под кнопкой оплаты (ошибка или подсказка)

export function initCart() {
  document.querySelector('nav button[data-page="cart"]').addEventListener("click", loadCart);
  // Вернулись в мини-апп из чата, где могли добавить место в корзину.
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) loadCart();
  });
  loadCart();
}

async function loadCart() {
  try {
    const [cart, orders] = await Promise.all([api("/api/cart"), api("/api/orders")]);
    render(cart, orders.orders);
  } catch {
    $("cart-root").replaceChildren(h("div", "card", t("cart.loadFailed")));
  }
}

function updateBadge(count) {
  const badge = $("cart-count");
  badge.textContent = String(count);
  badge.hidden = count === 0;
}

function render(cart, orders) {
  const root = $("cart-root");
  root.replaceChildren();
  updateBadge(cart.items.length);

  if (lastOrder) root.appendChild(renderSuccess(lastOrder));

  if (cart.items.length === 0) {
    if (!lastOrder) root.appendChild(renderEmpty());
  } else {
    cart.items.forEach((item) => root.appendChild(item.type === "ticket" ? renderTicket(item) : renderItem(item)));
    root.appendChild(renderSummary(cart));
  }

  if (orders.length > 0) root.appendChild(renderOrders(orders));
}

function renderEmpty() {
  const card = h("div", "card cart-empty");
  card.append(
    h("b", "", t("cart.emptyTitle")),
    h("small", "", t("cart.emptyText")),
  );
  const btn = h("button", "idea-btn", t("cart.backToChat"));
  btn.type = "button";
  btn.addEventListener("click", () => tg.close());
  card.appendChild(btn);
  return card;
}

function renderItem(item) {
  const card = h("div", "card cart-item");

  const head = h("div", "cart-head");
  const title = h("div", "cart-title");
  title.append(h("b", "", item.name), h("small", "", [kindLabel(item), has("city." + item.city) ? t("city." + item.city) : item.city, item.address || t("cart.noAddress")].join(" · ")));
  const del = h("button", "icon-btn");
  del.type = "button";
  del.setAttribute("aria-label", t("cart.delete"));
  del.appendChild(iconEl("trash", 18));
  del.addEventListener("click", () => act(() => api("/api/cart/" + item.id, { method: "DELETE" })));
  head.append(title, del);

  const row = h("div", "cart-row");
  const stepper = h("div", "stepper");
  const minus = h("button", "icon-btn");
  minus.type = "button";
  minus.disabled = item.nights <= 1;
  minus.setAttribute("aria-label", t("cart.fewerNights"));
  minus.appendChild(iconEl("minus", 16));
  minus.addEventListener("click", () => setNights(item, item.nights - 1));
  const plus = h("button", "icon-btn");
  plus.type = "button";
  plus.disabled = item.nights >= 30;
  plus.setAttribute("aria-label", t("cart.moreNights"));
  plus.appendChild(iconEl("plus", 16));
  plus.addEventListener("click", () => setNights(item, item.nights + 1));
  stepper.append(minus, h("span", "stepper-value", item.nights + " " + nightsWord(item.nights)), plus);

  const price = h("div", "cart-price");
  price.append(h("b", "", "≈ " + money(item.subtotal)), h("small", "", "≈ " + money(item.price_per_night_est) + " " + t("cart.perNight")));
  row.append(stepper, price);

  card.append(head, row);
  return card;
}

function dateText(value) {
  if (!value || value.length < 10) return "";
  const [y, m, d] = value.slice(0, 10).split("-").map(Number);
  const date = new Date(y, m - 1, d).toLocaleDateString(locale(), { day: "numeric", month: "long" });
  const time = value.length >= 16 && value[10] === "T" ? " " + value.slice(11, 16) : "";
  return date + time;
}

function durationText(minutes) {
  if (typeof minutes !== "number") return "";
  return t("ticket.duration", { h: Math.floor(minutes / 60), m: String(minutes % 60).padStart(2, "0") });
}

function renderTicket(item) {
  const card = h("div", "card cart-item");

  const head = h("div", "cart-head");
  const title = h("div", "cart-title");
  const name = h("b", "with-ico");
  const city = (value) => (has("city." + value) ? t("city." + value) : value);
  name.append(iconEl("plane", 18), `${city(item.origin)} → ${city(item.destination)}`);
  title.append(name, h("small", "", [t("ticket.plane"), dateText(item.depart_at)].filter(Boolean).join(" · ")));
  const del = h("button", "icon-btn");
  del.type = "button";
  del.setAttribute("aria-label", t("ticket.remove"));
  del.appendChild(iconEl("trash", 18));
  del.addEventListener("click", () => act(() => api("/api/cart/ticket/" + item.ticket_id, { method: "DELETE" })));
  head.append(title, del);

  const row = h("div", "cart-row");
  const info = [durationText(item.duration_min), typeof item.transfers === "number" ? (item.transfers === 0 ? t("ticket.direct") : t("ticket.transfers", { n: item.transfers })) : ""].filter(Boolean);
  const left = h("div", "");
  left.appendChild(h("small", "", info.join(" · ")));
  const price = h("div", "cart-price");
  price.appendChild(h("b", "", "≈ " + money(item.subtotal)));
  row.append(left, price);
  card.append(head, row);

  if (/^https:\/\//.test(item.url || "")) {
    const buy = h("button", "idea-btn with-ico");
    buy.type = "button";
    buy.append(iconEl("link", 16), t("ticket.buy"));
    buy.addEventListener("click", () => openLink(item.url));
    card.appendChild(buy);
  }
  return card;
}

function renderSummary(cart) {
  const card = h("div", "card cart-summary");
  const total = h("div", "total-row");
  total.append(h("span", "", t("cart.total")), h("b", "", "≈ " + money(cart.total)));
  const pay = h("button", "save", t("cart.pay"));
  pay.type = "button";
  pay.addEventListener("click", () => startPayment(pay));
  card.append(total, pay);
  if (payMessage) card.appendChild(h("small", "cart-note", payMessage));
  return card;
}

// Оплата: сервер отвечает либо готовым заказом (демо), либо ссылкой на счёт Telegram (ЮKassa).
async function startPayment(button) {
  if (busy) return;
  busy = true;
  button.disabled = true;
  payMessage = "";
  try {
    const known = (await api("/api/orders")).orders[0]?.code ?? null;
    const res = await api("/api/cart/checkout", { method: "POST" });
    if (res.mode === "demo") {
      lastOrder = res.order;
    } else if (res.mode === "invoice") {
      const status = await openInvoice(res.url);
      if (status === "paid") {
        lastOrder = await waitForOrder(known);
        if (!lastOrder) payMessage = t("cart.paidPending");
      } else if (status === "failed") {
        payMessage = t("cart.payFailed");
      }
    }
  } catch {
    payMessage = t("cart.payStartFailed");
  } finally {
    busy = false;
  }
  await loadCart();
}

function openInvoice(url) {
  return new Promise((resolve) => {
    if (typeof tg.openInvoice !== "function") {
      payMessage = t("cart.invoiceOnlyTelegram");
      resolve("unsupported");
      return;
    }
    tg.openInvoice(url, resolve);
  });
}

// Заказ создаёт бот после подтверждения платежа, поэтому ждём его появления в списке.
async function waitForOrder(knownCode) {
  for (let i = 0; i < 10; i++) {
    const top = (await api("/api/orders")).orders[0];
    if (top && top.code !== knownCode) return top;
    await new Promise((r) => setTimeout(r, 1000));
  }
  return null;
}

function renderSuccess(order) {
  const card = h("div", "card cart-success");
  const title = h("div", "with-ico success-title");
  title.append(iconEl("done", 22), h("b", "", t("cart.orderDone")));
  const code = h("div", "order-code", order.code);
  const how = order.provider === "telegram_yookassa" ? t("cart.howYookassa") : t("cart.howDemo");
  const info = h("small", "", t("cart.orderInfo", { total: money(order.total), how }));
  const ok = h("button", "idea-btn", t("cart.ok"));
  ok.type = "button";
  ok.addEventListener("click", () => {
    lastOrder = null;
    loadCart();
  });
  card.append(title, code, info, ok);
  return card;
}

function renderOrders(orders) {
  const box = h("div", "orders");
  box.appendChild(h("h3", "", t("cart.myOrders")));
  orders.forEach((o) => {
    const card = h("div", "card order-row");
    const date = new Date(o.created_at).toLocaleDateString(locale());
    const names = o.items.map((i) => i.name).join(", ");
    const left = h("div", "");
    left.append(h("b", "", o.code), h("small", "", date + " · " + names));
    card.append(left, h("b", "", "≈ " + money(o.total)));
    box.appendChild(card);
  });
  return box;
}

async function setNights(item, nights) {
  await act(() => api("/api/cart/" + item.id, { method: "PATCH", body: JSON.stringify({ nights }) }));
}

async function act(request) {
  if (busy) return;
  busy = true;
  try {
    await request();
  } catch {
  } finally {
    busy = false;
  }
  await loadCart();
}
