(function () {
  const DISMISS_KEY = "head2head-install-dismissed";
  const INSTALLED_KEY = "head2head-installed";
  const FALLBACK_DELAY_MS = 3000;

  function isStandalone() {
    return (
      window.matchMedia("(display-mode: standalone)").matches ||
      window.navigator.standalone === true
    );
  }

  function isAndroid() {
    return /Android/i.test(navigator.userAgent);
  }

  function createBanner() {
    const banner = document.createElement("div");
    banner.id = "install-banner";
    banner.className = "install-banner";
    banner.hidden = true;
    banner.innerHTML =
      '<p class="install-banner-text"></p>' +
      '<div class="install-banner-actions">' +
      '<button type="button" class="install-banner-install">Install</button>' +
      '<button type="button" class="install-banner-dismiss">Dismiss</button>' +
      "</div>";
    document.body.prepend(banner);
    return banner;
  }

  function setBannerMessage(banner, message, { showInstall = true } = {}) {
    banner.querySelector(".install-banner-text").textContent = message;
    banner.querySelector(".install-banner-install").hidden = !showInstall;
    banner.hidden = false;
  }

  function init() {
    if (!isAndroid() || isStandalone()) {
      return;
    }

    const banner = createBanner();
    const installBtn = banner.querySelector(".install-banner-install");
    const dismissBtn = banner.querySelector(".install-banner-dismiss");
    let deferredPrompt = null;
    let fallbackTimer = null;

    if (localStorage.getItem(INSTALLED_KEY) === "1") {
      setBannerMessage(
        banner,
        "Installed. Share a race link from RTRT or Sportstats and choose Head2Head.",
        { showInstall: false }
      );
      return;
    }

    if (localStorage.getItem(DISMISS_KEY) === "1") {
      return;
    }

    dismissBtn.addEventListener("click", () => {
      localStorage.setItem(DISMISS_KEY, "1");
      banner.hidden = true;
      if (fallbackTimer) {
        clearTimeout(fallbackTimer);
      }
    });

    installBtn.addEventListener("click", async () => {
      if (!deferredPrompt) {
        return;
      }
      deferredPrompt.prompt();
      const choice = await deferredPrompt.userChoice;
      deferredPrompt = null;
      if (choice.outcome === "accepted") {
        localStorage.setItem(INSTALLED_KEY, "1");
        setBannerMessage(
          banner,
          "Installed. Share a race link from RTRT or Sportstats and choose Head2Head.",
          { showInstall: false }
        );
      }
    });

    window.addEventListener("beforeinstallprompt", (event) => {
      event.preventDefault();
      deferredPrompt = event;
      if (fallbackTimer) {
        clearTimeout(fallbackTimer);
        fallbackTimer = null;
      }
      setBannerMessage(
        banner,
        "Install Head2Head to compare splits from the share menu.",
        { showInstall: true }
      );
    });

    window.addEventListener("appinstalled", () => {
      localStorage.setItem(INSTALLED_KEY, "1");
      setBannerMessage(
        banner,
        "Installed. Share a race link from RTRT or Sportstats and choose Head2Head.",
        { showInstall: false }
      );
    });

    fallbackTimer = window.setTimeout(() => {
      if (deferredPrompt || banner.hidden) {
        return;
      }
      setBannerMessage(
        banner,
        "Install Head2Head: Chrome menu (⋮) → Install app. Then share race links directly to Head2Head.",
        { showInstall: false }
      );
    }, FALLBACK_DELAY_MS);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
