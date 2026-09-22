
const CONDITION_LABELS = {
  needs_attic: "нужен чердак",
  fears_mirrors: "боится зеркал",
  no_humans_nearby: "нельзя рядом с людьми",
  likes_dampness: "любит сырость",
  needs_silence: "нужна тишина",
  needs_darkness: "боится яркого света",
  dislikes_crowds: "не любит тесноту",
};
const LIGHTING_LABELS = { dark: "тёмное", dim: "приглушённое", bright: "яркое" };
const HUMIDITY_LABELS = { dry: "сухо", normal: "нормально", damp: "сыро" };

const state = {
  ghosts: [],
  locations: [],
  matchResults: [],
};

function showError(message) {
  const banner = document.getElementById("error-banner");
  banner.textContent = message;
  banner.classList.remove("hidden");
  clearTimeout(showError._t);
  showError._t = setTimeout(() => banner.classList.add("hidden"), 7000);
}

async function guarded(fn) {
  try {
    return await fn();
  } catch (err) {
    if (err instanceof Api.ApiError) {
      showError(err.message);
    } else {
      showError("Неожиданная ошибка в приложении. Попробуйте обновить страницу.");
      console.error(err);
    }
    return null;
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

document.getElementById("tabs").addEventListener("click", (e) => {
  const btn = e.target.closest(".tab-btn");
  if (!btn) return;
  document.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("active", b === btn));
  const tab = btn.dataset.tab;
  document.querySelectorAll(".tab-panel").forEach((p) => p.classList.toggle("active", p.id === `tab-${tab}`));
  if (tab === "matching") guarded(loadMatchStatus);
  if (tab === "report") guarded(loadReport);
});

async function loadGhosts() {
  state.ghosts = (await Api.getGhosts()) || [];
  renderGhosts();
}

function renderGhosts() {
  const list = document.getElementById("ghosts-list");
  const empty = document.getElementById("ghosts-empty");
  if (state.ghosts.length === 0) {
    list.innerHTML = "";
    empty.classList.remove("hidden");
    return;
  }
  empty.classList.add("hidden");
  list.innerHTML = state.ghosts
    .map((g) => {
      const tags = (g.special_conditions || [])
        .map((c) => `<span class="tag">${escapeHtml(CONDITION_LABELS[c] || c)}</span>`)
        .join("");
      const overdue = new Date(g.relocation_deadline) < new Date(new Date().toDateString());
      return `
      <div class="card entity-card" data-id="${g.id}">
        <div class="main">
          <h4>${escapeHtml(g.name)}</h4>
          <div class="meta">
            Тревожность: ${g.anxiety_level}/10 · Любимая температура: ${g.favorite_temperature}°C ·
            Дедлайн: ${escapeHtml(g.relocation_deadline)}
            ${overdue ? '<span class="tag danger">дедлайн просрочен</span>' : ""}
          </div>
          <div>${tags || '<span class="meta">без особых условий</span>'}</div>
        </div>
        <button class="btn danger small" data-action="delete-ghost" data-id="${g.id}">Удалить</button>
      </div>`;
    })
    .join("");
}

document.getElementById("open-ghost-form").addEventListener("click", () => {
  document.getElementById("ghost-form").classList.remove("hidden");
});
document.getElementById("cancel-ghost-form").addEventListener("click", () => {
  document.getElementById("ghost-form").reset();
  document.getElementById("ghost-form").classList.add("hidden");
});
document.getElementById("ghost-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const fd = new FormData(form);
  const payload = {
    name: fd.get("name"),
    anxiety_level: Number(fd.get("anxiety_level")),
    favorite_temperature: Number(fd.get("favorite_temperature")),
    relocation_deadline: fd.get("relocation_deadline"),
    special_conditions: fd.getAll("special_conditions"),
  };
  const result = await guarded(() => Api.createGhost(payload));
  if (result) {
    form.reset();
    form.classList.add("hidden");
    await guarded(loadGhosts);
  }
});

