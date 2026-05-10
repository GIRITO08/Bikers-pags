function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(";").shift();
  return "";
}

function postForm(url, data) {
  const csrf = getCookie("csrftoken");
  return fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
      "X-CSRFToken": csrf,
    },
    body: new URLSearchParams(data).toString(),
  }).then((r) => r.json());
}

function ensureToastStack() {
  let stack = qs(".toast-stack");
  if (!stack) {
    stack = document.createElement("div");
    stack.className = "toast-stack";
    stack.setAttribute("aria-live", "polite");
    stack.setAttribute("aria-atomic", "true");
    document.body.appendChild(stack);
  }
  return stack;
}

function showToast(message, kind = "success") {
  const stack = ensureToastStack();
  const toast = document.createElement("div");
  toast.className = `toast toast--${kind}`;
  toast.textContent = message;
  stack.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 4200);
}

function ensureFriendBell() {
  const right = qs(".topbar__right");
  if (!right) return null;
  let bell = qs("[data-friend-bell]", right);
  if (bell) return bell;
  bell = document.createElement("a");
  bell.className = "btn btn--ghost btn--sm notifbell";
  bell.setAttribute("href", "/feed/");
  bell.setAttribute("data-friend-bell", "1");
  bell.innerHTML = `<span class="mi material-symbols-rounded" aria-hidden="true">notifications</span><span class="notifbell__badge" data-friend-bell-badge hidden>0</span>`;
  right.insertBefore(bell, right.firstChild);
  return bell;
}

function setFriendBellCount(count) {
  const bell = ensureFriendBell();
  if (!bell) return;
  const badge = qs("[data-friend-bell-badge]", bell);
  if (!badge) return;
  const n = Math.max(0, parseInt(count || 0, 10) || 0);
  badge.textContent = String(n > 99 ? "99+" : n);
  badge.hidden = n <= 0;
}

function qs(sel, root = document) {
  return root.querySelector(sel);
}

function qsa(sel, root = document) {
  return Array.from(root.querySelectorAll(sel));
}

function initAccordion() {
  qsa("[data-accordion]").forEach((acc, idx) => {
    const btn = qs("[data-accordion-toggle]", acc);
    if (!btn) return;
    const open = idx === 0;
    acc.classList.toggle("is-open", open);
    btn.addEventListener("click", () => {
      acc.classList.toggle("is-open");
      if (window.gsap) {
        const body = qs(".accordion__body", acc);
        if (body && acc.classList.contains("is-open")) {
          gsap.fromTo(body, { opacity: 0, y: -6 }, { opacity: 1, y: 0, duration: 0.35, ease: "power2.out" });
        }
      }
    });
  });
}

function initSearch() {
  const root = qs("[data-search]");
  if (!root) return;
  const input = qs("[data-search-input]", root);
  const results = qs("[data-search-results]", root);
  if (!input || !results) return;

  let timer = null;
  let last = "";

  function render(items) {
    results.innerHTML = "";
    if (!items.length) {
      results.hidden = true;
      return;
    }
    items.forEach((u) => {
      const a = document.createElement("a");
      a.className = "search__item";
      a.href = `/riders/${encodeURIComponent(u.username)}/`;
      a.innerHTML = `
        <span class="avatar avatar--sm" style="background-image:url('${u.photo || ""}')"></span>
        <span class="search__meta">
          <span class="search__name">${u.name}</span>
          <span class="search__sub">@${u.username}</span>
        </span>
      `;
      results.appendChild(a);
    });
    results.hidden = false;
    if (window.gsap) gsap.fromTo(results, { opacity: 0, y: -6 }, { opacity: 1, y: 0, duration: 0.25 });
  }

  function close() {
    results.hidden = true;
  }

  input.addEventListener("input", () => {
    const q = input.value.trim();
    if (q === last) return;
    last = q;
    clearTimeout(timer);
    if (!q) {
      close();
      return;
    }
    timer = setTimeout(() => {
      fetch(`/api/search/?q=${encodeURIComponent(q)}`)
        .then((r) => r.json())
        .then((data) => render(data.results || []))
        .catch(() => close());
    }, 200);
  });

  document.addEventListener("click", (e) => {
    if (!root.contains(e.target)) close();
  });
}

