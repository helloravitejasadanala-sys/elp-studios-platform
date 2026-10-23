const $ = (sel, root = document) => root.querySelector(sel);
const main = $("#main");
const topbar = $("#topbar-actions");

const state = {
  config: null,
  token: sessionStorage.getItem("elpToken") || "",
  signedIn: sessionStorage.getItem("elpSignedIn") === "1",
  view: "login",
  events: [],
  storage: null,
  cssByStyle: {},
  wizardTab: 0,
  created: null,
  uploads: [],
};

const DRAFT_KEY = "elp-studio-draft";

function defaultDraft() {
  return {
    brand_id: "mini-momentz",
    event_name: "",
    event_type: "other",
    event_date: "",
    duration: "full-day",
    client_name: "",
    client_email: "",
    client_phone: "",
    layout: "grid",
    welcome: "",
    watermark: false,
    access: "password",
    password: "Gallery" + Math.floor(1000 + Math.random() * 9000),
    expiration_days: 180,
    allow_downloads: true,
    allow_original: true,
    feedback_enabled: true,
    allow_favorites: true,
    allow_likes: true,
    allow_comments: true,
    allow_user_uploads: false,
    publish_now: false,
  };
}

function loadDraft() {
  try {
    return { ...defaultDraft(), ...JSON.parse(localStorage.getItem(DRAFT_KEY) || "{}") };
  } catch {
    return defaultDraft();
  }
}

function saveDraft(partial) {
  const next = { ...loadDraft(), ...partial };
  localStorage.setItem(DRAFT_KEY, JSON.stringify(next));
  return next;
}

function brandById(id) {
  return (state.config?.brands || []).find((b) => b.id === id) || state.config?.brands?.[0];
}

function shareLink(event) {
  const origin = state.config?.picpeakPublicOrigin || "http://localhost:3000";
  if (!event?.slug || !event?.share_token) return "";
  return `${origin}/gallery/${event.slug}/${event.share_token}`;
}

function shareText(brand, link) {
  const template =
    brand?.whatsapp_share_template ||
    "Your photographs are ready! We've put together your gallery so you can relive all those beautiful moments.\n\nView your gallery: {link}\n\n{brand}";
  return template.replaceAll("{link}", link).replaceAll("{brand}", brand?.display_name || "");
}

function waUrl(message, phone) {
  const digits = String(phone || "").replace(/\D+/g, "");
  const base = digits ? `https://wa.me/${digits}` : "https://wa.me/";
  return `${base}?text=${encodeURIComponent(message)}`;
}

