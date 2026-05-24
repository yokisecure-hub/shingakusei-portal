(() => {
  const state = {
    config: null,
    activeCategory: "all",
    channel: "web",
  };

  const $ = (id) => document.getElementById(id);

  async function loadConfig() {
    const res = await fetch("config.json", { cache: "no-store" });
    if (!res.ok) throw new Error(`config.json fetch failed: ${res.status}`);
    return res.json();
  }

  function detectChannel(cfg) {
    const param = cfg.tracking?.channel_param || "src";
    const url = new URL(window.location.href);
    const v = (url.searchParams.get(param) || "").toLowerCase();
    const channels = cfg.tracking?.channels || {};
    if (v && channels[v]) return v;
    return cfg.tracking?.default_channel || "web";
  }

  function decorateUrl(rawUrl, cfg, channel) {
    if (!rawUrl || rawUrl === "#") return rawUrl;
    let u;
    try {
      u = new URL(rawUrl);
    } catch {
      return rawUrl;
    }
    const tracking = cfg.tracking || {};
    const channels = tracking.channels || {};
    const medium = channels[channel]?.medium || channel;
    const source = tracking.utm_source || "tenant-portal";
    if (!u.searchParams.has("utm_source")) u.searchParams.set("utm_source", source);
    if (!u.searchParams.has("utm_medium")) u.searchParams.set("utm_medium", medium);
    if (!u.searchParams.has("utm_campaign")) {
      const campaign = (cfg.portal?.property_name || "tenant-portal").replace(/\s+/g, "-");
      u.searchParams.set("utm_campaign", campaign);
    }
    return u.toString();
  }

  function renderHeader(cfg) {
    if (cfg.portal?.title) {
      $("portalTitle").textContent = cfg.portal.title;
      document.title = cfg.portal.title;
    }
    if (cfg.portal?.subtitle) $("portalSubtitle").textContent = cfg.portal.subtitle;
    if (cfg.portal?.property_name) $("propertyName").textContent = cfg.portal.property_name;
    if (cfg.portal?.footer_note) $("footerNote").textContent = cfg.portal.footer_note;
  }

  function renderOptInBanner(cfg) {
    const banner = $("optInBanner");
    if (!banner) return;
    const opt = cfg.optin_banner;
    if (!opt?.enabled) {
      banner.hidden = true;
      return;
    }
    const titleEl = banner.querySelector(".optin__title");
    const msgEl = banner.querySelector(".optin__message");
    if (opt.title && titleEl) titleEl.textContent = opt.title;
    if (opt.message && msgEl) msgEl.textContent = opt.message;
    banner.hidden = false;
  }

  function renderTabs(cfg) {
    const tabs = $("categoryTabs");
    tabs.innerHTML = "";
    const items = [{ id: "all", label: "すべて" }, ...(cfg.categories || [])];
    for (const cat of items) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "tab";
      btn.textContent = cat.label;
      btn.setAttribute("aria-pressed", String(cat.id === state.activeCategory));
      btn.addEventListener("click", () => {
        state.activeCategory = cat.id;
        renderTabs(state.config);
        renderCards(state.config);
      });
      tabs.appendChild(btn);
    }
  }

  function renderCards(cfg) {
    const wrap = $("serviceCards");
    const empty = $("emptyState");
    wrap.innerHTML = "";

    const list = (cfg.services || []).filter((s) =>
      state.activeCategory === "all" ? true : s.category === state.activeCategory
    );

    if (list.length === 0) {
      empty.hidden = false;
      return;
    }
    empty.hidden = true;

    for (const svc of list) {
      const card = document.createElement("article");
      card.className = "card";

      const head = document.createElement("div");
      head.className = "card__head";

      const icon = document.createElement("div");
      icon.className = "card__icon";
      icon.setAttribute("aria-hidden", "true");
      icon.textContent = svc.icon || "🔗";

      const titleWrap = document.createElement("div");
      const title = document.createElement("h2");
      title.className = "card__title";
      title.textContent = svc.name || "";
      titleWrap.appendChild(title);
      if (svc.tagline) {
        const tag = document.createElement("span");
        tag.className = "card__tag";
        tag.textContent = svc.tagline;
        titleWrap.appendChild(tag);
      }

      head.appendChild(icon);
      head.appendChild(titleWrap);
      card.appendChild(head);

      if (svc.description) {
        const desc = document.createElement("p");
        desc.className = "card__desc";
        desc.textContent = svc.description;
        card.appendChild(desc);
      }

      const cta = document.createElement("a");
      cta.className = "card__cta";
      cta.href = decorateUrl(svc.url || "#", cfg, state.channel);
      cta.target = "_blank";
      cta.rel = "noopener noreferrer sponsored";
      cta.textContent = svc.cta || "詳しく見る";
      card.appendChild(cta);

      wrap.appendChild(card);
    }
  }

  async function init() {
    try {
      state.config = await loadConfig();
      state.channel = detectChannel(state.config);
      document.documentElement.setAttribute("data-channel", state.channel);
      renderHeader(state.config);
      renderOptInBanner(state.config);
      renderTabs(state.config);
      renderCards(state.config);
    } catch (err) {
      console.error(err);
      $("serviceCards").innerHTML =
        '<p style="color:#b00;text-align:center;">設定ファイルを読み込めませんでした。</p>';
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