function initFriendButtons() {
  qsa("[data-user-card]").forEach((card) => {
    const btn = qs("[data-add-friend]", card);
    if (btn) {
      btn.addEventListener("click", async () => {
        const userId = card.getAttribute("data-user-id");
        if (!userId) return;
        btn.disabled = true;
        btn.textContent = "Enviando...";
        try {
          const res = await postForm("/api/friends/request/", { user_id: userId });
          if (res && res.ok) {
            if (res.status === "accepted") {
              btn.textContent = "Amigos";
              btn.disabled = true;
            } else {
              btn.textContent = "Pendiente";
              btn.disabled = true;
            }
          } else {
            btn.textContent = "Error";
            btn.disabled = false;
          }
        } catch {
          btn.textContent = "Error";
          btn.disabled = false;
        }
      });
    }

    const acceptBtn = qs("[data-accept-friend]", card);
    if (acceptBtn) {
      acceptBtn.addEventListener("click", async () => {
        const requestId = acceptBtn.getAttribute("data-request-id");
        if (!requestId) return;
        acceptBtn.disabled = true;
        acceptBtn.textContent = "Aceptando...";
        try {
          const res = await postForm("/api/friends/accept/", { request_id: requestId });
          if (res && res.ok) {
            acceptBtn.textContent = "Amigos";
            acceptBtn.disabled = true;
            showToast("Solicitud aceptada", "success");
          } else {
            acceptBtn.textContent = "Error";
            acceptBtn.disabled = false;
          }
        } catch {
          acceptBtn.textContent = "Error";
          acceptBtn.disabled = false;
        }
      });
    }
  });
}

function initFriendUpdates() {
  if (!qs(".topbar")) return;
  const key = "tm_friend_updates_since";
  const keyIncoming = "tm_friend_incoming_since";
  let since = parseInt(localStorage.getItem(key) || "0", 10);
  let sinceIncoming = parseInt(localStorage.getItem(keyIncoming) || "0", 10);
  if (!since) {
    since = Date.now();
    localStorage.setItem(key, String(since));
  }
  if (!sinceIncoming) {
    sinceIncoming = Date.now();
    localStorage.setItem(keyIncoming, String(sinceIncoming));
  }

  async function poll() {
    try {
      const r = await fetch(`/api/friends/updates/?since=${encodeURIComponent(String(since))}`);
      const data = await r.json();
      if (!data || !data.ok) return;
      const events = Array.isArray(data.events) ? data.events : [];
      events.forEach((e) => {
        const name = (e && e.name) || "Un rider";
        showToast(`${name} aceptó tu solicitud`, "success");
      });
      const now = typeof data.now === "number" ? data.now : Date.now();
      const maxEvent = events.reduce((acc, e) => Math.max(acc, (e && e.ts) || 0), 0);
      since = Math.max(since, now, maxEvent);
      localStorage.setItem(key, String(since));
    } catch {}
  }

  async function pollIncoming() {
    try {
      const r = await fetch(`/api/friends/incoming/?since=${encodeURIComponent(String(sinceIncoming))}`);
      const data = await r.json();
      if (!data || !data.ok) return;
      setFriendBellCount(data.count || 0);
      const events = Array.isArray(data.events) ? data.events : [];
      events.forEach((e) => {
        const name = (e && e.name) || "Un rider";
        showToast(`${name} te envió solicitud`, "success");
      });
      const now = typeof data.now === "number" ? data.now : Date.now();
      const maxEvent = events.reduce((acc, e) => Math.max(acc, (e && e.ts) || 0), 0);
      sinceIncoming = Math.max(sinceIncoming, now, maxEvent);
      localStorage.setItem(keyIncoming, String(sinceIncoming));
    } catch {}
  }

  poll();
  pollIncoming();
  setInterval(() => {
    poll();
    pollIncoming();
  }, 12000);
}

function initCarousel() {
  const root = qs("[data-carousel]");
  if (!root) return;
  const track = qs("[data-carousel-track]", root);
  if (!track) return;
  const slides = qsa(".carousel__slide", track);
  if (!slides.length) return;
  const prev = qs("[data-carousel-prev]", root);
  const next = qs("[data-carousel-next]", root);

  let idx = 0;
  function show(i, dir = 1) {
    slides.forEach((s) => s.classList.remove("is-active"));
    const slide = slides[i];
    slide.classList.add("is-active");
    if (window.gsap) {
      gsap.fromTo(
        slide,
        { opacity: 0, x: dir > 0 ? 12 : -12 },
        { opacity: 1, x: 0, duration: 0.35, ease: "power2.out" }
      );
    }
  }
  function go(delta) {
    idx = (idx + delta + slides.length) % slides.length;
    show(idx, delta);
  }

  show(idx, 1);
  if (prev) prev.addEventListener("click", () => go(-1));
  if (next) next.addEventListener("click", () => go(1));

  setInterval(() => go(1), 6000);
}

function initStoriesScroll() {
  const row = qs("[data-stories-row]");
  if (!row) return;
  row.addEventListener(
    "wheel",
    (e) => {
      if (Math.abs(e.deltaY) <= Math.abs(e.deltaX)) return;
      row.scrollLeft += e.deltaY;
      e.preventDefault();
    },
    { passive: false }
  );
}