async function api(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  if (opts.json) {
    headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(opts.json);
  }
  const res = await fetch("/pp" + path, { ...opts, headers, credentials: "include" });
  const text = await res.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { raw: text };
  }
  if (!res.ok) {
    const err = new Error(data.error || data.message || text || `HTTP ${res.status}`);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

function clearLocalSession() {
  state.token = "";
  state.signedIn = false;
  sessionStorage.removeItem("elpToken");
  sessionStorage.removeItem("elpSignedIn");
}

function markSignedIn(token) {
  state.signedIn = true;
  sessionStorage.setItem("elpSignedIn", "1");
  if (token) {
    state.token = token;
    sessionStorage.setItem("elpToken", token);
  } else {
    state.token = "";
    sessionStorage.removeItem("elpToken");
  }
}

async function logoutPicPeak() {
  try {
    await api("/api/auth/logout", { method: "POST" });
  } catch {
    /* still clear the console view; cookie clear is the server's job */
  }
  clearLocalSession();
  state.view = "login";
  render();
}

function render() {
  topbar.innerHTML = "";
  if (state.signedIn) {
    topbar.innerHTML = `
      <button class="btn" data-go="dashboard">Galleries</button>
      <button class="btn" data-go="storage">Storage</button>
      <button class="btn primary" data-go="wizard">New gallery</button>
      <button class="btn ghost" id="logout">Log out</button>
    `;
    $("#logout").onclick = () => logoutPicPeak();
  }
  topbar.querySelectorAll("[data-go]").forEach((btn) => {
    btn.onclick = () => {
      state.view = btn.dataset.go;
      render();
    };
  });
  if (!state.signedIn || state.view === "login") return renderLogin();
  if (state.view === "wizard") return renderWizard();
  if (state.view === "event") return renderEvent();
  if (state.view === "storage") return renderStorage();
  return renderDashboard();
}

function renderLogin() {
  main.innerHTML = `
    <div class="card" style="max-width:420px;margin:2rem auto;">
      <h2>Sign in</h2>
      <p class="muted">Use the same PicPeak admin username and password as http://localhost:3000/admin</p>
      <label>Username</label>
      <input id="user" value="admin" autocomplete="username" />
      <label>Password</label>
      <input id="pass" type="password" autocomplete="current-password" />
      <p class="error" id="login-error"></p>
      <p style="margin-top:1rem;"><button class="btn primary" id="login">Continue</button></p>
    </div>`;
  $("#login").onclick = async () => {
    $("#login-error").textContent = "";
    try {
      const data = await api("/api/auth/admin/login", {
        method: "POST",
        json: { username: $("#user").value, password: $("#pass").value },
      });
      if (data.mfaRequired) {
        throw new Error("This admin account requires 2FA. Finish sign-in in PicPeak Admin at /admin, then try again.");
      }
      if (!data.user) {
        throw new Error("PicPeak rejected the login (no admin user in the response).");
      }
      if (data.mustChangePassword || data.user?.mustChangePassword) {
        $("#login-error").textContent = "PicPeak requires an admin password change in /admin first.";
        return;
      }
      // aio:stable puts the JWT in the HttpOnly admin_token cookie, not in JSON.
      const jsonToken = data.token || data.user?.token || "";
      markSignedIn(jsonToken || "");
      try {
        const session = await api("/api/auth/session");
        if (session.valid === false) {
          throw new Error(session.error || "PicPeak session cookie was not accepted.");
        }
      } catch (sessionErr) {
        clearLocalSession();
        throw sessionErr;
      }
      state.view = "dashboard";
      await bootstrap();
      await loadEvents();
      render();
    } catch (err) {
      $("#login-error").textContent = err.message;
    }
  };
}

async function bootstrap() {
  try {
    const templates = await api("/api/admin/css-templates");
    const list = templates.templates || templates || [];
    for (const t of list) {
      const slot = t.slot_number || t.slot;
      const brand = (state.config.brands || []).find((b) => Number(b.css_slot) === Number(slot));
      if (brand) state.cssByStyle[brand.default_style] = t.id;
    }
  } catch {
    /* CSS templates optional until apply-platform-settings.py has been run */
  }
  try {
    state.storage = await api("/api/admin/settings/storage/info");
  } catch {
    state.storage = null;
  }
}

async function loadEvents() {
  const data = await api("/api/admin/events?page=1&limit=100");
  state.events = data.events || data || [];
}

function eventStatus(ev) {
  if (ev.is_archived || ev.status === "archived") return "archived";
  if (ev.expires_at && new Date(ev.expires_at) < new Date()) return "expired";
  if (ev.is_draft) return "draft";
  return "published";
}

function renderDashboard() {
  const q = (state.filterQ || "").toLowerCase();
  const brandF = state.filterBrand || "";
  const statusF = state.filterStatus || "";
  const rows = state.events.filter((ev) => {
    const brand = inferBrand(ev);
    const blob = `${ev.event_name || ""} ${ev.customer_name || ""} ${ev.customer_email || ""}`.toLowerCase();
    if (q && !blob.includes(q)) return false;
    if (brandF && brand !== brandF) return false;
    if (statusF && eventStatus(ev) !== statusF) return false;
    return true;
  });
  const used = state.storage?.total_used;
  const disk = state.storage?.disk_total;
  main.innerHTML = `
    <div class="grid two">
      <div class="card">
        <p class="eyebrow">Galleries</p>
        <h2 style="margin:0">${state.events.length} on this PicPeak</h2>
        <p class="muted">Existing photos stay in the Docker volume. This console does not delete media.</p>
      </div>
      <div class="card">
        <p class="eyebrow">Storage</p>
        <h2 style="margin:0">${used != null ? formatBytes(used) : "See PicPeak Admin"} used</h2>
        <p class="muted">${disk != null ? "Reported capacity " + formatBytes(disk) + " is usually the Windows/WSL2 virtual disk, not Synology." : "Run scripts/verify-storage.ps1 for the volume path."}</p>
        <p><button class="btn" data-go="storage">Storage &amp; costs</button></p>
      </div>
    </div>
    <div class="card" style="margin-top:1rem">
      <div class="row">
        <input id="search" placeholder="Search event or client" style="flex:1;min-width:180px" />
        <select id="brand-filter"><option value="">All brands</option>${(state.config.brands || [])
          .map((b) => `<option value="${b.id}">${esc(b.display_name)}</option>`)
          .join("")}</select>
        <select id="status-filter">
          <option value="">All statuses</option>
          <option value="draft">Draft</option>
          <option value="published">Published</option>
          <option value="expired">Expired</option>
        </select>
        <button class="btn" id="refresh">Refresh</button>
      </div>
      <div style="overflow:auto;margin-top:0.8rem">
        <table class="table">
          <thead><tr><th>Gallery</th><th>Brand</th><th>Client</th><th>Status</th><th></th></tr></thead>
          <tbody>
            ${
              rows
                .map((ev) => {
                  const brand = brandById(inferBrand(ev));
                  const st = eventStatus(ev);
                  return `<tr>
                    <td><strong>${esc(ev.event_name || "Untitled")}</strong><br><span class="muted">${esc(ev.event_date || "")}</span></td>
                    <td>${esc(brand?.display_name || "—")}</td>
                    <td>${esc(ev.customer_name || "—")}<br><span class="muted">${esc(ev.customer_email || ev.customer_phone || "")}</span></td>
                    <td><span class="badge ${st}">${st}</span></td>
                    <td><button class="btn" data-open="${ev.id}">Open</button></td>
                  </tr>`;
                })
                .join("") || `<tr><td colspan="5" class="muted">No galleries match.</td></tr>`
            }
          </tbody>
        </table>
      </div>
    </div>`;
  $("#search").value = state.filterQ || "";
  $("#brand-filter").value = state.filterBrand || "";
  $("#status-filter").value = state.filterStatus || "";
  $("#search").oninput = (e) => {
    state.filterQ = e.target.value;
    renderDashboard();
  };
  $("#brand-filter").onchange = (e) => {
    state.filterBrand = e.target.value;
    renderDashboard();
  };
  $("#status-filter").onchange = (e) => {
    state.filterStatus = e.target.value;
    renderDashboard();
  };
  $("#refresh").onclick = async () => {
    await loadEvents();
    renderDashboard();
  };
  main.querySelectorAll("[data-open]").forEach((btn) => {
    btn.onclick = () => openEvent(Number(btn.dataset.open));
  });
  main.querySelectorAll("[data-go]").forEach((btn) => {
    btn.onclick = () => {
      state.view = btn.dataset.go;
      render();
    };
  });
}

function inferBrand(ev) {
  const welcome = ev.welcome_message || "";
  const m = welcome.match(/elp-brand:([a-z0-9-]+)/);
  if (m) return m[1];
  const name = (ev.event_name || "").toLowerCase();
  for (const b of state.config.brands || []) {
    if (name.includes(b.display_name.toLowerCase())) return b.id;
  }
  return "";
}

function openEvent(id) {
  state.created = state.events.find((e) => e.id === id) || { id };
  state.view = "event";
  render();
}

function renderWizard() {
  const d = loadDraft();
  const brand = brandById(d.brand_id);
  const tabs = ["Event details", "Gallery design", "Access & security", "Guest features", "Review & create"];
  if (!d.welcome && brand) saveDraft({ welcome: brand.welcome, brand_id: brand.id });
  const tab = state.wizardTab;
  main.innerHTML = `
    <div class="card">
      <div class="tabs">${tabs
        .map((t, i) => `<button class="tab ${i === tab ? "active" : ""}" data-tab="${i}">${i + 1}. ${t}</button>`)
        .join("")}</div>
      <div id="tab-body" style="margin-top:1rem"></div>
      <div class="row" style="margin-top:1rem;justify-content:space-between">
        <button class="btn" id="prev" ${tab === 0 ? "disabled" : ""}>Back</button>
        <div class="row">
          <button class="btn ghost" id="save-draft">Save draft locally</button>
          ${tab < 4 ? `<button class="btn primary" id="next">Continue</button>` : `<button class="btn accent" id="create">Create gallery</button>`}
        </div>
      </div>
      <p class="error" id="wiz-error"></p>
    </div>`;
  const body = $("#tab-body");
  if (tab === 0) body.innerHTML = tabDetails(d);
  if (tab === 1) body.innerHTML = tabDesign(d, brand);
  if (tab === 2) body.innerHTML = tabAccess(d);
  if (tab === 3) body.innerHTML = tabGuests(d);
  if (tab === 4) body.innerHTML = tabReview(d, brand);
  bindWizardFields();
  main.querySelectorAll("[data-tab]").forEach((btn) => {
    btn.onclick = () => {
      collectWizard();
      state.wizardTab = Number(btn.dataset.tab);
      renderWizard();
    };
  });
  $("#prev").onclick = () => {
    collectWizard();
    state.wizardTab = Math.max(0, tab - 1);
    renderWizard();
  };
  $("#save-draft").onclick = () => {
    collectWizard();
    $("#wiz-error").textContent = "Saved in this browser. Nothing was sent to PicPeak yet.";
    $("#wiz-error").className = "success";
  };
  const next = $("#next");
  if (next)
    next.onclick = () => {
      collectWizard();
      state.wizardTab = Math.min(4, tab + 1);
      renderWizard();
    };
  const create = $("#create");
  if (create) create.onclick = createGallery;
}

function tabDetails(d) {
  return `
    <div class="brand-pick">
      ${(state.config.brands || [])
        .map(
          (b) => `<button type="button" class="brand-card ${d.brand_id === b.id ? "selected" : ""}" data-brand="${b.id}">
        ${b.logo_web_path ? `<img src="${b.logo_web_path}" alt="">` : ""}
        <strong>${esc(b.display_name)}</strong>
        <div class="muted">${b.has_genuine_logo ? "Genuine logo" : "Placeholder logo"}</div>
      </button>`
        )
        .join("")}
    </div>
    <div class="grid two" style="margin-top:1rem">
      <div><label>Event name</label><input id="event_name" value="${esc(d.event_name)}" required></div>
      <div><label>Event type</label><select id="event_type">${eventTypeOptions(d)}</select></div>
      <div><label>Event date</label><input id="event_date" type="date" value="${esc(d.event_date)}"></div>
      <div><label>Duration</label>
        <select id="duration">
          <option value="full-day" ${d.duration === "full-day" ? "selected" : ""}>Full-day</option>
          <option value="partial-day" ${d.duration === "partial-day" ? "selected" : ""}>Partial-day</option>
        </select>
        <p class="hint">Stored with the gallery for ELP; PicPeak has no native duration field.</p>
      </div>
      <div><label>Client name (optional)</label><input id="client_name" value="${esc(d.client_name)}"></div>
      <div><label>Client email (optional)</label><input id="client_email" type="email" value="${esc(d.client_email)}" placeholder="Leave blank — WhatsApp is enough"></div>
      <div><label>Client phone (optional, for WhatsApp)</label><input id="client_phone" value="${esc(d.client_phone)}" placeholder="+44…"></div>
    </div>`;
}

function eventTypeOptions(d) {
  const brand = brandById(d.brand_id);
  const preferred = new Set(brand?.event_categories || []);
  const types = [
    ["wedding", "Wedding"],
    ["engagement", "Engagement"],
    ["birthday", "Birthday"],
    ["maternity", "Maternity"],
    ["newborn", "Newborn"],
    ["baby-shower", "Baby Shower"],
    ["cultural-event", "Cultural Event"],
    ["corporate", "Corporate"],
    ["other", "Other"],
  ];
  return types
    .map(([id, label]) => {
      const mark = preferred.has(id) || preferred.has(label) ? " ★" : "";
      return `<option value="${id}" ${d.event_type === id ? "selected" : ""}>${label}${mark}</option>`;
    })
    .join("");
}

function tabDesign(d, brand) {
  return `
    <p class="muted">Brand theme: <strong>${esc(brand?.display_name || "")}</strong> · ${esc(brand?.css_template_name || brand?.default_style || "")}</p>
    <div class="grid two">
      <div><label>Layout</label>
        <select id="layout">${(state.config.layouts || [])
          .map((l) => `<option value="${l.id}" ${d.layout === l.id ? "selected" : ""}>${l.label}</option>`)
          .join("")}</select>
      </div>
      <div><label>Colour palette</label>
        <input value="${esc(Object.values(brand?.colours || {}).slice(0, 4).join("  "))}" disabled>
      </div>
    </div>
    <label>Gallery welcome message</label>
    <textarea id="welcome">${esc(d.welcome || brand?.welcome || "")}</textarea>
    <label style="margin-top:0.8rem">Cover photograph / extra media (uploaded after create)</label>
    <input id="media" type="file" multiple accept="${state.config.video.accept}">
    <p class="hint">Photos and videos. MP4 is preferred. Originals are stored; downloads stay original when original-resolution is on. Max photo ${state.config.video.maxPhotoMb} MB, video ${state.config.video.maxVideoMb} MB unless you raised it in PicPeak.</p>
    <label class="row" style="margin-top:0.6rem"><input type="checkbox" id="watermark" ${d.watermark ? "checked" : ""} style="width:auto"> Watermark downloads</label>
  `;
}

function tabAccess(d) {
  return `
    <label>Access</label>
    <select id="access">
      <option value="password" ${d.access === "password" ? "selected" : ""}>Password-protected</option>
      <option value="unlisted" ${d.access === "unlisted" ? "selected" : ""}>Unlisted unique link (no password)</option>
    </select>
    <p class="hint">PicPeak share links are always unique. There is no public directory of client galleries.</p>
    <div class="grid two" style="margin-top:1rem">
      <div><label>Gallery password</label><input id="password" value="${esc(d.password)}"></div>
      <div><label>Expiry (days from event date, optional)</label><input id="expiration_days" type="number" min="0" value="${esc(d.expiration_days)}"></div>
    </div>
    <label class="row"><input type="checkbox" id="allow_downloads" ${d.allow_downloads ? "checked" : ""} style="width:auto"> Allow photo/video downloads</label>
    <label class="row"><input type="checkbox" id="allow_original" ${d.allow_original ? "checked" : ""} style="width:auto"> Original-resolution downloads (no recompression)</label>
  `;
}

function tabGuests(d) {
  return `
    <label class="row"><input type="checkbox" id="feedback_enabled" ${d.feedback_enabled ? "checked" : ""} style="width:auto"> Enable guest feedback</label>
    <label class="row"><input type="checkbox" id="allow_favorites" ${d.allow_favorites ? "checked" : ""} style="width:auto"> Favourites</label>
    <label class="row"><input type="checkbox" id="allow_likes" ${d.allow_likes ? "checked" : ""} style="width:auto"> Likes</label>
    <label class="row"><input type="checkbox" id="allow_comments" ${d.allow_comments ? "checked" : ""} style="width:auto"> Comments</label>
    <label class="row"><input type="checkbox" id="allow_user_uploads" ${d.allow_user_uploads ? "checked" : ""} style="width:auto"> Allow guest photo uploads</label>
    <label class="row"><input type="checkbox" id="publish_now" ${d.publish_now ? "checked" : ""} style="width:auto"> Publish immediately (you can still share later)</label>
    <p class="hint">PicPeak keeps password, expiry, downloads, favourites, comments, guest uploads, and client access. This wizard does not remove those features from Admin.</p>
  `;
}

function tabReview(d, brand) {
  return `
    <dl class="summary">
      <dt>Brand</dt><dd>${esc(brand?.display_name)}</dd>
      <dt>Event</dt><dd>${esc(d.event_name) || "—"} · ${esc(d.event_type)} · ${esc(d.event_date) || "no date"} · ${esc(d.duration)}</dd>
      <dt>Client</dt><dd>${esc(d.client_name) || "No name"} · ${esc(d.client_email) || "no email"} · ${esc(d.client_phone) || "no phone"}</dd>
      <dt>Access</dt><dd>${d.access === "password" ? "Password-protected" : "Unlisted link"} · expiry ${d.expiration_days || "none"} days</dd>
      <dt>Downloads</dt><dd>${d.allow_downloads ? "On" : "Off"} · originals ${d.allow_original ? "on" : "off"} · watermark ${d.watermark ? "on" : "off"}</dd>
    </dl>
    <p class="muted">Email is optional. After create you can copy the link, share on WhatsApp, or send email if you have an address.</p>
  `;
}

function bindWizardFields() {
  main.querySelectorAll("[data-brand]").forEach((btn) => {
    btn.onclick = () => {
      const brand = brandById(btn.dataset.brand);
      saveDraft({ brand_id: brand.id, welcome: brand.welcome });
      renderWizard();
    };
  });
}

function collectWizard() {
  const keys = [
    "event_name",
    "event_type",
    "event_date",
    "duration",
    "client_name",
    "client_email",
    "client_phone",
    "layout",
    "welcome",
    "access",
    "password",
    "expiration_days",
  ];
  const patch = {};
  for (const key of keys) {
    const el = document.getElementById(key);
    if (el) patch[key] = el.value;
  }
  for (const key of [
    "watermark",
    "allow_downloads",
    "allow_original",
    "feedback_enabled",
    "allow_favorites",
    "allow_likes",
    "allow_comments",
    "allow_user_uploads",
    "publish_now",
  ]) {
    const el = document.getElementById(key);
    if (el) patch[key] = el.checked;
  }
  const media = document.getElementById("media");
  if (media?.files?.length) state.queuedFiles = Array.from(media.files);
  saveDraft(patch);
}

function elpWelcome(brandId, welcome, duration) {
  const meta = `<!--elp-brand:${brandId}${duration ? " elp-duration:" + duration : ""}-->`;
  return meta + (welcome ? "\n" + welcome : "");
}

async function createGallery() {
  collectWizard();
  const d = loadDraft();
  const err = $("#wiz-error");
  err.className = "error";
  if (!d.event_name.trim()) {
    err.textContent = "Event name is required.";
    return;
  }
  if (d.access === "password" && String(d.password || "").length < 6) {
    err.textContent = "Password must be at least 6 characters, or choose Unlisted link.";
    return;
  }
  const brand = brandById(d.brand_id);
  const payload = {
    event_type: d.event_type || "other",
    event_name: d.event_name.trim(),
    require_password: d.access === "password",
    allow_downloads: !!d.allow_downloads,
    allow_favorites: !!d.allow_favorites,
    allow_likes: !!d.allow_likes,
    allow_comments: !!d.allow_comments,
    feedback_enabled: !!d.feedback_enabled,
    watermark_downloads: !!d.watermark,
    allow_user_uploads: !!d.allow_user_uploads,
    header_style: "hero",
    hero_logo_visible: true,
    layout: d.layout,
    welcome_message: elpWelcome(brand.id, d.welcome, d.duration),
  };
  if (d.event_date) payload.event_date = d.event_date;
  if (d.client_name) payload.customer_name = d.client_name;
  if (d.client_email) payload.customer_email = d.client_email;
  if (d.client_phone) payload.customer_phone = d.client_phone.slice(0, 32);
  if (state.config.adminEmailDefault) payload.admin_email = state.config.adminEmailDefault;
  if (d.access === "password") payload.password = d.password;
  if (Number(d.expiration_days) > 0) payload.expiration_days = Number(d.expiration_days);
  const cssId = state.cssByStyle[brand.default_style];
  if (cssId) payload.css_template_id = cssId;
  try {
    err.textContent = "Creating…";
    const created = await api("/api/admin/events", { method: "POST", json: payload });
    if (!created.id) throw new Error(JSON.stringify(created));
    if (brand.logo_web_path) {
      try {
        const logoResp = await fetch(brand.logo_web_path);
        const blob = await logoResp.blob();
        const fd = new FormData();
        fd.append("logo", blob, brand.logo_filename || "logo.jpg");
        await api(`/api/admin/events/${created.id}/logo`, { method: "POST", body: fd });
      } catch (logoErr) {
        console.warn("logo upload", logoErr);
      }
    }
    if (d.publish_now) {
      await api(`/api/admin/events/${created.id}/publish`, {
        method: "POST",
        json: { password: d.password || undefined, notify_customer: false },
      });
      created.is_draft = false;
    }
    state.created = created;
    state.view = "event";
    localStorage.removeItem(DRAFT_KEY);
    await loadEvents();
    render();
    if (state.queuedFiles?.length) uploadQueued(created.id, state.queuedFiles);
  } catch (e) {
    err.textContent = e.message;
  }
}

function renderEvent() {
  const ev = state.created || {};
  const brand = brandById(inferBrand(ev) || loadDraft().brand_id);
  const link = shareLink(ev);
  const msg = shareText(brand, link);
  main.innerHTML = `
    <div class="card">
      <p class="eyebrow">${esc(brand?.display_name || "Gallery")}</p>
      <h2 style="margin:0 0 0.4rem">${esc(ev.event_name || "Untitled")}</h2>
      <p class="muted">${ev.is_draft ? "Draft — guests cannot open the link until you publish." : "Published"} · id ${ev.id}</p>
      <p><code id="share-link">${esc(link || "(missing share token — open in PicPeak Admin)")}</code></p>
      <div class="row">
        <button class="btn primary" id="copy">Copy gallery link</button>
        <a class="btn accent" id="wa" target="_blank" rel="noopener">Share via WhatsApp</a>
        <a class="btn" id="mail">Send via Email</a>
        ${link ? `<a class="btn" target="_blank" rel="noopener" href="${esc(link)}">Preview client gallery</a>` : ""}
        <a class="btn ghost" target="_blank" rel="noopener" href="${state.config.picpeakPublicOrigin}/admin">Open in PicPeak Admin</a>
      </div>
      <p class="success" id="copied"></p>
      <hr style="border:0;border-top:1px solid var(--line);margin:1.2rem 0">
      <h3>Upload photos &amp; videos</h3>
      <input id="more" type="file" multiple accept="${state.config.video.accept}">
      <div class="progress" style="margin:0.6rem 0"><span id="bar"></span></div>
      <p class="muted" id="up-status">MP4 preferred. MOV may play only in Safari unless you enable browser-playable copies (beta PicPeak). Downloads stay original when original-resolution is on.</p>
      <p class="error" id="up-error"></p>
      <div id="media-list"></div>
    </div>`;
  $("#copy").onclick = async () => {
    if (!link) return;
    await navigator.clipboard.writeText(link);
    $("#copied").textContent = "Link copied.";
  };
  $("#wa").href = waUrl(msg, ev.customer_phone);
  const subject = (brand?.email_subject || "Your {brand} gallery is ready").replace("{brand}", brand?.display_name || "");
  $("#mail").href = `mailto:${encodeURIComponent(ev.customer_email || "")}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(msg)}`;
  $("#more").onchange = () => uploadQueued(ev.id, Array.from($("#more").files || []));
  loadMedia(ev.id);
}

async function loadMedia(eventId) {
  const box = $("#media-list");
  if (!box) return;
  try {
    const data = await api(`/api/admin/photos/${eventId}/photos`);
    const photos = data.photos || data || [];
    const vids = photos.filter((p) => /mp4|mov|webm|m4v|video/i.test(`${p.filename || ""} ${p.mime_type || p.type || ""}`));
    box.innerHTML = `<p>${photos.length} files · ${vids.length} videos · ${photos.length - vids.length} photos</p>
      <div class="row">${["all", "photos", "videos"]
        .map((f) => `<button class="btn" data-filter="${f}">${f}</button>`)
        .join("")}</div>
      <div id="tiles" class="grid two" style="margin-top:0.6rem"></div>`;
    const paint = (filter) => {
      $("#tiles").innerHTML = photos
        .filter((p) => {
          const video = /mp4|mov|webm|m4v|video/i.test(`${p.filename || ""} ${p.mime_type || p.type || ""}`);
          if (filter === "photos") return !video;
          if (filter === "videos") return video;
          return true;
        })
        .slice(0, 24)
        .map((p) => `<div class="card" style="padding:0.5rem">${esc(p.filename || p.id)}</div>`)
        .join("");
    };
    paint("all");
    box.querySelectorAll("[data-filter]").forEach((btn) => (btn.onclick = () => paint(btn.dataset.filter)));
  } catch (e) {
    box.textContent = "Media list unavailable until files are uploaded.";
  }
}

function uploadQueued(eventId, files) {
  const list = files || [];
  const bar = $("#bar");
  const status = $("#up-status");
  const err = $("#up-error");
  if (err) err.textContent = "";
  let done = 0;
  const run = async () => {
    for (const file of list) {
      try {
        if (status) status.textContent = `Uploading ${file.name} (${formatBytes(file.size)})…`;
        if (file.size > 40 * 1024 * 1024) await chunkedUpload(eventId, file, bar);
        else await simpleUpload(eventId, file, bar);
        done += 1;
      } catch (e) {
        if (err) err.textContent = `${file.name}: ${e.message}`;
        else alert(e.message);
      }
    }
    if (status) status.textContent = `Uploaded ${done} of ${list.length} file(s).`;
    loadMedia(eventId);
  };
  run();
}

function simpleUpload(eventId, file, bar) {
  return new Promise((resolve, reject) => {
    const fd = new FormData();
    fd.append("photos", file, file.name);
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `/pp/api/admin/events/${eventId}/upload`);
    xhr.withCredentials = true;
    if (state.token) xhr.setRequestHeader("Authorization", "Bearer " + state.token);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && bar) bar.style.width = Math.round((e.loaded / e.total) * 100) + "%";
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve(JSON.parse(xhr.responseText || "{}"));
      else reject(new Error(xhr.responseText || `HTTP ${xhr.status}`));
    };
    xhr.onerror = () => reject(new Error("Network error during upload"));
    xhr.send(fd);
  });
}