document.getElementById("ghosts-list").addEventListener("click", async (e) => {
  const btn = e.target.closest('[data-action="delete-ghost"]');
  if (!btn) return;
  if (!confirm("Удалить эту заявку?")) return;
  await guarded(() => Api.deleteGhost(btn.dataset.id));
  await guarded(loadGhosts);
});

async function loadLocations() {
  state.locations = (await Api.getLocations()) || [];
  renderLocations();
}

function renderLocations() {
  const list = document.getElementById("locations-list");
  const empty = document.getElementById("locations-empty");
  if (state.locations.length === 0) {
    list.innerHTML = "";
    empty.classList.remove("hidden");
    return;
  }
  empty.classList.add("hidden");
  list.innerHTML = state.locations
    .map((l) => {
      const full = l.occupied >= l.capacity;
      return `
      <div class="card entity-card" data-id="${l.id}">
        <div class="main">
          <h4>${escapeHtml(l.name)} <span class="meta">(${escapeHtml(l.location_type)})</span></h4>
          <div class="meta">
            Вместимость: ${l.occupied}/${l.capacity} ${full ? '<span class="tag danger">переполнено</span>' : ""} ·
            Температура: ${l.ambient_temperature}°C · Шум: ${l.noise_level}/10
          </div>
          <div>
            <span class="tag">${LIGHTING_LABELS[l.lighting] || l.lighting}</span>
            <span class="tag">${HUMIDITY_LABELS[l.humidity] || l.humidity}</span>
            ${l.has_people ? '<span class="tag warn">бывают люди</span>' : '<span class="tag ok">без людей</span>'}
            ${l.has_mirrors ? '<span class="tag">есть зеркала</span>' : ""}
            ${l.has_attic ? '<span class="tag">есть чердак</span>' : ""}
          </div>
        </div>
        <button class="btn danger small" data-action="delete-location" data-id="${l.id}">Удалить</button>
      </div>`;
    })
    .join("");
}

document.getElementById("open-location-form").addEventListener("click", () => {
  document.getElementById("location-form").classList.remove("hidden");
});
document.getElementById("cancel-location-form").addEventListener("click", () => {
  document.getElementById("location-form").reset();
  document.getElementById("location-form").classList.add("hidden");
});
document.getElementById("location-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const fd = new FormData(form);
  const payload = {
    name: fd.get("name"),
    location_type: fd.get("location_type"),
    capacity: Number(fd.get("capacity")),
    occupied: Number(fd.get("occupied")),
    lighting: fd.get("lighting"),
    noise_level: Number(fd.get("noise_level")),
    humidity: fd.get("humidity"),
    ambient_temperature: Number(fd.get("ambient_temperature")),
    has_people: fd.get("has_people") === "on",
    has_mirrors: fd.get("has_mirrors") === "on",
    has_attic: fd.get("has_attic") === "on",
    restrictions: [],
  };
  const result = await guarded(() => Api.createLocation(payload));
  if (result) {
    form.reset();
    form.classList.add("hidden");
    await guarded(loadLocations);
  }
});

document.getElementById("locations-list").addEventListener("click", async (e) => {
  const btn = e.target.closest('[data-action="delete-location"]');
  if (!btn) return;
  if (!confirm("Удалить это место? Связанные назначения тоже будут сняты.")) return;
  await guarded(() => Api.deleteLocation(btn.dataset.id));
  await guarded(loadLocations);
});

async function loadMatchStatus() {
  const results = await Api.getMatchStatus();
  state.matchResults = results || [];
  console.log("GET /api/match ->", state.matchResults);
  safeRenderMatching();
}

document.getElementById("run-matching").addEventListener("click", async () => {
  const results = await guarded(() => Api.runMatching());
  console.log("POST /api/match/run ->", results);
  if (results) {
    state.matchResults = results;
    safeRenderMatching();
  }
});

