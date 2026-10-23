// Обёртка над Telegram WebApp. Вне Telegram (обычный браузер) подставляем заглушку,
// чтобы страницу можно было разрабатывать без бота.
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