async function chunkedUpload(eventId, file, bar) {
  const chunkSize = 10 * 1024 * 1024;
  const totalChunks = Math.ceil(file.size / chunkSize);
  const init = await api(`/api/admin/photos/${eventId}/chunked-upload/init`, {
    method: "POST",
    json: { filename: file.name, fileSize: file.size, totalChunks },
  });
  const uploadId = init.uploadId;
  const size = init.chunkSize || chunkSize;
  const chunks = Math.ceil(file.size / size);
  for (let i = 0; i < chunks; i++) {
    const blob = file.slice(i * size, Math.min(file.size, (i + 1) * size));
    const chunkHeaders = { "Content-Type": "application/octet-stream" };
    if (state.token) chunkHeaders.Authorization = "Bearer " + state.token;
    const res = await fetch(`/pp/api/admin/photos/${eventId}/chunked-upload/${uploadId}/chunk/${i}`, {
      method: "POST",
      credentials: "include",
      headers: chunkHeaders,
      body: blob,
    });
    if (!res.ok) throw new Error(`Chunk ${i} failed: ${await res.text()}`);
    if (bar) bar.style.width = Math.round(((i + 1) / chunks) * 100) + "%";
  }
  return api(`/api/admin/photos/${eventId}/chunked-upload/${uploadId}/complete`, {
    method: "POST",
    json: { category_id: null, detect_duplicates: true },
  });
}