// renderMatching() раньше вызывался напрямую — если внутри .map() при сборке
// разметки одной карточки происходила ошибка (например, обращение к полю
// несуществующего объекта), она обрывала всю функцию ДО присвоения
// list.innerHTML, и на экране просто оставалось то, что было раньше — без
// какой-либо видимой ошибки, только молчаливый "как будто ничего не
// произошло". safeRenderMatching() ловит это и показывает баннер с ошибкой,
// а не оставляет старую картинку молча висеть на экране.
function safeRenderMatching() {
  try {
    renderMatching();
  } catch (err) {
    console.error("renderMatching() упал:", err);
    showError("Не получилось отрисовать вкладку «Подбор» — ошибка в браузере, см. консоль (F12).");
  }
}

function locationOptionsHtml(selectedId) {
  return state.locations
    .map(
      (l) =>
        `<option value="${l.id}" ${String(l.id) === String(selectedId) ? "selected" : ""}>
          ${escapeHtml(l.name)} (${l.occupied}/${l.capacity})
        </option>`
    )
    .join("");
}

function renderMatching() {
  const list = document.getElementById("matching-results");
  const empty = document.getElementById("matching-empty");
  const existingDebug = document.getElementById("matching-debug");

  if (state.ghosts.length === 0 || state.locations.length === 0) {
    list.innerHTML = "";
    empty.classList.remove("hidden");
    if (existingDebug) existingDebug.remove();
    return;
  }
  empty.classList.add("hidden");

  if (state.matchResults.length === 0) {
    list.innerHTML = `<p class="hint">Загрузка предложений…</p>`;
    if (existingDebug) existingDebug.remove();
    return;
  }

  list.innerHTML = state.matchResults
    .map((r) => renderMatchCard(r))
    .join("");

  renderMatchDebugPanel();
}

// Собирает разметку одной карточки. Вынесено из renderMatching() отдельной
// функцией и написано защищённо (не берёт поля напрямую без проверки), чтобы
// один "кривой" объект в ответе сервера не ломал всю отрисовку вкладки молча —
// раньше именно так и было: r.assignment мог оказаться null там, где фронт
// этого не ожидал, .map() падал с исключением ДО того, как list.innerHTML
// вообще успевал обновиться, и внешне это выглядело как "нажал — ничего не
// изменилось", хотя сервер на самом деле уже всё сохранил.
function renderMatchCard(r) {
  if (r.status === "matched") {
    const a = r.assignment || {};
    const isAssigned = r.assigned === true;
    const isManual = a.manual === true;
    const score = typeof a.score === "number" ? a.score : 0;
    const scoreClass = score < 50 ? "low" : "";
    const statusTag = isAssigned
      ? '<span class="tag status-assigned">✓ Назначено</span>'
      : '<span class="tag status-suggested">◌ Предложено — пока не сохранено</span>';
    const autoManualTag = isAssigned
      ? isManual
        ? '<span class="tag warn">✋ Ручной выбор</span>'
        : '<span class="tag ok">⚙ Назначено автоматически</span>'
      : "";
    const warnings = (a.warnings || []).length
      ? `<div class="warning-box">⚠ ${a.warnings.map(escapeHtml).join("; ")}</div>`
      : "";
    const unassignBtn = isAssigned
      ? `<button class="btn ghost small" data-action="unassign" data-ghost-id="${r.ghost_id}">Снять назначение</button>`
      : "";
    const quickAssignBtn = isAssigned
      ? ""
      : `<button class="btn small primary" data-action="quick-assign" data-ghost-id="${r.ghost_id}" data-location-id="${a.location_id}">Назначить</button>`;
    const explanation = Array.isArray(a.explanation) ? a.explanation : [];
    return `
    <div class="card match-card ${isAssigned ? "matched" : "suggested"}" data-ghost-id="${r.ghost_id}" data-assigned="${isAssigned}" data-manual="${isManual}">
      <div class="entity-card">
        <div class="main">
          <div class="match-title-row">
            <h4>${escapeHtml(r.ghost_name)} → ${escapeHtml(a.location_name || "?")}${
              isAssigned ? "" : ' <span class="hint-inline">— лучшее авто-предложение</span>'
            }</h4>
            ${quickAssignBtn}
          </div>
          <div class="tags-row">${statusTag} ${autoManualTag}</div>
          <ul class="explanation">${explanation.map((x) => `<li>${escapeHtml(x)}</li>`).join("")}</ul>
          ${warnings}
        </div>
        <div class="score-badge ${scoreClass}">${score}/100</div>
      </div>
      <div class="select-row">
        <select data-role="override-select">${locationOptionsHtml(a.location_id)}</select>
        <button class="btn small" data-action="manual-assign" data-ghost-id="${r.ghost_id}">Выбрать вручную</button>
        ${unassignBtn}
      </div>
      <div class="manual-feedback"></div>
    </div>`;
  }

  const rejected = (r.rejected_locations || [])
    .map((rl) => `<li><strong>${escapeHtml(rl.location_name)}:</strong> ${(rl.reasons || []).map(escapeHtml).join(", ")}</li>`)
    .join("");
  return `
  <div class="card match-card impossible" data-ghost-id="${r.ghost_id}">
    <div class="main">
      <div class="match-title-row">
        <h4>${escapeHtml(r.ghost_name)} → переселение невозможно</h4>
      </div>
      <div class="tags-row"><span class="tag danger">✕ Автоматически не получилось</span></div>
      <p class="reasons">Причина: ${escapeHtml(r.impossible_reason || "нет подходящих мест")}</p>
      ${rejected ? `<ul class="reasons">${rejected}</ul>` : ""}
    </div>
    <div class="select-row">
      <select data-role="override-select">${locationOptionsHtml("")}</select>
      <button class="btn small" data-action="manual-assign" data-ghost-id="${r.ghost_id}">Назначить вручную</button>
    </div>
    <div class="manual-feedback"></div>
  </div>`;
}

