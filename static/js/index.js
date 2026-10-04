const state = { data: null, access: "all", axis: "release", frontier: false, query: "", sort: "score", direction: -1, selected: null };
const $ = (selector) => document.querySelector(selector);
const percent = (value) => Number.isFinite(value) ? `${value.toFixed(2)}%` : "—";
const dateValue = (value) => value ? Date.parse(`${value}T00:00:00Z`) : null;
const dateLabel = (value) => value ? new Intl.DateTimeFormat("en", { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" }).format(new Date(dateValue(value))) : "Not documented";
const sizeLabel = (row) => row.parameters_b == null ? "Not disclosed" : `${row.parameters_b}B`;
const accessLabel = (access) => access === "open" ? "Open Source" : "Closed Source";
const providerLogos = {
  OpenAI: "openai", Google: "google", Meta: "meta", Microsoft: "microsoft",
  Qwen: "qwen", DeepSeek: "deepseek", NVIDIA: "nvidia",
};

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text != null) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function link(text, href, className) {
  const node = element("a", text, className);
  node.href = href;
  if (href.startsWith("https://")) { node.target = "_blank"; node.rel = "noopener noreferrer"; }
  return node;
}

function rankedRows() {
  return state.data.results.filter((row) => row.complete)
    .sort((a, b) => b.metrics.overall - a.metrics.overall || a.name.localeCompare(b.name));
}

function visibleRows() {
  return state.data.results.filter((row) => (state.access === "all" || row.access === state.access)
    && `${row.name} ${row.provider}`.toLowerCase().includes(state.query));
}

function renderInspector(row) {
  const panel = $("#model-inspector");
  panel.replaceChildren();
  if (!row) { panel.append(element("p", "No matching models. Try another search.")); return; }
  panel.append(element("p", "MODEL DETAIL", "eyebrow"), element("h4", row.name),
    element("p", accessLabel(row.access), `access-badge access-${row.access}`));
  const score = element("div", row.complete ? percent(row.metrics.overall) : "Pending", "inspector-score");
  score.append(element("span", row.complete ? "Overall score" : "Evaluation in progress")); panel.append(score);
  const facts = element("dl");
  for (const [label, value] of [["Release date", dateLabel(row.release_date)], ["Total parameters", sizeLabel(row)],
    ...(row.active_parameters_b ? [["Active parameters", `${row.active_parameters_b}B`]] : []),
    ["Coverage", `${row.n.toLocaleString()} / ${row.expected_n.toLocaleString()}`], ["Judge", row.judge],
    ...(row.evaluated_on ? [["Evaluated", dateLabel(row.evaluated_on)]] : [])]) {
    facts.append(element("dt", label), element("dd", value));
  }
  panel.append(facts);
  const sources = element("div", null, "inspector-sources");
  if (row.release_source) sources.append(link("Release source ↗", row.release_source));
  if (row.parameters_source && row.parameters_source !== row.release_source) sources.append(link("Parameter source ↗", row.parameters_source));
  sources.append(link("Score evidence ↗", row.artifact_url));
  panel.append(sources);
  if (row.release_note) panel.append(element("p", row.release_note, "inspector-note"));
}

function selectModel(row) {
  state.selected = row?.id ?? null;
  document.querySelectorAll("[data-model-id]").forEach((node) => node.classList.toggle("is-selected", node.dataset.modelId === state.selected));
  renderInspector(row);
}

function renderTable(rows) {
  const body = $("#full-results-body"); body.replaceChildren();
  const ranks = rankedRows();
  const accessor = (row) => state.sort === "size" ? row.parameters_b : state.sort === "release" ? dateValue(row.release_date) : row.metrics.overall;
  const sorted = [...rows].sort((a, b) => {
    if (a.complete !== b.complete) return a.complete ? -1 : 1;
    const x = accessor(a), y = accessor(b);
    if (x == null) return y == null ? a.name.localeCompare(b.name) : 1;
    if (y == null) return -1;
    return (x - y) * state.direction || a.name.localeCompare(b.name);
  });
  $("#result-count").textContent = `${rows.length} models${state.query ? ` matching “${state.query}”` : ""} · overall ranking across all models`;
  $("#table-caption").textContent = `StructEval leaderboard: ${rows.filter((r) => r.complete).length} ranked models shown. All models are ranked together by overall score; filters preserve overall ranks. Row labels identify Open Source and Closed Source models. Incomplete evaluations are marked pending.`;
  if (!rows.length) {
    const row = element("tr"), cell = element("td", "No models match your search. Clear the search to see all results.", "empty-results");
    cell.colSpan = 10; row.append(cell); body.append(row);
  }
  for (const model of sorted) {
    const row = element("tr", null, `model-row row-${model.access}`); row.dataset.modelId = model.id;
    const rank = model.complete ? ranks.findIndex((r) => r.metrics.overall === model.metrics.overall) + 1 : null;
    if (rank === 1) row.classList.add("leader-row");
    row.append(element("td", rank == null ? "—" : String(rank).padStart(2, "0"), "rank"));
    const name = element("th", null, "model-cell"); name.scope = "row";
    const button = element("button", model.name, "model-button"); button.type = "button";
    button.addEventListener("click", () => selectModel(model));
    button.addEventListener("focus", () => selectModel(model));
    const details = element("span", null, "model-secondary");
    const badge = element("span", null, `row-access-badge access-${model.access}`);
    const symbol = element("i", null, `legend-dot ${model.access === "open" ? "open-dot" : "closed-dot"}`);
    symbol.setAttribute("aria-hidden", "true");
    badge.append(symbol, element("span", accessLabel(model.access)));
    details.append(element("span", model.provider), badge);
    name.append(button, details); row.append(name);
    if (!model.complete) name.append(element("span", `${model.n.toLocaleString()} / ${model.expected_n.toLocaleString()} evaluated`, "cell-secondary"));
    const size = element("td", null, model.parameters_b == null ? "undisclosed" : "");
    size.append(model.parameters_source ? link(sizeLabel(model), model.parameters_source) : element("span", sizeLabel(model)));
    if (model.active_parameters_b) size.append(element("span", `${model.active_parameters_b}B active`, "cell-secondary")); row.append(size);
    const date = element("td"); date.append(model.release_source ? link(model.release_date ?? "Not documented", model.release_source) : element("span", "Not documented")); row.append(date);
    row.append(element("td", model.complete ? percent(model.metrics.overall) : "Pending", model.complete ? "score" : "pending-score"));
    for (const key of ["t_generation", "t_conversion", "v_generation", "v_conversion"]) row.append(element("td", model.complete ? percent(model.metrics[key]) : "—"));
    const source = element("td"); source.append(link("Data ↗", model.artifact_url, "evidence-link")); row.append(source);
    body.append(row);
  }
  document.querySelectorAll("[data-sort]").forEach((button) => {
    const active = button.dataset.sort === state.sort;
    button.closest("th").setAttribute("aria-sort", active ? (state.direction === -1 ? "descending" : "ascending") : "none");
    button.querySelector("span").textContent = active ? (state.direction === -1 ? "↓" : "↑") : "↕";
  });
}

function svgElement(tag, attrs = {}, text) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, String(value));
  if (text != null) node.textContent = text;
  return node;
}

