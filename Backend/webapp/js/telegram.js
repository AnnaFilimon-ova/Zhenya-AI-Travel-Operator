const noop = () => {};

export const tg = window.Telegram?.WebApp ?? {
  initData: "",
  initDataUnsafe: {},
  colorScheme: "light",
  ready: noop,
  expand: noop,
  close: noop,
  setHeaderColor: noop,
  setBackgroundColor: noop,
  onEvent: noop,
};

export const isInTelegram = Boolean(tg.initData);

export function openLink(url) {
  if (typeof tg.openLink === "function") tg.openLink(url);
  else window.open(url, "_blank", "noopener");
}