function initProfilePhotoUpload() {
  const form = qs("[data-photo-form]");
  if (!form) return;

  function setPreview(previewSel, file) {
    if (!file) return;
    const preview = qs(previewSel);
    if (!preview) return;
    const url = URL.createObjectURL(file);
    preview.style.backgroundImage = `url('${url}')`;
  }

  qsa("[data-dropzone]").forEach((zone) => {
    const type = zone.getAttribute("data-dropzone") || "";
    const previewSel = zone.getAttribute("data-preview") || "";
    const input = qs("input[type='file']", zone);
    if (!input) return;

    function onFiles(files) {
      const file = files && files[0];
      if (!file) return;
      setPreview(previewSel, file);
    }

    zone.addEventListener("dragover", (e) => {
      e.preventDefault();
      zone.classList.add("is-dragover");
    });
    zone.addEventListener("dragleave", () => zone.classList.remove("is-dragover"));
    zone.addEventListener("drop", (e) => {
      e.preventDefault();
      zone.classList.remove("is-dragover");
      if (!e.dataTransfer || !e.dataTransfer.files || !e.dataTransfer.files.length) return;
      input.files = e.dataTransfer.files;
      input.dispatchEvent(new Event("change", { bubbles: true }));
    });

    input.addEventListener("change", () => onFiles(input.files));

    const trigger = qs(`[data-upload-trigger='${type}']`);
    if (trigger) {
      trigger.addEventListener("click", () => input.click());
    }
  });
}

function initTopbarTabIndicator() {
  const nav = qs("[data-topbar-tabs]");
  if (!nav) return;
  const indicator = qs("[data-tab-indicator]", nav);
  const tabs = qsa(".topbar__tab", nav);
  if (!indicator || !tabs.length) return;

  function place(tab, animate) {
    if (!tab) return;
    const navRect = nav.getBoundingClientRect();
    const tabRect = tab.getBoundingClientRect();
    const x = Math.round(tabRect.left - navRect.left);
    const w = Math.round(tabRect.width);
    if (!animate) {
      const prev = indicator.style.transition;
      indicator.style.transition = "none";
      indicator.style.width = `${w}px`;
      indicator.style.transform = `translateX(${x}px)`;
      indicator.offsetHeight;
      indicator.style.transition = prev;
      return;
    }
    indicator.style.width = `${w}px`;
    indicator.style.transform = `translateX(${x}px)`;
  }

  const active = qs(".topbar__tab.is-active", nav) || tabs[0];
  const prevHref = sessionStorage.getItem("tm_prev_active_href") || "";
  const prevTab = prevHref ? tabs.find((t) => (t.getAttribute("href") || "") === prevHref) : null;
  if (prevTab && prevTab !== active) {
    place(prevTab, false);
    requestAnimationFrame(() => place(active, true));
  } else {
    place(active, false);
    requestAnimationFrame(() => place(active, true));
  }

  tabs.forEach((t) => {
    t.addEventListener("click", () => {
      const currentActive = qs(".topbar__tab.is-active", nav);
      const href = currentActive ? currentActive.getAttribute("href") || "" : "";
      if (href) sessionStorage.setItem("tm_prev_active_href", href);
    });
  });

  window.addEventListener("resize", () => place(qs(".topbar__tab.is-active", nav) || tabs[0], false));
}

function initGsapPage() {
  if (!window.gsap) return;
  const page = (window.TesaliaPage && window.TesaliaPage.name) || "";
  if (page === "login") {
    gsap.fromTo("[data-animate='auth']", { opacity: 0, y: 14, scale: 0.985 }, { opacity: 1, y: 0, scale: 1, duration: 0.55, ease: "power2.out" });
  }
  if (page === "feed") {
    gsap.fromTo("[data-animate='card']", { opacity: 0, scale: 0.99 }, { opacity: 1, scale: 1, duration: 0.45, stagger: 0.06, ease: "power2.out" });
  }
  if (page === "profile") {
    gsap.fromTo("[data-animate='hero']", { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.5, ease: "power2.out" });
  }
  if (page === "register") {
    gsap.fromTo(".register__header", { opacity: 0, y: -10 }, { opacity: 1, y: 0, duration: 0.45, ease: "power2.out" });
    gsap.fromTo(".accordion", { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.45, stagger: 0.04, ease: "power2.out" });
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initAccordion();
  initSearch();
  initFriendButtons();
  initFriendUpdates();
  initCarousel();
  initStoriesScroll();
  initProfilePhotoUpload();
  initTopbarTabIndicator();
  initGsapPage();
});