function scoreDomain(rows) {
  if (!rows.length) return { min: 0, max: 100, step: 20 };
  const scores = rows.map((row) => row.metrics.overall);
  const low = Math.min(...scores), high = Math.max(...scores);
  // Keep single points and tightly clustered scores readable without a zero span.
  const padding = Math.max(2, (high - low) * 0.08);
  const lower = Math.max(0, low - padding), upper = Math.min(100, high + padding);
  const targetStep = (upper - lower) / 6;
  const magnitude = 10 ** Math.floor(Math.log10(targetStep));
  const step = [1, 2, 2.5, 5, 10].map((value) => value * magnitude)
    .reduce((best, value) => Math.abs(value - targetStep) < Math.abs(best - targetStep) ? value : best);
  return {
    min: Math.max(0, Math.floor(lower / step) * step),
    max: Math.min(100, Math.ceil(upper / step) * step),
    step,
  };
}

function renderChart(rows) {
  const svg = $("#score-chart"); svg.replaceChildren();
  const width = Math.max(280, Math.round(svg.parentElement.clientWidth)), height = width < 500 ? 340 : 390;
  const margin = { left: 44, right: 30, top: 30, bottom: 70 };
  const plotW = width - margin.left - margin.right, plotH = height - margin.top - margin.bottom;
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  const isSize = state.axis === "size";
  const plotted = rows.filter((r) => isSize ? r.parameters_b > 0 : Number.isFinite(dateValue(r.release_date)));
  $("#frontier-control").hidden = isSize;
  const hasTimeline = new Set(plotted.map((r) => r.release_date)).size > 1;
  $("#frontier-toggle").disabled = !hasTimeline;
  const domain = scoreDomain(plotted);
  $("#chart-heading").textContent = isSize ? "Score vs. model size" : "Score vs. release date";
  svg.append(svgElement("title", { id: "plot-title" }, $("#chart-heading").textContent),
    svgElement("desc", { id: "plot-description" }, `Overall StructEval score. Vertical axis automatically scaled from ${domain.min} to ${domain.max} percent for the visible models. ${plotted.length} models. ${isSize ? "Logarithmic horizontal axis in billions of total parameters." : "Horizontal axis is the model release date, not evaluation date."} Focus a point to read its details. All scores also appear in the table below.`));
  const y = (score) => margin.top + (domain.max - score) / (domain.max - domain.min) * plotH;
  const yTicks = Array.from({ length: Math.round((domain.max - domain.min) / domain.step) + 1 }, (_, i) => Number((domain.min + i * domain.step).toFixed(2)));
  for (const tick of yTicks) {
    svg.append(svgElement("line", { x1: margin.left, x2: width - margin.right, y1: y(tick), y2: y(tick), class: "grid-line" }),
      svgElement("text", { x: margin.left - 10, y: y(tick) + 4, "text-anchor": "end", class: "tick-label" }, tick));
  }
  svg.append(svgElement("text", { x: margin.left, y: 14, class: "axis-caption" }, "Overall score (%) · auto scale"));
  $("#chart-empty").hidden = plotted.length > 0;
  $("#chart-empty").textContent = rows.length ? "Parameter counts are not disclosed for these models. Switch to release date to explore their scores." : "No completed evaluations match your search.";
  const missing = rows.length - plotted.length;
  $("#chart-note").textContent = isSize
    ? `${plotted.length} of ${rows.length} models plotted. Total parameters, in billions (log scale). ${missing ? `${missing} model${missing === 1 ? " has" : "s have"} no disclosed parameter count and ${missing === 1 ? "is" : "are"} omitted.` : "MoE active parameter counts are listed in model details."}`
    : `Release dates refer to the vendor availability linked in each model's details. ${missing ? `${missing} models with undocumented dates are omitted.` : "Evaluation dates are recorded separately."}`;
  if (!plotted.length) return;
  const values = plotted.map((r) => isSize ? Math.log10(r.parameters_b) : dateValue(r.release_date));
  let min = Math.min(...values), max = Math.max(...values), ticks;
  if (isSize) {
    min = Math.floor(min); max = Math.ceil(max);
    if (min === max) { min -= 0.5; max += 0.5; }
    ticks = [];
    for (let exponent = Math.floor(min); exponent <= Math.ceil(max); exponent++) {
      for (const multiplier of [1, 2, 5]) {
        const val = multiplier * 10 ** exponent;
        if (Math.log10(val) >= min && Math.log10(val) <= max) ticks.push({ value: Math.log10(val), label: `${val}B` });
      }
    }
  } else {
    if (min === max) { min -= 1000 * 86400 * 90; max += 1000 * 86400 * 90; }
    const count = width < 500 ? 3 : 5;
    const formatter = new Intl.DateTimeFormat("en", { month: "short", year: "2-digit", timeZone: "UTC" });
    ticks = Array.from({ length: count }, (_, i) => { const value = min + (max - min) * i / (count - 1); return { value, label: formatter.format(new Date(value)) }; });
  }
  const pad = (max - min) * 0.07;
  const x = (value) => margin.left + (value - min + pad) / (max - min + 2 * pad) * plotW;
  for (const tick of ticks) svg.append(svgElement("text", { x: x(tick.value), y: height - 32, "text-anchor": "middle", class: "tick-label" }, tick.label));
  svg.append(svgElement("text", { x: margin.left + plotW / 2, y: height - 9, "text-anchor": "middle", class: "axis-caption" }, isSize ? "Total parameters (billions, log scale)" : "Model release date"));
  const points = plotted.map((row, i) => ({ row, x: x(values[i]), y: y(row.metrics.overall) }));
  if (!isSize && state.frontier && hasTimeline) {
    // Same-day releases contribute their highest score before the running maximum.
    const dailyBest = new Map();
    for (const row of plotted) {
      const date = dateValue(row.release_date);
      dailyBest.set(date, Math.max(dailyBest.get(date) ?? -Infinity, row.metrics.overall));
    }
    const timeline = [...dailyBest].sort((a, b) => a[0] - b[0]);
    let best = timeline[0][1];
    let path = `M ${x(timeline[0][0])} ${y(best)}`;
    for (const [date, score] of timeline.slice(1)) {
      path += ` H ${x(date)}`;
      if (score > best) { best = score; path += ` V ${y(best)}`; }
    }
    const line = svgElement("path", { d: path, class: "best-score-line" });
    line.append(svgElement("title", {}, "Best observed score among the visible models released by each date"));
    svg.append(line);
    const explanation = " Line: best observed score among the shown models released by each date; based on current results, not historical leaderboard snapshots.";
    $("#chart-note").textContent += explanation;
    svg.querySelector("desc").textContent += explanation;
  }
  const labelBoxes = [];
  for (const point of points) {
    const row = point.row, color = row.access === "open" ? "#087451" : "#274bb5";
    const group = svgElement("g", { transform: `translate(${point.x},${point.y})`, class: "plot-point", tabindex: "0", role: "button", "data-model-id": row.id,
      "aria-label": `${row.name}, ${accessLabel(row.access)}, ${percent(row.metrics.overall)} overall, released ${dateLabel(row.release_date)}, ${sizeLabel(row)} total parameters. Show details.` });
    group.append(svgElement("circle", { r: 18, fill: color, class: "point-halo" }));
    const logo = providerLogos[row.provider];
    const marker = svgElement("circle", { r: 13, fill: "white", stroke: "#c4cdc8", class: "point-shape" });
    group.append(marker);
    if (logo) {
      const logoImage = svgElement("image", { href: `./static/images/providers/${logo}.svg`, x: -9, y: -9, width: 18, height: 18,
        preserveAspectRatio: "xMidYMid meet", class: "point-logo", "aria-hidden": "true" });
      logoImage.addEventListener("error", () => { logoImage.remove(); marker.setAttribute("fill", color); });
      group.append(logoImage);
    } else {
      marker.setAttribute("fill", color);
    }
    const accessMark = row.access === "open"
      ? svgElement("circle", { cx: 11, cy: 11, r: 5.5, fill: color, class: "point-access-mark", "aria-hidden": "true" })
      : svgElement("path", { d: "M11 4 L18 11 L11 18 L4 11 Z", fill: color, class: "point-access-mark", "aria-hidden": "true" });
    group.append(accessMark);
    group.append(svgElement("title", {}, `${row.name} · ${accessLabel(row.access)} · ${percent(row.metrics.overall)} · ${dateLabel(row.release_date)} · ${sizeLabel(row)}`));
    for (const event of ["pointerenter", "focus", "click"]) group.addEventListener(event, () => selectModel(row));
    group.addEventListener("keydown", (event) => { if (["Enter", " "].includes(event.key)) { event.preventDefault(); selectModel(row); } });
    svg.append(group);
    const name = row.name.replace(" Instruct", "").replace(" 128K", "");
    const labelW = name.length * 5.7;
    const candidates = [[28, -16], [-labelW - 28, -16], [28, 12], [-labelW - 28, 12], [28, -34], [-labelW - 28, -34]];
    for (const [dx, dy] of candidates) {
      const box = { x: point.x + dx, y: point.y + dy - 11, w: labelW, h: 15 };
      if (box.x < margin.left || box.x + box.w > width - 8 || box.y < 21 || box.y + box.h > height - margin.bottom) continue;
      if (labelBoxes.some((b) => box.x < b.x + b.w + 5 && box.x + box.w + 5 > b.x && box.y < b.y + b.h + 3 && box.y + box.h + 3 > b.y)) continue;
      if (points.some((p) => p.x + 20 > box.x && p.x - 16 < box.x + box.w && p.y + 20 > box.y && p.y - 16 < box.y + box.h)) continue;
      labelBoxes.push(box);
      svg.append(svgElement("text", { x: box.x, y: box.y + 11, class: "point-label" }, name)); break;
    }
  }
}

