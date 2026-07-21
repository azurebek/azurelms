(function () {
  var tg = window.Telegram && window.Telegram.WebApp;
  if (!tg) return;

  try {
    tg.ready();
    tg.expand();

    if (!tg.isVersionAtLeast || tg.isVersionAtLeast("6.1")) {
      tg.setHeaderColor("secondary_bg_color");
      tg.setBackgroundColor("secondary_bg_color");
    }

    if (tg.colorScheme === "dark") {
      document.documentElement.dataset.theme = "dark";
    }

    tg.onEvent("themeChanged", function () {
      if (tg.colorScheme === "dark") {
        document.documentElement.dataset.theme = "dark";
      } else {
        delete document.documentElement.dataset.theme;
      }
    });
  } catch (error) {
    // Telegram WebApp API versiyasi eski bo'lsa sahifa oddiy web rejimida ishlaydi.
  }
})();
