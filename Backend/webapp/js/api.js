import { tg } from "./telegram.js";

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