function renderBoard() {
  const rows = visibleRows();
  document.querySelectorAll("[data-legend-access]").forEach((node) => {
    node.hidden = state.access !== "all" && node.dataset.legendAccess !== state.access;
  });
  renderTable(rows); renderChart(rows.filter((r) => r.complete));
  const eligible = rows.filter((r) => r.complete && (state.axis !== "size" || r.parameters_b > 0));
  selectModel(eligible.find((r) => r.id === state.selected) ?? eligible[0] ?? rows[0]);
}

async function loadLeaderboard() {
  const response = await fetch("./static/data/leaderboard.json");
  if (!response.ok) throw new Error(`Leaderboard request failed: ${response.status}`);
  state.data = await response.json();
  if (state.data.schema_version !== 3 || !Array.isArray(state.data.results)) throw new Error("Unsupported leaderboard snapshot");
  const date = $("#snapshot-date"); date.dateTime = state.data.updated_at;
  date.textContent = new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" }).format(new Date(state.data.updated_at));
  $("#frontier-toggle").addEventListener("change", (event) => {
    state.frontier = event.target.checked;
    renderBoard();
  });
  document.querySelectorAll("[data-access]").forEach((button) => button.addEventListener("click", () => {
    state.access = button.dataset.access;
    document.querySelectorAll("[data-access]").forEach((b) => b.setAttribute("aria-pressed", String(b === button)));
    renderBoard();
  }));
  document.querySelectorAll("[data-axis]").forEach((button) => button.addEventListener("click", () => {
    state.axis = button.dataset.axis;
    document.querySelectorAll("[data-axis]").forEach((b) => b.setAttribute("aria-pressed", String(b === button)));
    renderBoard();
  }));
  $("#model-search").addEventListener("input", (event) => { state.query = event.target.value.trim().toLowerCase(); renderBoard(); });
  document.querySelectorAll("[data-sort]").forEach((button) => button.addEventListener("click", () => {
    if (state.sort === button.dataset.sort) state.direction *= -1;
    else { state.sort = button.dataset.sort; state.direction = -1; }
    renderTable(visibleRows());
    selectModel(visibleRows().find((r) => r.id === state.selected));
  }));
  renderBoard();
  let previousWidth = 0;
  new ResizeObserver((entries) => {
    const width = Math.round(entries[0].contentRect.width);
    if (width !== previousWidth) { previousWidth = width; renderChart(visibleRows().filter((r) => r.complete)); selectModel(visibleRows().find((r) => r.id === state.selected)); }
  }).observe($("#score-chart").parentElement);
}

function enableMobileNavigation() {
  const burger = $(".navbar-burger"), menu = $(".navbar-menu");
  burger.addEventListener("click", () => {
    const expanded = burger.getAttribute("aria-expanded") !== "true";
    burger.setAttribute("aria-expanded", String(expanded)); burger.classList.toggle("is-active", expanded); menu.classList.toggle("is-active", expanded);
  });
  menu.querySelectorAll("a").forEach((a) => a.addEventListener("click", () => {
    burger.setAttribute("aria-expanded", "false"); burger.classList.remove("is-active"); menu.classList.remove("is-active");
  }));
}

document.addEventListener("DOMContentLoaded", () => {
  enableMobileNavigation();
  loadLeaderboard().catch((error) => {
    const row = element("tr"), cell = element("td", "Results could not be loaded. Reload this page or download the results snapshot above.", "load-error");
    cell.colSpan = 10; row.append(cell); $("#full-results-body").replaceChildren(row);
    $("#snapshot-date").textContent = "unavailable";
    $("#chart-empty").hidden = false; $("#chart-empty").textContent = "Chart unavailable while result data cannot be loaded.";
    console.error(error);
  });
});