async function loadStorageReport() {
  const headers = {};
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const res = await fetch("/elp/storage-report", { headers, credentials: "include" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  state.storageReport = data;
  return data;
}

function renderStorage() {
  const cfg = state.config?.storage || {};
  const report = state.storageReport;
  if (!report && !state.storageLoading && !state.storageError) {
    state.storageLoading = true;
    loadStorageReport()
      .catch((err) => {
        state.storageError = err.message;
      })
      .finally(() => {
        state.storageLoading = false;
        if (state.view === "storage") renderStorage();
      });
  }
  if (!report) {
    main.innerHTML = `<div class="card"><h2>Storage &amp; cost monitoring</h2>
      <p class="${state.storageError ? "error" : "muted"}">${
        state.storageError || "Reading PicPeak storage/info (no files are deleted)…"
      }</p>
      ${state.storageError ? `<p><button class="btn" id="retry-storage">Try again</button></p>` : ""}
    </div>`;
    const retry = $("#retry-storage");
    if (retry)
      retry.onclick = () => {
        state.storageError = "";
        renderStorage();
      };
    return;
  }
  const usage = report.usage || {};
  const alert = report.alert || {};
  const rem = report.remaining || {};
  const bak = report.backup || {};
  const percent = usage.percent_used;
  const meter = Math.max(0, Math.min(100, Number(percent) || 0));
  main.innerHTML = `
    <div class="alert-banner ${esc(alert.level || "")}">
      <strong>${esc(alert.title || "Storage")}</strong>
      <p>${esc(alert.advice || "")}</p>
    </div>
    <div class="grid two" style="margin-top:1rem">
      <div class="card">
        <p class="eyebrow">Docker / PicPeak disk</p>
        <h2 style="margin:0">${formatBytes(usage.total_used)} used</h2>
        <div class="meter"><span class="${esc(alert.level || "ok")}" style="width:${meter}%"></span></div>
        <p class="muted">${formatBytes(usage.disk_available)} free of ${formatBytes(usage.disk_total)} reported · ${
          percent != null ? percent + "%" : "n/a"
        }</p>
        <p class="hint">${esc(report.capacity_note || "")}</p>
        <p class="hint">Volume <code>${esc(report.volume_name)}</code>. Measurement: ${esc(
          usage.storage_measurement || "PicPeak GET /api/admin/settings/storage/info"
        )}. Host check: <code>scripts/verify-storage.ps1</code>.</p>
      </div>
      <div class="card">
        <p class="eyebrow">Remaining at recent upload rate</p>
        <h2 style="margin:0">${
          rem.days_remaining != null ? rem.days_remaining + " days" : rem.status === "idle" ? "Idle" : "Unknown"
        }</h2>
        <p class="muted">${esc(rem.note || "")}</p>
        <p class="hint">Lookback ${report.lookback_days || 14} days · ${formatBytes(
          report.recent_upload_bytes
        )} uploaded · ${report.recent_upload_files || 0} files · confidence ${esc(rem.confidence || "none")}</p>
      </div>
    </div>
    ${renderBreakdown(usage.storage_breakdown)}
    <div class="card" style="margin-top:1rem">
      <div class="row" style="justify-content:space-between">
        <div>
          <p class="eyebrow">Per-event usage</p>
          <h3 style="margin:0.2rem 0 0">Photos vs videos</h3>
        </div>
        <button class="btn" id="refresh-storage">Refresh</button>
      </div>
      <p class="hint">Photo/video split uses each event’s media list. PicPeak storage_by_event is catalogued original bytes (top events) and is not a disk walk.</p>
      <div style="overflow:auto;margin-top:0.6rem">
        <table class="table">
          <thead><tr><th>Gallery</th><th>Photos</th><th>Videos</th><th>Total</th><th></th></tr></thead>
          <tbody>
            ${
              (report.events || [])
                .map(
                  (ev) => `<tr>
                    <td><strong>${esc(ev.event_name)}</strong><br><span class="badge ${esc(ev.status)}">${esc(
                      ev.status
                    )}</span></td>
                    <td>${ev.has_media_split ? `${ev.photo_count} · ${formatBytes(ev.photo_bytes)}` : "—"}</td>
                    <td>${ev.has_media_split ? `${ev.video_count} · ${formatBytes(ev.video_bytes)}` : "—"}</td>
                    <td>${formatBytes(ev.total_bytes)}</td>
                    <td>${ev.id ? `<button class="btn" data-open="${ev.id}">Open</button>` : ""}</td>
                  </tr>`
                )
                .join("") || `<tr><td colspan="5" class="muted">No events returned.</td></tr>`
            }
          </tbody>
        </table>
      </div>
    </div>
    ${renderArchivePolicy(report, cfg)}
    ${renderBackupCard(report, bak, cfg)}
    ${renderCostCard(report)}
    ${renderLimitsCard(report)}
  `;
  const refresh = $("#refresh-storage");
  if (refresh)
    refresh.onclick = async () => {
      state.storageReport = null;
      state.storageError = "";
      renderStorage();
    };
  main.querySelectorAll("[data-open]").forEach((btn) => {
    btn.onclick = () => openEvent(Number(btn.dataset.open));
  });
  bindArchiveConfirm(report);
  bindRestoreChecks();
}

function renderBreakdown(breakdown) {
  if (!breakdown || typeof breakdown !== "object") return "";
  const rows = Object.entries(breakdown)
    .map(([k, v]) => `<tr><td>${esc(k)}</td><td>${formatBytes(v)}</td></tr>`)
    .join("");
  if (!rows) return "";
  return `<div class="card" style="margin-top:1rem"><p class="eyebrow">On-disk breakdown</p>
    <table class="table"><tbody>${rows}</tbody></table>
    <p class="hint">From PicPeak’s storage walk (thumbnails, archives, caches). Not a second copy of your photos.</p></div>`;
}

function renderArchivePolicy(report, cfg) {
  const policy = report.archive_policy || cfg.archivePolicy || {};
  const steps = policy.steps || [];
  const never = policy.never || [];
  return `<div class="card" style="margin-top:1rem">
    <p class="eyebrow">Archive &amp; deletion</p>
    <h3 style="margin:0.2rem 0 0.6rem">PicPeak native — this console never deletes</h3>
    <ul>${steps.map((s) => `<li>${esc(s)}</li>`).join("")}</ul>
    <p class="muted">Never: ${never.map((s) => esc(s)).join(" · ")}</p>
    <label>Type the exact gallery name to unlock the PicPeak Admin archive link</label>
    <select id="archive-event">${(report.events || [])
      .map((ev) => `<option value="${esc(ev.event_name)}">${esc(ev.event_name)}</option>`)
      .join("")}</select>
    <input id="archive-confirm" placeholder="Type the gallery name" autocomplete="off" />
    <p class="error" id="archive-hint">Name must match exactly. No archive or delete request is sent from here.</p>
    <div class="row">
      <a class="btn" id="open-archives" target="_blank" rel="noopener" href="${esc(
        cfg.adminArchives || "#"
      )}">Open PicPeak Archives</a>
      <a class="btn danger" id="open-archive-event" aria-disabled="true">Archive in PicPeak Admin…</a>
    </div>
  </div>`;
}

function bindArchiveConfirm(report) {
  const select = $("#archive-event");
  const input = $("#archive-confirm");
  const link = $("#open-archive-event");
  const hint = $("#archive-hint");
  if (!select || !input || !link) return;
  const origin = state.config?.picpeakPublicOrigin || "";
  const sync = () => {
    const name = select.value;
    const ok = input.value.trim() === name && name.length > 0;
    link.setAttribute("aria-disabled", ok ? "false" : "true");
    if (ok) {
      link.href = `${origin}/admin`;
      hint.textContent = "Opens PicPeak Admin. Use Archive Gallery there (zip, then active originals are removed). Restore stays on Archives. This console still has not deleted anything.";
      hint.className = "success";
    } else {
      link.removeAttribute("href");
      hint.textContent = "Name must match exactly. No archive or delete request is sent from here.";
      hint.className = "error";
    }
  };
  select.onchange = sync;
  input.oninput = sync;
  link.onclick = (e) => {
    if (link.getAttribute("aria-disabled") === "true") e.preventDefault();
  };
}

function renderBackupCard(report, bak, cfg) {
  const policy = report.backup_policy || cfg.backupPolicy || {};
  const checks = policy.restore_test || [];
  const enabled = bak.enabled === true;
  return `<div class="card" style="margin-top:1rem">
    <p class="eyebrow">Backup status</p>
    <h3 style="margin:0.2rem 0 0.4rem">${enabled ? "PicPeak built-in backup is on" : "PicPeak built-in backup is off (default)"}</h3>
    <p class="muted">Destination: ${esc(bak.destination_type || "none")} · last run: ${esc(
      bak.last_run || "never"
    )} · next: ${esc(bak.next_run || "not scheduled")}</p>
    <p class="hint">${esc(bak.note || policy.independent || "")} aio writes local backups under ${esc(
      policy.aio_local_path || "/data/backup"
    )} — that is the same volume, not an off-site copy. This page does not enable S3, rsync, or email.</p>
    <p><a class="btn" target="_blank" rel="noopener" href="${esc(cfg.adminBackup || "#")}">Open PicPeak Backup &amp; Restore</a></p>
    <p class="eyebrow" style="margin-top:1rem">Restore testing checklist (saved only in this browser)</p>
    <ul class="check-list" id="restore-checks">
      ${checks
        .map(
          (item, i) =>
            `<li><label class="row"><input type="checkbox" data-restore="${i}" style="width:auto"> ${esc(item)}</label></li>`
        )
        .join("")}
    </ul>
  </div>`;
}

function bindRestoreChecks() {
  const key = "elp-restore-checklist";
  let saved = [];
  try {
    saved = JSON.parse(localStorage.getItem(key) || "[]");
  } catch {
    saved = [];
  }
  main.querySelectorAll("[data-restore]").forEach((box) => {
    box.checked = !!saved[Number(box.dataset.restore)];
    box.onchange = () => {
      const next = [...saved];
      next[Number(box.dataset.restore)] = box.checked;
      localStorage.setItem(key, JSON.stringify(next));
      saved = next;
    };
  });
}

function renderCostCard(report) {
  const cats = report.cost_categories || [];
  return `<div class="card" style="margin-top:1rem">
    <p class="eyebrow">Costs</p>
    <h3 style="margin:0.2rem 0 0.6rem">Software vs hosting vs backup vs optional extras</h3>
    <p class="hint">Nothing here is a paid commitment. Optional services stay off until you choose them outside this repo.</p>
    <table class="table">
      <thead><tr><th>Category</th><th>Committed?</th><th></th></tr></thead>
      <tbody>
        ${cats
          .map(
            (c) =>
              `<tr><td><strong>${esc(c.label)}</strong></td><td>${
                c.committed ? "Yes" : "No"
              }</td><td>${esc(c.summary)}</td></tr>`
          )
          .join("")}
      </tbody>
    </table>
  </div>`;
}

function renderLimitsCard(report) {
  const live = report.limits_live || {};
  const limits = report.technical_limits || [];
  return `<div class="card" style="margin-top:1rem">
    <p class="eyebrow">Technical limits</p>
    <h3 style="margin:0.2rem 0 0.6rem">Uploads, video, and this server</h3>
    <p class="muted">Live PicPeak caps: photos ${esc(live.max_photo_mb)} MB · videos ${esc(
      live.max_video_mb
    )} MB · types ${esc(live.allowed_file_types || "see Admin")}</p>
    <table class="table">
      <thead><tr><th>Limit</th><th>What PicPeak / Docker actually does</th></tr></thead>
      <tbody>
        ${limits.map((item) => `<tr><td>${esc(item.label)}</td><td>${esc(item.value)}<br><span class="muted">${esc(item.source)}</span></td></tr>`).join("")}
      </tbody>
    </table>
  </div>`;
}

function formatBytes(n) {
  if (n == null || Number.isNaN(Number(n))) return "—";
  const u = ["B", "KB", "MB", "GB", "TB"];
  let v = Number(n);
  let i = 0;
  while (v >= 1024 && i < u.length - 1) {
    v /= 1024;
    i += 1;
  }
  return `${v.toFixed(v >= 10 || i === 0 ? 0 : 1)} ${u[i]}`;
}

function esc(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function start() {
  state.config = await (await fetch("/config.json")).json();
  if (state.signedIn || state.token) {
    try {
      const session = await api("/api/auth/session");
      if (session.valid === false) throw new Error(session.error || "session");
      markSignedIn(state.token);
      await bootstrap();
      await loadEvents();
      state.view = "dashboard";
    } catch {
      clearLocalSession();
      state.view = "login";
    }
  }
  render();
}

start();
