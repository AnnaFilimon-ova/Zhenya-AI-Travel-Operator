import { tg } from "./telegram.js";

// Запрос к нашему серверу. Подпись Telegram (initData) отправляем в заголовке:
// по ней сервер понимает, кто пришёл.
export async function api(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: "tma " + tg.initData,
    },
  });
  if (!res.ok) throw new Error("HTTP " + res.status);
  return res.json();
}