// Отладочная панель под списком карточек: сырой JSON последнего ответа
// GET/POST /api/match, как его прислал сервер, без какой-либо обработки
// фронтендом. Добавлено, чтобы можно было своими глазами свериться —
// действительно ли сервер прислал правильные значения assigned/manual,
// не открывая вкладку Network в браузере. Свёрнуто по умолчанию (<details>).
function renderMatchDebugPanel() {
  const existing = document.getElementById("matching-debug");
  if (existing) existing.remove();

  const wrap = document.createElement("details");
  wrap.id = "matching-debug";
  wrap.style.marginTop = "16px";
  wrap.style.fontSize = "0.8rem";
  wrap.style.color = "var(--text-dim)";

  const summary = document.createElement("summary");
  summary.textContent = "Отладка: сырой ответ сервера (что реально пришло из /api/match)";
  summary.style.cursor = "pointer";
  wrap.appendChild(summary);

  const pre = document.createElement("pre");
  pre.style.whiteSpace = "pre-wrap";
  pre.style.wordBreak = "break-word";
  pre.style.background = "var(--bg-panel)";
  pre.style.border = "1px solid var(--border)";
  pre.style.borderRadius = "8px";
  pre.style.padding = "10px";
  pre.style.marginTop = "8px";
  pre.textContent = JSON.stringify(state.matchResults, null, 2);
  wrap.appendChild(pre);

  document.getElementById("matching-results").after(wrap);
}

document.getElementById("matching-results").addEventListener("click", async (e) => {
  const unassignBtn = e.target.closest('[data-action="unassign"]');
  if (unassignBtn) {
    await guarded(() => Api.unassign(unassignBtn.dataset.ghostId));
    await guarded(loadMatchStatus);
    return;
  }

  const quickAssignBtn = e.target.closest('[data-action="quick-assign"]');
  if (quickAssignBtn) {
    const card = quickAssignBtn.closest(".match-card");
    const feedback = card.querySelector(".manual-feedback");
    const ghostId = Number(quickAssignBtn.dataset.ghostId);
    const locationId = Number(quickAssignBtn.dataset.locationId);
    await tryManualAssign(ghostId, locationId, false, feedback);
    return;
  }

  const assignBtn = e.target.closest('[data-action="manual-assign"]');
  if (!assignBtn) return;
  const card = assignBtn.closest(".match-card");
  const select = card.querySelector('[data-role="override-select"]');
  const feedback = card.querySelector(".manual-feedback");
  const ghostId = Number(assignBtn.dataset.ghostId);
  const locationId = Number(select.value);
  if (!locationId) {
    feedback.innerHTML = `<div class="conflict-box">Выберите место из списка.</div>`;
    return;
  }
  await tryManualAssign(ghostId, locationId, false, feedback);
});

async function tryManualAssign(ghostId, locationId, force, feedback) {
  const result = await guarded(() => Api.manualAssign({ ghost_id: ghostId, location_id: locationId, force }));
  if (!result) return;

  if (result.status === "assigned") {
    feedback.innerHTML = "";
    await guarded(loadMatchStatus);
    return;
  }
  if (result.status === "blocked") {
    feedback.innerHTML = `<div class="conflict-box">🚫 Этот выбор невозможен: ${result.hard_conflicts
      .map(escapeHtml)
      .join("; ")}</div>`;
    return;
  }
  if (result.status === "needs_confirmation") {
    feedback.innerHTML = `
      <div class="warning-box">
        ⚠ ${result.warnings.map(escapeHtml).join("; ")}
        <div style="margin-top:8px;">
          <button class="btn small" data-confirm-force>Всё равно назначить</button>
        </div>
      </div>`;
    feedback.querySelector("[data-confirm-force]").addEventListener("click", () =>
      tryManualAssign(ghostId, locationId, true, feedback)
    );
  }
}

async function loadReport() {
  const r = await Api.getReport();
  if (!r) return;
  const container = document.getElementById("report-content");

  const problematicRows = r.most_problematic.length
    ? r.most_problematic
        .map((p) => `<tr><td>${escapeHtml(p.name)}</td><td>${p.anxiety_level}/10</td><td>${escapeHtml(p.deadline)}</td></tr>`)
        .join("")
    : `<tr><td colspan="3">Все привидения расселены 🎉</td></tr>`;

  const overloadedRows = r.overloaded_locations.length
    ? r.overloaded_locations
        .map(
          (o) =>
            `<tr><td>${escapeHtml(o.location_name)}</td><td>${o.occupied}/${o.capacity}</td><td>${Math.round(
              o.load_ratio * 100
            )}%</td></tr>`
        )
        .join("")
    : `<tr><td colspan="3">Перегруженных мест нет</td></tr>`;

  container.innerHTML = `
    <div class="report-grid">
      <div class="stat-tile"><div class="value">${r.total_ghosts}</div><div class="label">всего заявок</div></div>
      <div class="stat-tile"><div class="value" style="color:var(--ok)">${r.relocated}</div><div class="label">расселено</div></div>
      <div class="stat-tile"><div class="value" style="color:var(--danger)">${r.unrelocated}</div><div class="label">без места</div></div>
    </div>
    <div class="card">
      <h3>Самые проблемные заявки</h3>
      <table><thead><tr><th>Имя</th><th>Тревожность</th><th>Дедлайн</th></tr></thead>
      <tbody>${problematicRows}</tbody></table>
    </div>
    <div class="card">
      <h3>Перегруженные места (загрузка ≥ 80%)</h3>
      <table><thead><tr><th>Место</th><th>Занято</th><th>Загрузка</th></tr></thead>
      <tbody>${overloadedRows}</tbody></table>
    </div>
  `;
}
document.getElementById("refresh-report").addEventListener("click", () => guarded(loadReport));

document.getElementById("worklog-content").innerHTML = window.AI_WORKLOG_HTML || "<p>Worklog не найден.</p>";

(async function init() {
  await guarded(loadGhosts);
  await guarded(loadLocations);
})();
