const data = window.DASHBOARD_DATA;
const snapshot = window.LIVE_SNAPSHOT || {
  metrics: {},
  sourceSnapshots: [],
  notes: [],
  history: {},
  liveMetricCount: 0,
  sourceSnapshotCount: 0,
  generatedAt: ""
};

const sourceById = new Map(data.sources.map((source) => [source.id, source]));
const sourceSnapshotsBySourceId = new Map();
const trendCache = new Map();
const freshnessCache = new Map();
const referenceOnlyMetrics = new Set([
  "Land purchase area by developers",
  "Politburo and State Council wording changes",
  "Major-city mortgage and purchase restriction changes",
  "Foreign holdings of onshore bonds and equities",
  "Night lights",
  "Local-government special bond issuance",
  "LGFV stress proxies"
]);
const snapshotReferenceDate = (() => {
  const parsed = new Date(snapshot.generatedAt || "");
  return Number.isNaN(parsed.getTime()) ? new Date() : parsed;
})();

for (const item of snapshot.sourceSnapshots || []) {
  if (!sourceSnapshotsBySourceId.has(item.sourceId)) {
    sourceSnapshotsBySourceId.set(item.sourceId, []);
  }
  sourceSnapshotsBySourceId.get(item.sourceId).push(item);
}

for (const [sourceId, items] of sourceSnapshotsBySourceId.entries()) {
  items.sort((left, right) => String(right.date).localeCompare(String(left.date)));
  sourceSnapshotsBySourceId.set(sourceId, items);
}

const allMetrics = data.cycles.flatMap((cycle) =>
  cycle.metrics.map((metric) => ({
    ...metric,
    cycleId: cycle.id,
    cycleName: cycle.name,
    cycleCadence: cycle.cadence
  }))
);

const state = {
  filterMode: "all",
  search: "",
  cadence: "all"
};

const summaryPanel = document.querySelector("#summary-panel");
const signalGrid = document.querySelector("#signal-grid");
const insightGrid = document.querySelector("#insight-grid");
const cycleNav = document.querySelector("#cycle-nav");
const sourceGrid = document.querySelector("#source-grid");
const liveSourceList = document.querySelector("#live-source-list");
const snapshotNotes = document.querySelector("#snapshot-notes");
const synthesisSection = document.querySelector("#synthesis-section");
const cyclesGrid = document.querySelector("#cycles-grid");
const emptyState = document.querySelector("#empty-state");
const searchInput = document.querySelector("#search-input");
const cadenceFilter = document.querySelector("#cadence-filter");
const toggleButtons = Array.from(document.querySelectorAll(".toggle-button"));

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function normalizeText(value) {
  return String(value ?? "")
    .replaceAll("\u00a0", " ")
    .replaceAll("Â", "")
    .replace(/\s+/g, " ")
    .trim();
}

function uniq(values) {
  return [...new Set(values)];
}

function humanJoin(items) {
  const filtered = items.filter(Boolean);
  if (filtered.length <= 1) {
    return filtered[0] || "";
  }
  if (filtered.length === 2) {
    return `${filtered[0]} and ${filtered[1]}`;
  }
  return `${filtered.slice(0, -1).join(", ")}, and ${filtered[filtered.length - 1]}`;
}

function formatDate(value) {
  if (!value) {
    return "";
  }

  const isoOnly = /^\d{4}-\d{2}-\d{2}$/;
  const parsed = isoOnly.test(value) ? new Date(`${value}T00:00:00`) : new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric"
  });
}

function formatTimestamp(value) {
  if (!value) {
    return "";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
}

function formatMonthYear(value) {
  if (!value) {
    return "";
  }

  const parsed = parseSnapshotDate(value);
  if (!parsed) {
    return "";
  }

  return parsed.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short"
  });
}

function looksLikeReleaseTitle(value) {
  const text = normalizeText(value).toLowerCase();
  if (!text) {
    return false;
  }

  if (text.length > 52) {
    return true;
  }

  return /(national economy|sales prices of|investment in real estate|consumer price index|producer prices|purchasing managers'? index|profit of industrial enterprises|statistical communiqué|announcement on open market|financial statistics report|analysis report|historical daily statistics|made a steady start|maintained stable growth|got off to a robust and promising start|steady improvement despite challenges|market operation)/i.test(
    text
  );
}

function cleanPeriodLabel(value, fallbackDate = "") {
  const text = normalizeText(value);
  if (!text) {
    return formatMonthYear(fallbackDate) || formatDate(fallbackDate) || "";
  }

  if (/^\d{4}$/.test(text)) {
    return text;
  }

  if (/^\d{4}-\d{2}$/.test(text)) {
    return formatMonthYear(`${text}-01`) || text;
  }

  if (/^\d{4}-\d{2}-\d{2}$/.test(text) || /^\d{4}\/\d{2}\/\d{2}/.test(text)) {
    return formatDate(text);
  }

  if (looksLikeReleaseTitle(text)) {
    return formatMonthYear(fallbackDate) || formatDate(fallbackDate) || "";
  }

  return text;
}

function historyPeriodLabel(point) {
  return cleanPeriodLabel(point?.period || "", point?.date || "") || "the prior period";
}

function parseSnapshotDate(value) {
  if (!value) {
    return null;
  }

  const isoOnly = /^\d{4}-\d{2}-\d{2}$/;
  const parsed = isoOnly.test(value) ? new Date(`${value}T00:00:00`) : new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function hasReadableValue(value) {
  return Boolean(normalizeText(value));
}

function fillCadenceOptions() {
  if (!cadenceFilter) {
    return;
  }

  const cadences = uniq(allMetrics.map((metric) => metric.cadence)).sort((left, right) =>
    left.localeCompare(right)
  );

  cadenceFilter.insertAdjacentHTML(
    "beforeend",
    cadences
      .map((cadence) => `<option value="${escapeHtml(cadence)}">${escapeHtml(cadence)}</option>`)
      .join("")
  );
}

function liveMetricFor(metric) {
  return snapshot.metrics?.[metric.name] || null;
}

function liveMetricText(metric) {
  const liveMetric = liveMetricFor(metric);
  return normalizeText([liveMetric?.value || "", liveMetric?.secondary || ""].join(" "));
}

function latestMetricRecord(metric) {
  const liveMetric = liveMetricFor(metric);
  if (liveMetric && (hasReadableValue(liveMetric.value) || hasReadableValue(liveMetric.secondary))) {
    return {
      date: liveMetric.date || "",
      period: cleanPeriodLabel(liveMetric.period || "", liveMetric.date || ""),
      kind: "live"
    };
  }

  const history = historyForMetric(metric);
  if (history.length) {
    return {
      date: history[0].date || "",
      period: historyPeriodLabel(history[0]),
      kind: "history"
    };
  }

  const snapshots = latestSnapshotsForMetric(metric);
  if (snapshots.length) {
    return {
      date: snapshots[0].date || "",
      period: normalizeText(formatDate(snapshots[0].date)),
      kind: "snapshot"
    };
  }

  return {
    date: "",
    period: "",
    kind: "none"
  };
}

function metricAgeDays(metric) {
  const latest = latestMetricRecord(metric);
  const parsed = parseSnapshotDate(latest.date);
  if (!parsed) {
    return null;
  }
  return Math.max(0, Math.floor((snapshotReferenceDate.getTime() - parsed.getTime()) / 86400000));
}

function freshnessWindowDays(metric) {
  const cadence = String(metric.cadence || "").toLowerCase();
  if (cadence.includes("daily")) {
    return 7;
  }
  if (cadence.includes("weekly")) {
    return 21;
  }
  if (cadence.includes("event")) {
    return 240;
  }
  if (cadence.includes("monthly") && cadence.includes("quarterly")) {
    return 140;
  }
  if (cadence.includes("monthly")) {
    return 75;
  }
  if (cadence.includes("quarterly")) {
    return 200;
  }
  if (cadence.includes("annual") || cadence.includes("year")) {
    return 540;
  }
  return 120;
}

function isStructuralMetric(metric) {
  const latest = latestMetricRecord(metric);
  const cadence = String(metric.cadence || "").toLowerCase();
  const period = latest.period;

  if (cadence.includes("annual") || cadence.includes("year")) {
    return true;
  }

  if (/^\d{4}$/.test(period) || /\bannual\b/i.test(period)) {
    return true;
  }

  return false;
}

function metricFreshness(metric) {
  if (freshnessCache.has(metric.name)) {
    return freshnessCache.get(metric.name);
  }

  const liveMetric = liveMetricFor(metric);
  const latest = latestMetricRecord(metric);
  const snapshots = latestSnapshotsForMetric(metric);
  const ageDays = metricAgeDays(metric);
  const threshold = freshnessWindowDays(metric);
  const periodLabel = latest.period || normalizeText(liveMetric?.period || "");
  const datedLabel = periodLabel || formatDate(latest.date) || "the latest available source snapshot";
  let result;

  if (!liveMetric || (!hasReadableValue(liveMetric.value) && !hasReadableValue(liveMetric.secondary))) {
    if (snapshots.length) {
      result = {
        status: "context",
        label: "Context only",
        detail: `A release was pulled for ${datedLabel}, but no direct numeric reading is parsed yet.`,
        ageDays
      };
    } else {
      result = {
        status: "missing",
        label: "No value",
        detail: "The source is configured, but there is no direct parsed reading loaded yet.",
        ageDays
      };
    }
  } else if (isStructuralMetric(metric)) {
    result = {
      status: "structural",
      label: "Structural",
      detail: `Latest point is ${datedLabel}. This is useful background, but it should not drive the live month-to-month story.`,
      ageDays
    };
  } else if (referenceOnlyMetrics.has(metric.name) || (ageDays !== null && ageDays > threshold)) {
    result = {
      status: "stale",
      label: "Reference only",
      detail: `Latest point is ${datedLabel}. Kept on-page for context, but excluded from the main briefing because it is too old or incomplete.`,
      ageDays
    };
  } else if (ageDays !== null && ageDays > threshold * 0.55) {
    result = {
      status: "aging",
      label: "Recent",
      detail: `Latest point is ${datedLabel}. Still usable in the main briefing, but not one of the freshest signals on the page.`,
      ageDays
    };
  } else {
    result = {
      status: "current",
      label: "Current",
      detail: `Latest point is ${datedLabel}. Fresh enough to shape the main briefing.`,
      ageDays
    };
  }

  freshnessCache.set(metric.name, result);
  return result;
}

function latestSnapshotsForSourceId(sourceId) {
  return sourceSnapshotsBySourceId.get(sourceId) || [];
}

function latestSnapshotsForMetric(metric) {
  return uniq(
    metric.sourceIds.flatMap((sourceId) =>
      latestSnapshotsForSourceId(sourceId).map((item) => item.releaseId)
    )
  )
    .map((releaseId) =>
      (snapshot.sourceSnapshots || []).find((item) => item.releaseId === releaseId)
    )
    .filter(Boolean)
    .sort((left, right) => String(right.date).localeCompare(String(left.date)));
}

function historyForMetric(metric) {
  return (snapshot.history?.[metric.name] || []).slice().sort((left, right) =>
    String(right.date).localeCompare(String(left.date))
  );
}

function visibleSourcesForMetric(metric) {
  const resolved = metric.sourceIds.map((id) => sourceById.get(id)).filter(Boolean);
  if (state.filterMode !== "official") {
    return resolved;
  }
  return resolved.filter((source) => source.type === "official");
}

function primarySourceForMetric(metric) {
  const liveMetric = liveMetricFor(metric);
  if (liveMetric?.sourceId && sourceById.has(liveMetric.sourceId)) {
    return sourceById.get(liveMetric.sourceId);
  }

  const visibleSources = visibleSourcesForMetric(metric);
  if (visibleSources.length) {
    return visibleSources[0];
  }

  return metric.sourceIds.map((id) => sourceById.get(id)).find(Boolean) || null;
}

function metricVisibleByMode(metric) {
  const sources = metric.sourceIds.map((id) => sourceById.get(id)).filter(Boolean);
  const hasLiveMetric = Boolean(liveMetricFor(metric));
  const hasLiveContext = latestSnapshotsForMetric(metric).length > 0;

  if (state.filterMode === "mvp" && !metric.mvp) {
    return false;
  }

  if (state.filterMode === "live") {
    return hasLiveMetric || hasLiveContext;
  }

  if (state.filterMode === "official") {
    return sources.some((source) => source.type === "official");
  }

  return true;
}

function metricVisibleByCadence(metric) {
  return state.cadence === "all" || metric.cadence === state.cadence;
}

function metricVisibleBySearch(metric, cycle) {
  if (!state.search) {
    return true;
  }

  const liveMetric = liveMetricFor(metric);
  const liveSnapshots = latestSnapshotsForMetric(metric);
  const haystack = [
    metric.name,
    metric.cadence,
    cycle.name,
    cycle.description,
    ...cycle.whatMatters,
    ...(metric.tags || []),
    liveMetric?.value || "",
    liveMetric?.secondary || "",
    ...liveSnapshots.map((item) => item.title),
    ...liveSnapshots.map((item) => item.summary),
    ...liveSnapshots.flatMap((item) => item.highlights || [])
  ]
    .join(" ")
    .toLowerCase();

  return haystack.includes(state.search);
}

function metricMatches(metric, cycle) {
  if (!metricVisibleByMode(metric)) {
    return false;
  }
  if (!metricVisibleByCadence(metric)) {
    return false;
  }
  if (!metricVisibleBySearch(metric, cycle)) {
    return false;
  }
  return visibleSourcesForMetric(metric).length > 0;
}

function visibleCyclePayloads() {
  return data.cycles
    .map((cycle) => ({
      cycle,
      metrics: cycle.metrics.filter((metric) => metricMatches(metric, cycle))
    }))
    .filter(({ metrics }) => metrics.length);
}

function buildCyclePayloads() {
  return visibleCyclePayloads().map(({ cycle, metrics }) => {
    const rankedMetrics = rankMetrics(metrics);
    const signalMetrics = rankedMetrics.filter((metric) => {
      const freshness = metricFreshness(metric).status;
      return freshness === "current" || freshness === "aging";
    });
    const structuralMetrics = rankedMetrics.filter(
      (metric) => metricFreshness(metric).status === "structural"
    );
    const referenceMetrics = rankedMetrics.filter((metric) =>
      ["stale", "context", "missing"].includes(metricFreshness(metric).status)
    );
    const briefingMetrics = signalMetrics.length
      ? signalMetrics
      : structuralMetrics.length
        ? structuralMetrics
        : rankedMetrics.filter((metric) => metricFreshness(metric).status !== "missing");

    return {
      cycle,
      metrics: rankedMetrics,
      signalMetrics,
      structuralMetrics,
      referenceMetrics,
      briefingMetrics
    };
  });
}

function trendMagnitude(trend) {
  const raw = trend.primary || "";
  const match = raw.match(/([\d.]+)\s*%/);
  return match ? Math.abs(Number(match[1])) : 0;
}

const inverseMetrics = new Set([
  "USD/CNY",
  "Offshore CNH",
  "Urban surveyed unemployment",
  "31-city unemployment",
  "Youth unemployment",
  "PMI finished-goods inventory",
  "Accounts receivable",
  "Per-hundred-yuan costs",
  "Collection period for receivables",
  "Asset-liability ratio",
  "Finished-goods inventory",
  "Operating costs",
  "1Y real interest rate",
  "5Y real interest rate"
]);

function isInverseMetric(metricName) {
  return inverseMetrics.has(metricName);
}

function economicDirection(rawDirection, metricName) {
  if (!isInverseMetric(metricName)) return rawDirection;
  if (rawDirection === "up") return "down";
  if (rawDirection === "down") return "up";
  return rawDirection;
}

function directionFromDelta(delta, baseValue = 1) {
  const threshold = Math.max(Math.abs(baseValue || 1) * 0.003, 0.01);
  if (Math.abs(delta) <= threshold) {
    return "flat";
  }
  return delta > 0 ? "up" : "down";
}

function sparklineGeometry(points, width = 150, height = 34) {
  if (points.length < 2) {
    return null;
  }

  const values = points.map((point) => point.numeric);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const coords = points.map((point, index) => {
    const x = (index / Math.max(points.length - 1, 1)) * width;
    const y = height - ((point.numeric - min) / range) * height;
    return [x, y];
  });

  const line = coords
    .map(([x, y], index) => `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`)
    .join(" ");

  return {
    width,
    height,
    line
  };
}

function historyTrend(metric) {
  const history = historyForMetric(metric);
  const numericPoints = history
    .filter((point) => typeof point.numeric === "number" && Number.isFinite(point.numeric))
    .slice()
    .reverse();

  if (numericPoints.length < 2) {
    return null;
  }

  const earliest = numericPoints[0];
  const latest = numericPoints[numericPoints.length - 1];
  const previous = numericPoints[numericPoints.length - 2];
  const longDirection = directionFromDelta(latest.numeric - earliest.numeric, earliest.numeric);
  const shortDirection = directionFromDelta(latest.numeric - previous.numeric, previous.numeric);

  return {
    history,
    numericPoints,
    earliest,
    latest,
    previous,
    longDirection,
    shortDirection
  };
}

function firstNumeric(text) {
  const match = normalizeText(text)
    .replaceAll(",", "")
    .match(/-?\d+(?:\.\d+)?/);
  return match ? Number(match[0]) : null;
}

function formatSigned(value, digits = 1) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return "";
  }
  const formatted = Math.abs(number).toFixed(digits);
  if (number > 0) {
    return `+${formatted}`;
  }
  if (number < 0) {
    return `-${formatted}`;
  }
  return Number(formatted).toFixed(digits);
}

function percentTokens(text) {
  const raw = normalizeText(text);
  const tokens = [];
  const regex = /([+-]?\d+(?:\.\d+)?)\s*%\s*(y\/y|m\/m|q\/q)/gi;
  let match;

  while ((match = regex.exec(raw))) {
    tokens.push({
      value: Number(match[1]),
      period: match[2].toLowerCase(),
      raw: `${formatSigned(Number(match[1]), 1)}% ${match[2].toLowerCase()}`
    });
  }

  return tokens;
}

function pointToken(text) {
  const raw = normalizeText(text);
  const match = raw.match(/([+-]?\d+(?:\.\d+)?)\s*(pp|pts?|points?)/i);
  if (!match) {
    return null;
  }

  return {
    value: Number(match[1]),
    unit: match[2].toLowerCase().startsWith("p") ? "pp" : "pts",
    raw: `${formatSigned(Number(match[1]), 1)} ${match[2].toLowerCase().startsWith("p") ? "pp" : "pts"}`
  };
}

function directionalAmount(text) {
  const raw = normalizeText(text);
  let match = raw.match(/\b(Up|Down)\s+((?:RMB|USD|CNY)\s*[\d.,]+\s*(?:tn|bn|mn|million|billion|trillion)?)(.*)$/i);
  if (match) {
    return {
      direction: match[1].toLowerCase() === "up" ? "up" : "down",
      primary: `${match[1].toLowerCase() === "up" ? "+" : "-"}${normalizeText(match[2])}`,
      secondary: normalizeText(match[3]).replace(/^vs\s*/i, "vs ")
    };
  }

  match = raw.match(/^([+-])\s*((?:RMB|USD|CNY)\s*[\d.,]+\s*(?:tn|bn|mn|million|billion|trillion)?)(.*)$/i);
  if (match) {
    return {
      direction: match[1] === "+" ? "up" : "down",
      primary: `${match[1]}${normalizeText(match[2])}`,
      secondary: normalizeText(match[3])
    };
  }

  return null;
}

function readSignedLevel(text) {
  const raw = normalizeText(text);
  const match = raw.match(/^\s*([+-])\s*(?:[A-Za-z]{1,6}\s*)?(\d+(?:\.\d+)?)/);
  if (!match) {
    return null;
  }

  const direction = match[1] === "+" ? "up" : "down";
  return {
    direction,
    summary: direction === "up" ? "Net increase in the latest period." : "Net decrease in the latest period.",
    detail: raw
  };
}

function readSignedChange(text) {
  const raw = String(text || "");
  const yearMatch = raw.match(/([+-]\d+(?:\.\d+)?)\s*%\s*(?:y\/y|year|from a year|vs\s*[a-z0-9-]+)/i);
  if (yearMatch) {
    return {
      direction: Number(yearMatch[1]) > 0 ? "up" : "down",
      summary: `${Number(yearMatch[1]) > 0 ? "Up" : "Down"} ${Math.abs(Number(yearMatch[1]))}% from a year ago.`,
      detail: raw
    };
  }

  const monthMatch = raw.match(/([+-]\d+(?:\.\d+)?)\s*%\s*(?:m\/m|month)/i);
  if (monthMatch) {
    return {
      direction: Number(monthMatch[1]) > 0 ? "up" : "down",
      summary: `${Number(monthMatch[1]) > 0 ? "Up" : "Down"} ${Math.abs(Number(monthMatch[1]))}% from a month ago.`,
      detail: raw
    };
  }

  const ppMatch = raw.match(/([+-]\d+(?:\.\d+)?)\s*pp\b/i);
  if (ppMatch) {
    return {
      direction: Number(ppMatch[1]) > 0 ? "up" : "down",
      summary: `${Number(ppMatch[1]) > 0 ? "Up" : "Down"} ${Math.abs(Number(ppMatch[1]))} percentage points.`,
      detail: raw
    };
  }

  const genericChange = raw.match(/\b(up|down)\b\s*([A-Z]{0,4}\s*)?([\d.]+)/i);
  if (genericChange) {
    return {
      direction: genericChange[1].toLowerCase() === "up" ? "up" : "down",
      summary: `${genericChange[1][0].toUpperCase()}${genericChange[1].slice(1).toLowerCase()} versus the prior comparison period.`,
      detail: raw
    };
  }

  return null;
}

function readUpDownCounts(text) {
  const raw = String(text || "");
  const match = raw.match(/(\d+)\s*up\s*\/\s*(\d+)\s*flat\s*\/\s*(\d+)\s*down/i);
  if (!match) {
    return null;
  }

  const up = Number(match[1]);
  const flat = Number(match[2]);
  const down = Number(match[3]);
  if (up > down) {
    return {
      direction: "up",
      summary: `More cities are up than down.`,
      detail: `${up} up, ${flat} flat, ${down} down.`
    };
  }

  if (down > up) {
    return {
      direction: "down",
      summary: `More cities are down than up.`,
      detail: `${down} down, ${flat} flat, ${up} up.`
    };
  }

  return {
    direction: "flat",
    summary: `Up and down readings are evenly split.`,
    detail: `${up} up, ${flat} flat, ${down} down.`
  };
}

function readMixedSignals(text) {
  const raw = String(text || "");
  const positiveCount = (raw.match(/\+\d+(?:\.\d+)?/g) || []).length;
  const negativeCount = (raw.match(/-\d+(?:\.\d+)?/g) || []).length;

  if (positiveCount > 0 && negativeCount > 0) {
    return {
      direction: "mixed",
      summary: "Some parts are up while others are down.",
      detail: raw
    };
  }

  return null;
}

function hasExplicitChangeSignal(rawText) {
  return Boolean(
    percentTokens(rawText).length ||
      pointToken(rawText) ||
      directionalAmount(rawText) ||
      readSignedChange(rawText) ||
      readUpDownCounts(rawText)
  );
}

function historySignalIsReliable(metric, history, rawText) {
  if (!history) {
    return false;
  }

  if (history.numericPoints.length >= 3) {
    return true;
  }

  if (hasExplicitChangeSignal(rawText)) {
    return true;
  }

  const cadence = String(metric.cadence || "").toLowerCase();
  const metricName = metric.name.toLowerCase();
  if (
    cadence.includes("daily") ||
    cadence.includes("weekly") ||
    cadence.includes("quarter") ||
    cadence.includes("annual") ||
    cadence.includes("year")
  ) {
    return true;
  }

  return /usd\/cny|cnh|csi 300|hang seng|index|yield|lpr|rrr|repo|fx reserves|population|births|deaths|urbanization|working-age|capacity utilization/.test(
    metricName
  );
}

function plainLevelTrend(metric, liveMetric) {
  const value = normalizeText(liveMetric?.value || "");
  if (!value) {
    return null;
  }

  const metricName = metric.name.toLowerCase();
  const secondary =
    normalizeText(liveMetric?.secondary || "") ||
    cleanPeriodLabel(liveMetric?.period || "", liveMetric?.date || "");
  let primary = value;
  const rawText = normalizeText([value, secondary].join(" "));
  const netFlowMatch = rawText.match(
    /\bnet (buy|sell)\s+((?:HKD|RMB|USD|CNY)\s*[\d,.\s]+(?:m|mn|bn|tn|million|billion|trillion)?)/i
  );
  let direction = "update";
  let label = "Latest";
  let summary = "Latest available reading.";

  if (/\bnet sell\b/i.test(rawText)) {
    direction = "down";
    label = "Down";
    if (netFlowMatch) {
      primary = `Net ${netFlowMatch[1].toLowerCase()} ${normalizeText(netFlowMatch[2])}`;
    }
    summary = "Latest flow shows net selling.";
  } else if (/\bnet buy\b/i.test(rawText)) {
    direction = "up";
    label = "Up";
    if (netFlowMatch) {
      primary = `Net ${netFlowMatch[1].toLowerCase()} ${normalizeText(netFlowMatch[2])}`;
    }
    summary = "Latest flow shows net buying.";
  } else if (/rate|yield|lpr|rrr|repo/.test(metricName)) {
    summary = "Latest policy or market level.";
  } else if (/liquidity operations|omo|reverse repo/.test(metricName)) {
    summary = "Latest liquidity operation.";
  } else if (/stock connect/.test(metricName)) {
    if (netFlowMatch) {
      primary = `Net ${netFlowMatch[1].toLowerCase()} ${normalizeText(netFlowMatch[2])}`;
      direction = netFlowMatch[1].toLowerCase() === "buy" ? "up" : "down";
      label = direction === "up" ? "Up" : "Down";
    }
    summary = "Latest Stock Connect flow reading.";
  } else if (/trade balance/.test(metricName)) {
    summary = "Latest trade balance reading.";
  } else if (/industrial production by sector/.test(metricName)) {
    summary = "Latest sector breakdown from the release.";
  } else if (/household formation proxies/.test(metricName)) {
    summary = "Latest housing-demand proxy reading.";
  } else if (/shipments|imports by commodity|exports by destination|output by sector/.test(metricName)) {
    summary = "Latest breakdown from the source release.";
  } else if (/loans|financing|bond issuance|funds available|mortgage/.test(metricName)) {
    summary = "Latest financing reading.";
  }

  return {
    direction,
    label,
    primary,
    secondary,
    summary,
    detail: rawText,
    basis: "release"
  };
}

function inferTrend(metric) {
  if (trendCache.has(metric.name)) {
    return trendCache.get(metric.name);
  }

  const liveMetric = liveMetricFor(metric);
  const rawText = liveMetricText(metric);
  const history = historyTrend(metric);
  const metricName = metric.name.toLowerCase();

  if (/70-city|home price index/.test(metricName)) {
    const mmMatch = normalizeText(liveMetric?.value).match(/([\d.]+)$/);
    const yyMatch = normalizeText(liveMetric?.secondary).match(/Avg Y\/Y\s*([\d.]+)/i);
    const citySplit = readUpDownCounts(liveMetric?.secondary || "");

    if (mmMatch) {
      const mmValue = Number(mmMatch[1]) - 100;
      const yyValue = yyMatch ? Number(yyMatch[1]) - 100 : null;
      const result = {
        direction: directionFromDelta(mmValue, 1),
        label: mmValue > 0 ? "Up" : mmValue < 0 ? "Down" : "Flat",
        primary: `${formatSigned(mmValue, 2)}% m/m`,
        secondary: yyValue !== null ? `${formatSigned(yyValue, 2)}% y/y` : citySplit?.detail || "",
        summary:
          mmValue === 0
            ? "Flat month to month."
            : `${mmValue > 0 ? "Up" : "Down"} ${Math.abs(mmValue).toFixed(2)}% month to month.`,
        detail: citySplit?.detail || rawText,
        basis: "release"
      };
      trendCache.set(metric.name, result);
      return result;
    }
  }

  if (/real interest rate/.test(metricName)) {
    const rateMatch = normalizeText(liveMetric?.value).match(/([+-]?\d+(?:\.\d+)?)%/);
    if (rateMatch) {
      const level = Number(rateMatch[1]);
      const result = {
        direction: level > 0 ? "up" : level < 0 ? "down" : "flat",
        label: level > 0 ? "Up" : level < 0 ? "Down" : "Flat",
        primary: `${formatSigned(level, 2)}%`,
        secondary: normalizeText(liveMetric?.secondary || ""),
        summary: `Current real rate is ${level > 0 ? "+" : ""}${level.toFixed(2)}%. ${level > 1.5 ? "Tight relative to deflation risk." : level > 0 ? "Mildly positive real rate." : "Accommodative \u2014 real rate is negative."}`,
        detail: rawText,
        basis: "release"
      };
      trendCache.set(metric.name, result);
      return result;
    }
  }

  const explicitPercents = percentTokens(rawText);
  if (explicitPercents.length) {
    const priority = { "y/y": 0, "q/q": 1, "m/m": 2 };
    explicitPercents.sort((left, right) => (priority[left.period] ?? 9) - (priority[right.period] ?? 9));
    const primaryToken = explicitPercents[0];
    const secondaryToken = explicitPercents[1] || null;
    let secondaryLabel = secondaryToken ? secondaryToken.raw : "";
    if (secondaryToken && secondaryToken.period === primaryToken.period) {
      const secText = normalizeText(liveMetric?.secondary || "");
      const avgMatch = secText.match(/([\w-]+\s+avg)\s/i);
      if (avgMatch) {
        secondaryLabel = `${avgMatch[1]} ${secondaryToken.raw}`;
      }
    } else if (secondaryToken) {
      secondaryLabel = secondaryToken.raw;
    }
    const result = {
      direction: directionFromDelta(primaryToken.value, 1),
      label:
        primaryToken.value > 0
          ? "Up"
          : primaryToken.value < 0
            ? "Down"
            : "Flat",
      primary: primaryToken.raw,
      secondary: secondaryLabel,
      summary:
        primaryToken.value === 0
          ? `Flat on a ${primaryToken.period} basis.`
          : `${primaryToken.value > 0 ? "Up" : "Down"} ${Math.abs(primaryToken.value).toFixed(1)}% on a ${primaryToken.period} basis.`,
      detail: rawText,
      basis: "release"
    };
    trendCache.set(metric.name, result);
    return result;
  }

  const explicitPoints = pointToken(rawText);
  if (explicitPoints) {
    const result = {
      direction: directionFromDelta(explicitPoints.value, 1),
      label:
        explicitPoints.value > 0
          ? "Up"
          : explicitPoints.value < 0
            ? "Down"
            : "Flat",
      primary: explicitPoints.raw,
      secondary: normalizeText(liveMetric?.value || ""),
      summary:
        explicitPoints.value === 0
          ? "No net point change."
          : `${explicitPoints.value > 0 ? "Up" : "Down"} ${Math.abs(explicitPoints.value).toFixed(1)} percentage points.`,
      detail: rawText,
      basis: "release"
    };
    trendCache.set(metric.name, result);
    return result;
  }

  const amountMove = directionalAmount(liveMetric?.secondary || "");
  if (amountMove) {
    const result = {
      direction: amountMove.direction,
      label: amountMove.direction === "up" ? "Up" : "Down",
      primary: amountMove.primary,
      secondary: amountMove.secondary,
      summary: `${amountMove.direction === "up" ? "Higher" : "Lower"} than the comparison period.`,
      detail: rawText,
      basis: "release"
    };
    trendCache.set(metric.name, result);
    return result;
  }

  if (history && historySignalIsReliable(metric, history, rawText)) {
    const labelMap = {
      up: "Up",
      down: "Down",
      flat: "Flat"
    };
    const delta = history.latest.numeric - history.earliest.numeric;
    const comparisonLabel = historyPeriodLabel(history.earliest);
    const latestLabel = historyPeriodLabel(history.latest);
    let primary = "";
    let secondary = latestLabel
      ? `Latest ${history.latest.value} (${latestLabel})`
      : `Latest ${history.latest.value}`;

    if (/pmi/.test(metricName)) {
      primary = `${formatSigned(delta, 1)} pts vs ${comparisonLabel}`;
    } else if (/%/.test(normalizeText(history.latest.value)) || /rate|yield|unemployment|lpr|rrr/.test(metricName)) {
      primary = `${formatSigned(delta, 1)} pp vs ${comparisonLabel}`;
    } else if (/usd\/cny|cnh|csi 300|hang seng|index/.test(metricName)) {
      const pct = history.earliest.numeric !== 0 ? (delta / Math.abs(history.earliest.numeric)) * 100 : 0;
      primary = `${formatSigned(pct, 1)}% vs ${comparisonLabel}`;
      secondary = `${formatSigned(delta, 2)} absolute move`;
    } else {
      const pct = history.earliest.numeric !== 0 ? (delta / Math.abs(history.earliest.numeric)) * 100 : null;
      primary =
        pct !== null && Number.isFinite(pct)
          ? `${formatSigned(pct, 1)}% vs ${comparisonLabel}`
          : `${formatSigned(delta, 1)} vs ${comparisonLabel}`;
    }

    const result = {
      direction: history.longDirection,
      label: labelMap[history.longDirection],
      primary,
      secondary,
      summary:
        history.longDirection === "flat"
          ? `Roughly flat since ${comparisonLabel}.`
          : `${labelMap[history.longDirection]} since ${comparisonLabel}.`,
      detail:
        history.shortDirection === "flat"
          ? `Latest value is ${history.latest.value}; it is broadly flat versus the prior point.`
          : `Latest value is ${history.latest.value}; it is ${history.shortDirection === "up" ? "higher" : "lower"} than the prior point.`,
      basis: "history",
      history
    };
    trendCache.set(metric.name, result);
    return result;
  }

  const upDownCounts = readUpDownCounts(rawText);
  if (upDownCounts) {
    const result = {
      ...upDownCounts,
      label:
        upDownCounts.direction === "up"
          ? "Up"
          : upDownCounts.direction === "down"
            ? "Down"
            : "Flat",
      primary: upDownCounts.detail,
      secondary: "",
      basis: "release"
    };
    trendCache.set(metric.name, result);
    return result;
  }

  const signedLevel = readSignedLevel(liveMetric?.value || "");
  if (signedLevel) {
    const result = {
      ...signedLevel,
      label: signedLevel.direction === "up" ? "Up" : "Down",
      primary: normalizeText(liveMetric?.value || ""),
      secondary: normalizeText(liveMetric?.secondary || ""),
      basis: "release"
    };
    trendCache.set(metric.name, result);
    return result;
  }

  const mixed = readMixedSignals(rawText);
  if (mixed) {
    const result = {
      ...mixed,
      label: "Mixed",
      primary: normalizeText(liveMetric?.value || "") || "Mixed signal",
      secondary: normalizeText(liveMetric?.secondary || ""),
      basis: "release"
    };
    trendCache.set(metric.name, result);
    return result;
  }

  if (/\b(flat|unchanged|steady)\b/i.test(rawText)) {
    const result = {
      direction: "flat",
      label: "Flat",
      summary: "No clear movement in the latest read.",
      detail: rawText || "Latest release context only.",
      basis: "release"
    };
    trendCache.set(metric.name, result);
    return result;
  }

  if (
    metric.cadence.toLowerCase().includes("event") ||
    /\beffective\b|\blatest\b|\bannouncement\b|\bpolicy\b/i.test(rawText)
  ) {
    const result = {
      direction: "update",
      label: "Update",
      primary: normalizeText(liveMetric?.value || "Latest setting"),
      secondary: normalizeText(liveMetric?.secondary || ""),
      summary: "This is best read as the latest setting or policy change.",
      detail: rawText || "Event-driven release context.",
      basis: "release"
    };
    trendCache.set(metric.name, result);
    return result;
  }

  const levelTrend = plainLevelTrend(metric, liveMetric);
  if (levelTrend) {
    trendCache.set(metric.name, levelTrend);
    return levelTrend;
  }

  const snapshots = latestSnapshotsForMetric(metric);
  if (snapshots.length) {
    const result = {
      direction: "mixed",
      label: "Context",
      primary: "Release context",
      secondary: formatDate(snapshots[0].date),
      summary: "Latest release context is available, but no clean trend line is loaded.",
      detail: snapshots[0].highlights?.[0] || snapshots[0].summary,
      basis: "snapshot"
    };
    trendCache.set(metric.name, result);
    return result;
  }

  const result = {
    direction: "unknown",
    label: "Waiting",
    primary: "No parsed change",
    secondary: "",
    summary: "No simple trend signal is loaded yet.",
    detail: "Source is configured, but no parsed trend is available in the snapshot.",
    basis: "none"
  };
  trendCache.set(metric.name, result);
  return result;
}

function friendlyMetricDescription(metric, cycle) {
  const text = `${metric.name} ${(metric.tags || []).join(" ")}`.toLowerCase();

  if (/home price|housing price|70-city/.test(text)) {
    return "Shows whether home prices are still falling or beginning to stabilize.";
  }
  if (/property sales|sales by floor area|sales by value|housing turnover/.test(text)) {
    return "Shows whether housing demand and buyer activity are coming back.";
  }
  if (/starts|construction under way/.test(text)) {
    return "Shows whether developers are willing to keep building new projects.";
  }
  if (/completion/.test(text)) {
    return "Shows whether homes are actually being delivered rather than just started.";
  }
  if (/real estate investment|land purchase/.test(text)) {
    return "Shows how much money and appetite remain in the property pipeline.";
  }
  if (/funds available|developer/.test(text)) {
    return "Shows whether funding is still reaching property developers.";
  }
  if (/tsf|social financing/.test(text)) {
    return "Shows how much total credit is entering the economy.";
  }
  if (/new rmb loans|household loans|corporate medium\/long-term loans|bankers' acceptances/.test(text)) {
    return "Shows who is borrowing and where credit is actually going.";
  }
  if (/m1|m2/.test(text)) {
    return "Shows how much liquidity is circulating through the economy.";
  }
  if (/lpr|rrr|reverse repo|mlf|liquidity operations/.test(text)) {
    return "Shows how loose or tight policy settings are right now.";
  }
  if (/cpi|food cpi|services cpi|core cpi/.test(text)) {
    return "Shows price pressure that households feel in everyday spending.";
  }
  if (/ppi|input prices|output prices|gdp deflator|nominal gdp/.test(text)) {
    return "Shows whether pricing power and nominal growth are improving or staying weak.";
  }
  if (/retail sales|online retail|catering revenue/.test(text)) {
    return "Shows whether consumers are still spending.";
  }
  if (/unemployment|hours worked|average wage|income/.test(text)) {
    return "Shows whether jobs, hours, and pay are improving.";
  }
  if (/pmi|industrial production|inventory|capacity utilization/.test(text)) {
    return "Shows whether factories are seeing stronger demand or building unwanted stock.";
  }
  if (/industrial profits|profit margin|business revenue|operating costs|receivable/.test(text)) {
    return "Shows whether companies are making money or getting squeezed.";
  }
  if (/exports|imports|trade balance|commodity|integrated-circuit imports|shipping|scfi/.test(text)) {
    return "Shows whether global demand is helping or hurting China’s growth.";
  }
  if (/fx reserves|current account|external debt|foreign holdings/.test(text)) {
    return "Shows the external buffer and the flow of money into or out of China.";
  }
  if (/usd\/cny|cnh|csi 300|hang seng|stock connect|yield spread/.test(text)) {
    return "Shows how markets and investors are reacting.";
  }
  if (/dependency ratio/.test(text)) {
    return "Rising dependency ratio increases fiscal burden and shifts savings dynamics.";
  }
  if (/total fertility rate/.test(text)) {
    return "Below-replacement fertility compounds the demographic drag on housing and labor supply.";
  }
  if (/population|births|deaths|working-age|urbanization|migrant/.test(text)) {
    return "Shows the slower-moving population backdrop for housing, labor, and demand.";
  }
  if (/budget|revenue|expenditure|special bond|infrastructure|land-sales/.test(text)) {
    return "Shows how much fiscal support is reaching the economy.";
  }
  if (/integrated-circuit output|phone shipments|electronics|high-tech|technology-transformation|ev output|solar-cell/.test(text)) {
    return "Shows whether upgrading and tech investment are still moving forward.";
  }
  if (/electricity|rail freight|port throughput|night lights|no2|commodity production/.test(text)) {
    return "Shows real-world activity outside the headline GDP numbers.";
  }

  return `Shows the state of the ${cycle.name.replace(/\s+cycle$/i, "").toLowerCase()} picture.`;
}

function specialInterpretation(metric) {
  const liveMetric = liveMetricFor(metric);
  const value = liveMetric?.value || "";
  const numeric = firstNumeric(value);
  const text = metric.name.toLowerCase();

  if (/official manufacturing pmi|pmi /.test(text) && typeof numeric === "number") {
    if (numeric > 50) {
      return "Above 50 usually means expansion.";
    }
    if (numeric < 50) {
      return "Below 50 usually means contraction.";
    }
    return "A reading of 50 usually means flat activity.";
  }

  if (/70-city|home price|housing price|price index/.test(text) && /m\/m/i.test(value) && typeof numeric === "number") {
    if (numeric > 100) {
      return "Above 100 means prices rose month to month.";
    }
    if (numeric < 100) {
      return "Below 100 means prices fell month to month.";
    }
    return "A reading of 100 means prices were flat month to month.";
  }

  if (/(cpi|ppi)/.test(text) && typeof numeric === "number" && /%/.test(value)) {
    if (numeric < 0) {
      return "Negative means prices were lower than a year earlier.";
    }
    if (numeric > 0) {
      return "Positive means prices were higher than a year earlier.";
    }
    return "A zero reading means no price change from a year earlier.";
  }

  if (/unemployment/.test(text) && typeof numeric === "number") {
    return numeric > 5.5
      ? "Elevated unemployment signals weak labor demand."
      : "Lower unemployment is positive, but check hours worked for hidden slack.";
  }

  if (/real interest rate/.test(text)) {
    return "This is a level (LPR minus CPI), not a change — higher means tighter real monetary conditions.";
  }

  if (/lpr|rrr|reverse repo|mlf|liquidity operations/.test(text)) {
    return "This is a policy setting, not a growth rate.";
  }

  if (/usd\/cny|offshore cnh/.test(text)) {
    return typeof numeric === "number" && numeric > 7.2
      ? "Elevated — a weaker yuan signals capital-flow pressure or deliberate easing."
      : "A lower reading means a stronger yuan; higher means weaker.";
  }

  if (/stock connect/.test(text)) {
    return "Positive means net buying; negative means net selling.";
  }

  if (/fx reserves/.test(text)) {
    return "This is the stock of reserves rather than a spending flow.";
  }

  if (/exports|imports|trade balance/.test(text)) {
    const growthMatch = normalizeText(liveMetric?.secondary || "").match(/([\d.]+)%\s*y\/y/i);
    const growthRate = growthMatch ? Number(growthMatch[1]) : null;
    if (growthRate !== null && growthRate > 15) {
      return "Unusually strong — check for tariff front-loading before reading as durable demand. RMB-denominated.";
    }
    return "Trade values move with both volume and prices. These are RMB-denominated.";
  }

  if (/completions/.test(text)) {
    return "Completions matter because they show delivery, not just plans.";
  }

  if (/^household loans$/i.test(text.trim())) {
    const liveVal = normalizeText(liveMetric?.value || "");
    if (/^-/.test(liveVal)) {
      return "Negative household borrowing means consumers are deleveraging in aggregate — a sign of weak confidence.";
    }
    return "This shows where new financing is actually landing.";
  }

  if (/corporate medium\/long-term loans|government bond financing/.test(text)) {
    return "This shows where new financing is actually landing.";
  }

  if (/^retail sales$/i.test(text.trim())) {
    return "This is nominal growth — subtract CPI to approximate real consumer spending.";
  }

  if (/industrial profits/.test(text) && !/sector|margin/.test(text)) {
    return "When profit growth far exceeds revenue growth, suspect base effects or one-off cost savings rather than genuine margin expansion.";
  }

  if (/^business revenue$/i.test(text.trim())) {
    return "Compare with profit growth — a large gap signals base effects or cost compression, not durable margin gains.";
  }

  if (/private fixed-asset investment/.test(text)) {
    return "Private investment contracting while total FAI grows signals state-led substitution, not organic recovery.";
  }

  if (/capacity utilization/.test(text) && typeof numeric === "number") {
    return numeric < 74
      ? "Below 74% signals meaningful excess capacity across industry."
      : "Capacity utilization is within normal range.";
  }

  if (/pmi export orders/.test(text) && typeof numeric === "number") {
    return numeric < 50
      ? "Below 50 signals export-order contraction — check against actual export growth for front-loading."
      : "Above 50 signals export-order expansion.";
  }

  if (/^real retail sales/i.test(text)) {
    return "This is retail sales deflated by CPI \u2014 a cleaner read on real consumer spending.";
  }

  if (/^real disposable income/i.test(text)) {
    return "Nominal per capita income growth minus CPI \u2014 shows real purchasing power.";
  }

  if (/^real credit growth/i.test(text)) {
    return "TSF stock growth minus GDP deflator \u2014 real pace of credit expansion.";
  }

  if (/current account.*% of gdp/i.test(text)) {
    return "A large surplus relative to GDP suggests weak domestic absorption.";
  }

  if (/^fiscal impulse/i.test(text)) {
    return "The fiscal deficit-to-GDP ratio \u2014 rising means fiscal stance is loosening.";
  }

  if (/^household savings rate/i.test(text)) {
    return "Higher savings rate often signals precautionary behavior rather than strength.";
  }

  if (/labor productivity/i.test(text)) {
    return "GDP per employed person \u2014 an annual structural indicator of efficiency.";
  }

  if (/private enterprise profit/i.test(text)) {
    return "Compare with state-holding enterprise profits to gauge private-sector health.";
  }

  if (/state-holding enterprise profit/i.test(text)) {
    return "Compare with private enterprise profits to see the ownership divergence.";
  }

  if (/services share.*gdp/i.test(text)) {
    return "Rising services share usually signals structural rebalancing toward consumption.";
  }

  if (/services value.*added/i.test(text)) {
    return "Tertiary sector growth \u2014 services are now over half of GDP.";
  }

  if (/contribution to gdp growth/i.test(text)) {
    return "Expenditure-side GDP decomposition \u2014 shows what drove growth.";
  }

  if (/terms of trade/i.test(text)) {
    return "Export prices divided by import prices \u2014 measures external purchasing power.";
  }

  return "";
}

function cycleToneCopy(tone, counts) {
  if (tone === "down") {
    return "under pressure";
  }
  if (tone === "up") {
    if (counts && counts.flat > 0) {
      return "showing pockets of improvement";
    }
    return "firming";
  }
  if (tone === "flat") {
    return "mostly stable";
  }
  if (tone === "update") {
    return "mostly current settings";
  }
  if (tone === "mixed" && counts) {
    if (counts.up > 0 && counts.down > 0) {
      return "sending mixed signals";
    }
  }
  return "mixed";
}

function cycleShortName(name) {
  return name.replace(/\s+cycle$/i, "");
}

function metricTrendPhrase(metric) {
  const trend = inferTrend(metric);
  if (trend.direction === "update" && trend.primary) {
    return `${metric.name} at ${trend.primary}`;
  }
  if (trend.primary && trend.primary !== trend.label) {
    return `${metric.name} ${trend.primary}`;
  }
  if (trend.direction === "mixed") {
    return `${metric.name} mixed`;
  }
  if (trend.direction === "unknown") {
    return `${metric.name} awaiting a cleaner signal`;
  }
  return `${metric.name} ${trend.label.toLowerCase()}`;
}

function collapsedMetricScore(metric) {
  let score = metricPriorityScore(metric);
  const trend = inferTrend(metric);
  const freshness = metricFreshness(metric).status;

  if (trend.basis === "snapshot") {
    score -= 220;
  }
  if (trend.direction === "unknown") {
    score -= 180;
  }
  if (["context", "missing", "stale"].includes(freshness)) {
    score -= 160;
  }
  if (
    trend.basis === "history" &&
    trend.history?.numericPoints?.length < 3 &&
    !hasExplicitChangeSignal(liveMetricText(metric))
  ) {
    score -= 60;
  }

  return score;
}

function readableCollapsedMetrics(metrics) {
  return metrics.filter((metric) => {
    const freshness = metricFreshness(metric).status;
    const trend = inferTrend(metric);
    if (["context", "missing", "stale"].includes(freshness)) {
      return false;
    }
    if (trend.basis === "snapshot" || trend.direction === "unknown") {
      return false;
    }
    return true;
  });
}

function collapsedLeadMetrics(payload, count = 3) {
  const primaryPool = payload.signalMetrics.length
    ? payload.signalMetrics
    : payload.structuralMetrics.length
      ? payload.structuralMetrics
      : payload.metrics.filter((metric) => metricFreshness(metric).status !== "missing");
  const fallbackPool = payload.metrics.filter((metric) => metricFreshness(metric).status !== "missing");
  const ranked = (metrics) =>
    [...metrics].sort((left, right) => collapsedMetricScore(right) - collapsedMetricScore(left));
  const picks = [];

  for (const metric of ranked(readableCollapsedMetrics(primaryPool))) {
    if (!picks.includes(metric)) {
      picks.push(metric);
    }
  }

  for (const metric of ranked(readableCollapsedMetrics(fallbackPool))) {
    if (!picks.includes(metric)) {
      picks.push(metric);
    }
  }

  for (const metric of ranked(fallbackPool)) {
    if (!picks.includes(metric) && inferTrend(metric).direction !== "unknown") {
      picks.push(metric);
    }
  }

  return picks.slice(0, count);
}

function cycleSummaryMetrics(payload, count = 4) {
  const leads = collapsedLeadMetrics(payload, count);
  if (leads.length) {
    return leads;
  }
  return (payload.signalMetrics.length ? payload.signalMetrics : payload.briefingMetrics).slice(0, count);
}

function cycleNarrative(payload) {
  const summary = summarizeCycle(cycleSummaryMetrics(payload, 4));
  const leadMetrics = collapsedLeadMetrics(payload, 3);
  const leaders = leadMetrics.map((metric) => metricTrendPhrase(metric));
  const cycleName = payload.cycle.name.replace(/\s+cycle$/i, "");
  const structuralLeadCount = leadMetrics.filter(
    (metric) => metricFreshness(metric).status === "structural"
  ).length;

  if (!leaders.length) {
    return `${cycleName} does not have a clean readable signal on the page yet.`;
  }

  const joined =
    leaders.length === 1
      ? leaders[0]
      : leaders.length === 2
        ? `${leaders[0]}, and ${leaders[1]}`
        : `${leaders[0]}, ${leaders[1]}, and ${leaders[2]}`;

  if (
    (!payload.signalMetrics.length && payload.structuralMetrics.length) ||
    structuralLeadCount >= Math.max(2, leadMetrics.length - 1)
  ) {
    return `${cycleName} is being read mainly through slower structural data right now. Main signals: ${joined}.`;
  }

  let toneText = cycleToneCopy(summary.tone, summary.counts);
  if (payload.cycle.id === "policy") {
    if (summary.tone === "down") {
      toneText = "tight relative to conditions";
    } else if (summary.tone === "up") {
      toneText = "easing";
    } else if (summary.tone === "mixed") {
      toneText = "in a mixed stance";
    }
  }

  return `${cycleName} is ${toneText} right now. Main signals: ${joined}.`;
}

function cycleScopeNote(payload) {
  const parts = [];
  if (payload.signalMetrics.length) {
    parts.push(`${payload.signalMetrics.length} current or recent`);
  } else if (payload.structuralMetrics.length) {
    parts.push(`${payload.structuralMetrics.length} structural`);
  }
  if (payload.structuralMetrics.length && payload.signalMetrics.length) {
    parts.push(`${payload.structuralMetrics.length} structural`);
  }
  if (payload.referenceMetrics.length) {
    parts.push(`${payload.referenceMetrics.length} reference-only`);
  }
  if (!parts.length) {
    return "This cycle does not have a clean set of parsed current readings yet.";
  }
  return `This cycle summary is driven by ${humanJoin(parts)} metrics, with the older context parked lower in the drilldown.`;
}

function metricPriorityScore(metric) {
  let score = 0;
  const freshness = metricFreshness(metric);
  if (metric.mvp) {
    score += 100;
  }
  if (liveMetricFor(metric)) {
    score += 30;
  }
  if (historyForMetric(metric).length > 1) {
    score += 14;
  }

  if (freshness.status === "current") {
    score += 36;
  } else if (freshness.status === "aging") {
    score += 18;
  } else if (freshness.status === "structural") {
    score -= 18;
  } else if (freshness.status === "stale") {
    score -= 70;
  } else if (freshness.status === "context") {
    score -= 52;
  } else if (freshness.status === "missing") {
    score -= 90;
  }

  const trend = inferTrend(metric);
  if (trend.direction === "up" || trend.direction === "down") {
    score += 12;
  }
  if (trend.direction === "mixed") {
    score += 6;
  }
  if (trend.direction === "update") {
    score += 4;
  }
  if (trend.basis === "snapshot") {
    score -= 80;
  }
  if (trend.direction === "unknown") {
    score -= 90;
  }
  if (
    trend.basis === "history" &&
    trend.history?.numericPoints?.length < 3 &&
    !hasExplicitChangeSignal(liveMetricText(metric))
  ) {
    score -= 24;
  }

  return score;
}

function rankMetrics(metrics) {
  return [...metrics].sort((left, right) => {
    const scoreGap = metricPriorityScore(right) - metricPriorityScore(left);
    if (scoreGap !== 0) {
      return scoreGap;
    }
    return left.name.localeCompare(right.name);
  });
}

function summarizeCycle(metrics) {
  const usableMetrics = metrics.filter((metric) => {
    const trend = inferTrend(metric);
    return trend.direction !== "unknown" && trend.basis !== "snapshot";
  });
  const population = usableMetrics.length ? usableMetrics : metrics;
  const counts = {
    up: 0,
    down: 0,
    flat: 0,
    mixed: 0,
    update: 0,
    unknown: 0
  };

  for (const metric of population) {
    const rawDir = inferTrend(metric).direction;
    const dir = economicDirection(rawDir, metric.name);
    counts[dir] += 1;
  }

  let label = "Mixed";
  let tone = "mixed";

  if (counts.down >= 2 && counts.up === 0 && counts.down >= counts.flat) {
    label = "Under pressure";
    tone = "down";
  } else if (counts.up >= 2 && counts.down === 0 && counts.up >= counts.flat) {
    label = "Firming";
    tone = "up";
  } else if (counts.flat >= Math.max(counts.up, counts.down, 2)) {
    label = "Stable";
    tone = "flat";
  } else if (counts.update >= Math.max(counts.up, counts.down, 2) && counts.up + counts.down === 0) {
    label = "Settings";
    tone = "update";
  }

  const sentence = `${counts.down} down, ${counts.up} up, ${counts.flat} flat, ${counts.mixed + counts.update + counts.unknown} mixed or contextual.`;

  return {
    counts,
    label,
    tone,
    sentence,
    netSignal: counts.up - counts.down,
    populatedCount: population.length
  };
}

function sourceCoverageStats() {
  const representedMetrics = allMetrics.filter((metric) => {
    const hasLiveMetric = Boolean(liveMetricFor(metric));
    const hasLiveContext = latestSnapshotsForMetric(metric).length > 0;
    return hasLiveMetric || hasLiveContext;
  });

  const officialRepresented = representedMetrics.filter((metric) => {
    const liveMetric = liveMetricFor(metric);
    if (liveMetric?.sourceId && sourceById.has(liveMetric.sourceId)) {
      return sourceById.get(liveMetric.sourceId)?.type === "official";
    }

    const snapshotItem = latestSnapshotsForMetric(metric)[0];
    if (snapshotItem?.sourceId && sourceById.has(snapshotItem.sourceId)) {
      return sourceById.get(snapshotItem.sourceId)?.type === "official";
    }

    const source = primarySourceForMetric(metric);
    return source?.type === "official";
  });

  return {
    representedMetrics: representedMetrics.length,
    officialRepresented: officialRepresented.length
  };
}

function confidenceLabel() {
  const { representedMetrics, officialRepresented } = sourceCoverageStats();
  const share = officialRepresented / Math.max(representedMetrics, 1);
  if (share >= 0.82) {
    return {
      label: "High",
      detail: "Most visible metrics are being driven by official releases rather than fallbacks."
    };
  }
  if (share >= 0.6) {
    return {
      label: "Moderate",
      detail: "The main story is still mostly official-source, but some sections lean on proxies or market fallbacks."
    };
  }
  return {
    label: "Mixed",
    detail: "A larger share of the current view depends on fallbacks, proxies, or partial parsing."
  };
}

function cycleStoryLeaders(cyclePayloads) {
  return cyclePayloads
    .map((payload) => {
      const summary = summarizeCycle(cycleSummaryMetrics(payload, 4));
      return {
        cycle: payload.cycle,
        summary,
        score: summary.netSignal
      };
    })
    .sort((left, right) => Math.abs(right.score) - Math.abs(left.score));
}

function buildTopline(cyclePayloads) {
  const stories = cycleStoryLeaders(cyclePayloads);
  const weak = stories
    .filter((item) => item.summary.tone === "down")
    .slice(0, 2)
    .map((item) => cycleShortName(item.cycle.name).toLowerCase());
  const firm = stories
    .filter((item) => item.summary.tone === "up")
    .slice(0, 2)
    .map((item) => cycleShortName(item.cycle.name).toLowerCase());
  const flat = stories
    .filter((item) => item.summary.tone === "flat")
    .slice(0, 1)
    .map((item) => cycleShortName(item.cycle.name).toLowerCase());

  if (weak.length && firm.length) {
    return `${humanJoin(weak)} remain the main weak spots, while ${humanJoin(firm)} look firmer.`;
  }

  if (weak.length) {
    return `${humanJoin(weak)} remain the clearest pressure points in the dashboard.`;
  }

  if (firm.length) {
    return `${humanJoin(firm)} are the clearest improving parts of the dashboard right now.`;
  }

  if (flat.length) {
    return `${humanJoin(flat)} look broadly stable, while the rest of the dashboard is mixed.`;
  }

  return "The dashboard is mixed right now, with no single cycle fully dominating the picture.";
}

function renderCycleMeter(summary) {
  const total =
    summary.counts.up +
    summary.counts.down +
    summary.counts.flat +
    summary.counts.mixed +
    summary.counts.update +
    summary.counts.unknown;

  const segments = [
    ["down", summary.counts.down],
    ["up", summary.counts.up],
    ["flat", summary.counts.flat],
    ["mixed", summary.counts.mixed + summary.counts.unknown],
    ["update", summary.counts.update]
  ].filter(([, count]) => count > 0);

  return `
    <div class="cycle-meter">
      <div class="cycle-meter-bar">
        ${segments
          .map(
            ([tone, count]) =>
              `<span class="cycle-meter-segment cycle-meter-segment--${escapeHtml(tone)}" style="width: ${(count / Math.max(total, 1)) * 100}%"></span>`
          )
          .join("")}
      </div>
      <div class="cycle-meter-legend">
        ${segments
          .map(
            ([tone, count]) =>
              `<span class="cycle-meter-item"><i class="meter-dot meter-dot--${escapeHtml(tone)}"></i>${escapeHtml(String(count))} ${escapeHtml(tone)}</span>`
          )
          .join("")}
      </div>
    </div>
  `;
}

function standoutMetrics(cyclePayloads) {
  const ranked = cyclePayloads
    .flatMap((payload) =>
      (payload.signalMetrics.length ? payload.signalMetrics : payload.briefingMetrics).map((metric) => ({
        cycle: payload.cycle,
        metric,
        trend: inferTrend(metric),
        score: collapsedMetricScore(metric)
      }))
    )
    .filter(
      ({ metric, trend }) =>
        !["unknown"].includes(trend.direction) &&
        trend.basis !== "snapshot" &&
        !["context", "missing", "stale"].includes(metricFreshness(metric).status)
    )
    .sort((left, right) => {
      const directionScore = (item) =>
        item.trend.direction === "down" || item.trend.direction === "up"
          ? 2
          : item.trend.direction === "flat"
            ? 1
            : 0;
      const gap = directionScore(right) - directionScore(left);
      if (gap !== 0) {
        return gap;
      }
      return right.score - left.score;
    });

  const cycleCounts = new Map();
  const diverse = [];
  // First pass: max 1 per cycle to ensure diversity in the top 5
  for (const item of ranked) {
    const cid = item.cycle.id;
    if (!cycleCounts.has(cid)) {
      diverse.push(item);
      cycleCounts.set(cid, 1);
    }
    if (diverse.length >= 5) break;
  }
  // Second pass: allow a second pick per cycle for slots 6-8
  for (const item of ranked) {
    if (diverse.includes(item)) continue;
    const cid = item.cycle.id;
    const count = cycleCounts.get(cid) || 0;
    if (count < 2) {
      diverse.push(item);
      cycleCounts.set(cid, count + 1);
    }
    if (diverse.length >= 8) break;
  }
  return diverse;
}

function renderSummary(cyclePayloads) {
  if (!summaryPanel) {
    return;
  }

  const { representedMetrics, officialRepresented } = sourceCoverageStats();
  const refreshedAt = formatTimestamp(snapshot.generatedAt);
  const confidence = confidenceLabel();
  const topline = buildTopline(cyclePayloads);
  const leadEvidence = standoutMetrics(cyclePayloads).slice(0, 3);
  const currentSignalCount = cyclePayloads.reduce(
    (total, payload) => total + payload.signalMetrics.length,
    0
  );
  const structuralCount = cyclePayloads.reduce(
    (total, payload) => total + payload.structuralMetrics.length,
    0
  );
  const referenceCount = cyclePayloads.reduce(
    (total, payload) => total + payload.referenceMetrics.length,
    0
  );

  summaryPanel.innerHTML = `
    <p class="summary-kicker">Main takeaway</p>
    <h2>${escapeHtml(topline)}</h2>
    <p class="summary-copy">
      Read the page as a briefing, not a spreadsheet. Current or recent signals shape the story;
      structural annual data and older reference releases are still on-page, but they are tagged
      separately so they do not distort the headline read.
    </p>
    <div class="summary-brief">
      ${leadEvidence
        .map(({ cycle, metric, trend }) => {
          const reading = trend.primary || liveMetricFor(metric)?.value || "Release context";
          return `
            <div class="summary-brief-item">
              <strong>${escapeHtml(metric.name)}</strong>
              <span>${escapeHtml(reading)} · ${escapeHtml(cycleShortName(cycle.name))}</span>
            </div>
          `;
        })
        .join("")}
    </div>
    <div class="summary-grid">
      <div class="summary-stat">
        <strong>${escapeHtml(confidence.label)}</strong>
        <span>data confidence</span>
      </div>
      <div class="summary-stat">
        <strong>${officialRepresented}</strong>
        <span>official-led metrics</span>
      </div>
      <div class="summary-stat">
        <strong>${currentSignalCount}</strong>
        <span>current or recent signals</span>
      </div>
      <div class="summary-stat">
        <strong>${structuralCount + referenceCount}</strong>
        <span>background or reference series</span>
      </div>
    </div>
    <p class="summary-stamp">
      Snapshot refreshed ${escapeHtml(refreshedAt || "recently")}. ${escapeHtml(
        confidence.detail
      )} ${escapeHtml(
        `${representedMetrics} populated metrics remain available in the appendix and cycle drilldowns, including ${structuralCount} structural series and ${referenceCount} reference-only items.`
      )}
    </p>
  `;
}

function renderInsights(cyclePayloads) {
  const items = standoutMetrics(cyclePayloads).slice(0, 5);

  insightGrid.innerHTML = items.length
    ? items
        .map(({ cycle, metric, trend }, index) => {
          const liveMetric = liveMetricFor(metric);
          return `
            <article class="insight-card" data-direction="${escapeHtml(trend.direction)}">
              <div class="insight-top">
                <span class="detail-chip">Takeaway ${String(index + 1).padStart(2, "0")}</span>
                <span class="trend-pill trend-pill--${escapeHtml(trend.direction)}">${escapeHtml(trend.label)}</span>
              </div>
              <h3>${escapeHtml(metric.name)}</h3>
              <p class="insight-reading">${escapeHtml(trend.primary || liveMetric?.value || "Release context")}</p>
              <p class="insight-copy">${escapeHtml(trend.summary)}</p>
              ${
                trend.secondary
                  ? `<p class="insight-subreading">${escapeHtml(trend.secondary)}</p>`
                  : ""
              }
              ${
                specialInterpretation(metric) || friendlyMetricDescription(metric, cycle)
                  ? `<p class="insight-meaning"><strong>${escapeHtml(
                      cycleShortName(cycle.name)
                    )}:</strong> ${escapeHtml(
                      specialInterpretation(metric) || friendlyMetricDescription(metric, cycle)
                    )}</p>`
                  : ""
              }
            </article>
          `;
        })
        .join("")
    : '<div class="empty-state">No standout metrics match the current filters.</div>';
}

function renderMiniSparkline(metric) {
  const trend = inferTrend(metric);
  if (!trend.history) {
    return '<div class="mini-sparkline mini-sparkline--empty">No 1Y chart</div>';
  }

  const geometry = sparklineGeometry(trend.history.numericPoints, 150, 34);
  if (!geometry) {
    return '<div class="mini-sparkline mini-sparkline--empty">No 1Y chart</div>';
  }

  const areaPath = `${geometry.line} L ${geometry.width.toFixed(2)} ${geometry.height.toFixed(2)} L 0 ${geometry.height.toFixed(2)} Z`;
  const dir = escapeHtml(trend.direction);
  const gradId = `spark-grad-${dir}`;

  return `
    <div class="mini-sparkline mini-sparkline--${dir}">
      <svg viewBox="0 0 ${geometry.width} ${geometry.height}" aria-hidden="true">
        <defs>
          <linearGradient id="${gradId}" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" class="sparkline-grad-stop" />
            <stop offset="100%" stop-color="transparent" />
          </linearGradient>
        </defs>
        <path class="sparkline-area" d="${areaPath}" fill="url(#${gradId})" />
        <path d="${geometry.line}"></path>
      </svg>
      <span>${escapeHtml(historyPeriodLabel(trend.history.earliest))} to ${escapeHtml(
        historyPeriodLabel(trend.history.latest)
      )}</span>
    </div>
  `;
}

function renderMetricCurrent(metric) {
  const liveMetric = liveMetricFor(metric);
  if (liveMetric) {
    return `
      <div class="metric-current">
        <span class="metric-current-label">Now</span>
        <strong>${escapeHtml(liveMetric.value)}</strong>
        <span>${escapeHtml(cleanPeriodLabel(liveMetric.period, liveMetric.date) || formatDate(liveMetric.date))}</span>
      </div>
    `;
  }

  const snapshots = latestSnapshotsForMetric(metric);
  if (snapshots.length) {
    return `
      <div class="metric-current">
        <span class="metric-current-label">Now</span>
        <strong>Release context</strong>
        <span>${escapeHtml(formatDate(snapshots[0].date))}</span>
      </div>
    `;
  }

  return `
    <div class="metric-current">
      <span class="metric-current-label">Now</span>
      <strong>Source only</strong>
      <span>No parsed value</span>
    </div>
  `;
}

function renderMetricDetail(metric, cycle) {
  const liveMetric = liveMetricFor(metric);
  const snapshots = latestSnapshotsForMetric(metric);
  const source = primarySourceForMetric(metric);
  const trend = inferTrend(metric);
  const history = historyForMetric(metric);
  const description = friendlyMetricDescription(metric, cycle);
  const freshness = metricFreshness(metric);

  return `
    <div class="metric-detail">
      <p class="metric-detail-lead">${escapeHtml(description)}</p>
      <p class="metric-detail-freshness metric-detail-freshness--${escapeHtml(
        freshness.status
      )}">${escapeHtml(freshness.detail)}</p>
      <p class="metric-detail-copy">${escapeHtml(trend.detail)}</p>
      ${
        liveMetric?.secondary
          ? `<p class="metric-detail-raw"><strong>Latest release text:</strong> ${escapeHtml(liveMetric.secondary)}</p>`
          : snapshots[0]
            ? `<p class="metric-detail-raw"><strong>Release note:</strong> ${escapeHtml(
                snapshots[0].highlights?.[0] || snapshots[0].summary
              )}</p>`
            : ""
      }
      <div class="metric-detail-meta">
        <span class="detail-chip">${escapeHtml(metric.cadence)}</span>
        <span class="detail-chip detail-chip--${escapeHtml(freshness.status)}">${escapeHtml(
          freshness.label
        )}</span>
        <span class="detail-chip">${escapeHtml(trend.basis === "history" ? "Based on 1Y history" : trend.basis === "release" ? "Based on latest release" : trend.basis === "snapshot" ? "Based on release context" : "Source configured")}</span>
        ${metric.mvp ? '<span class="detail-chip detail-chip--mvp">Key signal</span>' : ""}
        ${
          source
            ? `<a class="detail-chip detail-chip--link" href="${source.url}" target="_blank" rel="noreferrer">${escapeHtml(source.owner)}</a>`
            : ""
        }
      </div>
      ${
        history.length > 1
          ? `
            <details class="history-detail">
              <summary>Open full 1Y history</summary>
              <div class="table-wrap">
                <table class="data-table history-table">
                  <thead>
                    <tr>
                      <th>Period</th>
                      <th>Value</th>
                      <th>Note</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${history
                      .map(
                        (point) => `
                          <tr>
                            <td>${escapeHtml(historyPeriodLabel(point))}</td>
                            <td>${escapeHtml(point.value)}</td>
                            <td>${escapeHtml(point.secondary || "")}</td>
                          </tr>
                        `
                      )
                      .join("")}
                  </tbody>
                </table>
              </div>
            </details>
          `
          : ""
      }
    </div>
  `;
}

function renderMetricRow(metric, cycle, index) {
  const trend = inferTrend(metric);
  const description = friendlyMetricDescription(metric, cycle);
  const interpretation = specialInterpretation(metric);
  const freshness = metricFreshness(metric);
  const magnitude = trendMagnitude(trend);
  const displayDirection = economicDirection(trend.direction, metric.name);

  return `
    <details class="metric-row ${index < 4 ? "is-priority" : ""}" data-direction="${escapeHtml(displayDirection)}" data-freshness="${escapeHtml(freshness.status)}" style="--mag: ${magnitude}">
      <summary>
        <div class="metric-name-block">
          <div class="metric-name-top">
            <h4>${escapeHtml(metric.name)}</h4>
            <div class="metric-name-tags">
              ${metric.mvp ? '<span class="mini-chip mini-chip--mvp">Key</span>' : ""}
              <span class="mini-chip mini-chip--${escapeHtml(freshness.status)}">${escapeHtml(
                freshness.label
              )}</span>
            </div>
          </div>
          <p>${escapeHtml(description)}</p>
        </div>
        ${renderMetricCurrent(metric)}
        <div class="metric-trend-block">
          <div class="metric-trend-top">
            <span class="trend-value trend-value--${escapeHtml(trend.direction)}">${escapeHtml(trend.primary || trend.label)}</span>
            <span class="trend-pill trend-pill--${escapeHtml(trend.direction)}">${escapeHtml(trend.label)}</span>
          </div>
          <p>${escapeHtml(trend.summary)}</p>
          ${
            trend.secondary
              ? `<p class="metric-trend-secondary">${escapeHtml(trend.secondary)}</p>`
              : ""
          }
          ${
            interpretation
              ? `<p class="metric-trend-note">${escapeHtml(interpretation)}</p>`
              : ""
          }
          ${renderMomentumBadge(metric)}
        </div>
        <div class="metric-chart-block">
          ${renderMiniSparkline(metric)}
        </div>
      </summary>
      ${renderMetricDetail(metric, cycle)}
    </details>
  `;
}

function renderMomentumBadge(metric) {
  const liveMetric = liveMetricFor(metric);
  const momentum = liveMetric?.momentum;
  if (!momentum || momentum.direction === "stable") {
    return "";
  }
  const icon = momentum.direction === "accelerating" ? "\u25B2\u25B2" : "\u25BC\u25BC";
  const cls = momentum.direction === "accelerating" ? "momentum-badge--accelerating" : "momentum-badge--decelerating";
  const label = momentum.direction === "accelerating" ? "Accelerating" : "Decelerating";
  return `<span class="momentum-badge ${cls}" title="${escapeHtml(momentum.delta)} vs prior period">${icon} ${escapeHtml(momentum.delta)} ${label}</span>`;
}

function renderPulseBoard(cyclePayloads) {
  signalGrid.innerHTML = cyclePayloads
    .map((payload) => {
      const summary = summarizeCycle(cycleSummaryMetrics(payload, 4));
      const keyMetrics = collapsedLeadMetrics(payload, 3);
      const narrative = cycleNarrative(payload);

      return `
        <article class="pulse-card pulse-card--${escapeHtml(summary.tone)}">
          <div class="heatmap-top">
            <div>
              <p class="pulse-kicker">${escapeHtml(payload.cycle.name)}</p>
              <h3>${escapeHtml(summary.label)}</h3>
            </div>
          </div>
          <p class="pulse-copy">${escapeHtml(narrative)}</p>
          ${renderCycleMeter(summary)}
          <p class="pulse-scope">${escapeHtml(cycleScopeNote(payload))}</p>
          <div class="pulse-metric-list">
            ${keyMetrics
              .map((metric) => {
                const trend = inferTrend(metric);
                const liveMetric = liveMetricFor(metric);
                return `
                  <div class="pulse-metric">
                    <div class="pulse-metric-copy">
                      <strong>${escapeHtml(metric.name)}</strong>
                      <span>${escapeHtml(trend.primary || liveMetric?.value || trend.summary)}</span>
                    </div>
                    <span class="trend-pill trend-pill--${escapeHtml(trend.direction)}">${escapeHtml(trend.label)}</span>
                  </div>
                `;
              })
              .join("")}
          </div>
        </article>
      `;
    })
    .join("");
}

function renderCycleNav(cyclePayloads) {
  if (!cycleNav) {
    return;
  }

  cycleNav.innerHTML = cyclePayloads
    .map((payload, index) => {
      const summary = summarizeCycle(cycleSummaryMetrics(payload, 4));
      return `
        <a class="cycle-nav-chip" href="#cycle-${escapeHtml(payload.cycle.id)}">
          <span class="cycle-nav-index">${String(index + 1).padStart(2, "0")}</span>
          <span class="cycle-nav-name">${escapeHtml(payload.cycle.name)}</span>
          <span class="trend-pill trend-pill--${escapeHtml(summary.tone)}">${escapeHtml(summary.label)}</span>
        </a>
      `;
    })
    .join("");
}

function renderMetricList(metrics, cycle, { startIndex = 0, highlightTop = false } = {}) {
  if (!metrics.length) {
    return "";
  }

  return `
    <div class="metric-list">
      <div class="metric-list-head">
        <span>Metric</span>
        <span>Latest reading</span>
        <span>Direction</span>
        <span>1Y view</span>
      </div>
      ${metrics
        .map((metric, index) =>
          renderMetricRow(metric, cycle, highlightTop ? startIndex + index : 99 + startIndex + index)
        )
        .join("")}
    </div>
  `;
}

function renderMetricGroup(title, description, metrics, cycle, options = {}) {
  if (!metrics.length) {
    return "";
  }

  return `
    <section class="metric-group metric-group--${escapeHtml(options.tone || "default")}">
      <div class="metric-group-head">
        <div>
          <h5>${escapeHtml(title)}</h5>
          <p>${escapeHtml(description)}</p>
        </div>
        <span class="source-count">${metrics.length} metrics</span>
      </div>
      ${renderMetricList(metrics, cycle, {
        startIndex: options.startIndex || 0,
        highlightTop: Boolean(options.highlightTop)
      })}
    </section>
  `;
}

function renderCycles(cyclePayloads) {
  const cards = cyclePayloads.map((payload, index) => {
    const keyMetrics = collapsedLeadMetrics(payload, 3);
    const leadQuestion =
      payload.cycle.whatMatters[0] || `How should this cycle be read right now?`;
    const signalDescription = payload.signalMetrics.length
      ? "These are the freshest signals and the only ones used to drive the main briefing."
      : "This cycle does not have enough fresh monthly signals right now, so the best available structural context is shown first.";
    const isOpen = false;
    const cardId = `cycle-card-${payload.cycle.id}`;

    const signalDirs = payload.signalMetrics.map((m) => economicDirection(inferTrend(m).direction, m.name));
    const upCount = signalDirs.filter((d) => d === "up").length;
    const downCount = signalDirs.filter((d) => d === "down").length;
    const dominantDirection = signalDirs.length === 0
      ? "flat"
      : upCount > 0 && downCount > 0
        ? "mixed"
        : downCount > upCount
          ? "down"
          : upCount > downCount
            ? "up"
            : "flat";

    return `
      <section class="cycle-panel" id="cycle-${escapeHtml(payload.cycle.id)}">
        <header class="cycle-panel-heading">
          <div class="cycle-panel-heading-copy">
            <p class="cycle-panel-index">Cycle ${String(index + 1).padStart(2, "0")}</p>
            <h3 class="cycle-panel-name"><span class="cycle-dot cycle-dot--${escapeHtml(dominantDirection)}"></span>${escapeHtml(cycleShortName(payload.cycle.name))}</h3>
            <button
              class="cycle-expand-link"
              type="button"
              data-cycle-toggle="${escapeHtml(cardId)}"
              aria-controls="${escapeHtml(cardId)}"
              aria-expanded="${isOpen ? "true" : "false"}"
            >
              ${isOpen ? "Collapse section" : "Expand section"}
            </button>
          </div>
        </header>
        <details class="cycle-card cycle-accordion" id="${escapeHtml(cardId)}" ${isOpen ? "open" : ""}>
          <summary class="cycle-summary">
            <div class="cycle-header-copy">
              <p class="cycle-description">${escapeHtml(payload.cycle.description)}</p>
              <p class="cycle-narrative"><strong>Current read:</strong> ${escapeHtml(
                cycleNarrative(payload)
              )}</p>
            </div>

            <div class="cycle-highlight-strip">
              ${keyMetrics
                .map((metric) => {
                  const trend = inferTrend(metric);
                  return `
                    <div class="cycle-highlight">
                      <span class="cycle-highlight-name">${escapeHtml(metric.name)}</span>
                      <strong>${escapeHtml(trend.primary || liveMetricFor(metric)?.value || trend.label)}</strong>
                      <span>${escapeHtml(trend.summary)}</span>
                    </div>
                  `;
                })
                .join("")}
            </div>
          </summary>

          <div class="cycle-body">
            <div class="cycle-metric-block">
              <div class="cycle-block-head">
                <h4>Essential metrics</h4>
                <p>Current first, then structural context, then older reference items.</p>
              </div>
              ${renderMetricGroup(
                payload.signalMetrics.length ? "Current" : "Best available context",
                signalDescription,
                payload.signalMetrics.length ? payload.signalMetrics : payload.briefingMetrics,
                payload.cycle,
                { highlightTop: true, startIndex: 0, tone: "signals" }
              )}
              ${renderMetricGroup(
                "Structural",
                "Useful background for the longer-run picture. These are valid data points, but they move too slowly to drive the live monthly story.",
                payload.structuralMetrics,
                payload.cycle,
                {
                  highlightTop: false,
                  startIndex: payload.signalMetrics.length || payload.briefingMetrics.length,
                  tone: "structural"
                }
              )}
              ${renderMetricGroup(
                "Reference",
                "Kept visible for transparency, but not used to shape the headline narrative because the reading is stale, context-only, or missing a clean parsed value.",
                payload.referenceMetrics,
                payload.cycle,
                {
                  highlightTop: false,
                  startIndex:
                    (payload.signalMetrics.length || payload.briefingMetrics.length) +
                    payload.structuralMetrics.length,
                  tone: "reference"
                }
              )}
            </div>
          </div>
        </details>
      </section>
    `;
  });

  cyclesGrid.innerHTML = cards.join("");
  emptyState.classList.toggle("hidden", cards.length > 0);

  const syncToggle = (panel) => {
    const details = panel.querySelector(".cycle-accordion");
    const button = panel.querySelector(".cycle-expand-link");
    if (!details || !button) {
      return;
    }

    const isOpen = details.open;
    button.textContent = isOpen ? "Collapse section" : "Expand section";
    button.setAttribute("aria-expanded", isOpen ? "true" : "false");
  };

  cyclesGrid.querySelectorAll(".cycle-panel").forEach((panel) => {
    const details = panel.querySelector(".cycle-accordion");
    const button = panel.querySelector(".cycle-expand-link");
    if (!details || !button) {
      return;
    }

    syncToggle(panel);
    button.addEventListener("click", () => {
      details.open = !details.open;
      syncToggle(panel);
    });
    details.addEventListener("toggle", () => syncToggle(panel));
  });
}

function renderSources() {
  const sortedSources = [...data.sources].sort((left, right) => {
    if (left.type !== right.type) {
      return left.type === "official" ? -1 : 1;
    }
    return left.name.localeCompare(right.name);
  });

  sourceGrid.innerHTML = sortedSources
    .map((source) => {
      const latestRelease = latestSnapshotsForSourceId(source.id)[0];
      const linkedMetrics = allMetrics.filter((metric) => metric.sourceIds.includes(source.id)).length;
      return `
        <article class="source-card">
          <div class="source-card-top">
            <span class="source-type source-type--${escapeHtml(source.type)}">${escapeHtml(source.type)}</span>
            <span class="source-count">${linkedMetrics} metrics</span>
          </div>
          <h3>${escapeHtml(source.name)}</h3>
          <p class="source-description">${escapeHtml(source.note)}</p>
          <p class="source-status">
            ${
              latestRelease
                ? `Latest pulled: ${escapeHtml(formatDate(latestRelease.date))}`
                : "No pulled snapshot loaded yet."
            }
          </p>
          <a href="${source.url}" target="_blank" rel="noreferrer">Open source</a>
        </article>
      `;
    })
    .join("");
}

function renderSnapshotNotes() {
  const notes = snapshot.notes || [];
  snapshotNotes.innerHTML = notes.length
    ? notes.map((note) => `<div class="snapshot-note">${escapeHtml(note)}</div>`).join("")
    : '<div class="snapshot-note">No active parsing caveats are attached to this snapshot.</div>';
}

function renderTable(table) {
  return `
    <div class="live-table-block">
      <h4>${escapeHtml(table.title)}</h4>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              ${table.headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("")}
            </tr>
          </thead>
          <tbody>
            ${table.rows
              .map(
                (row) => `
                  <tr>
                    ${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}
                  </tr>
                `
              )
              .join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function renderLiveSources() {
  const items = [...(snapshot.sourceSnapshots || [])].sort((left, right) =>
    String(right.date).localeCompare(String(left.date))
  );

  liveSourceList.innerHTML = items
    .map((item, index) => {
      const source = sourceById.get(item.sourceId);
      const tableCount = item.tables?.length || 0;
      return `
        <article class="live-source-card">
          <details ${index === 0 ? "open" : ""}>
            <summary>
              <div>
                <p class="live-source-kicker">${escapeHtml(source?.owner || "Source")}</p>
                <h3>${escapeHtml(item.title)}</h3>
                <p class="live-source-summary">${escapeHtml(item.summary)}</p>
              </div>
              <span class="source-count">${tableCount ? `${tableCount} tables` : "text"}</span>
            </summary>
            <div class="live-source-body">
              <div class="live-source-meta">
                <span class="detail-chip">${escapeHtml(formatDate(item.date))}</span>
                <a class="detail-chip detail-chip--link" href="${item.url}" target="_blank" rel="noreferrer">Open release</a>
              </div>
              <div class="highlight-list">
                ${(item.highlights || [])
                  .map((highlight) => `<div class="highlight-item">${escapeHtml(highlight)}</div>`)
                  .join("")}
              </div>
              ${(item.tables || []).map((table) => renderTable(table)).join("")}
            </div>
          </details>
        </article>
      `;
    })
    .join("");
}

function renderSynthesis(cyclePayloads) {
  if (!synthesisSection) return;

  const stories = cycleStoryLeaders(cyclePayloads);
  const weak = stories.filter((s) => s.summary.tone === "down");
  const firm = stories.filter((s) => s.summary.tone === "up");
  const mixed = stories.filter((s) => s.summary.tone === "mixed");

  const weakNames = weak.slice(0, 3).map((s) => cycleShortName(s.cycle.name).toLowerCase());
  const firmNames = firm.slice(0, 3).map((s) => cycleShortName(s.cycle.name).toLowerCase());

  const parts = [];
  if (weakNames.length) {
    parts.push(`<strong>${escapeHtml(humanJoin(weakNames))}</strong> ${weakNames.length === 1 ? "is" : "are"} under clear pressure`);
  }
  if (firmNames.length) {
    parts.push(`<strong>${escapeHtml(humanJoin(firmNames))}</strong> ${firmNames.length === 1 ? "shows" : "show"} improvement`);
  }
  if (mixed.length) {
    parts.push(`${mixed.length} cycle${mixed.length === 1 ? "" : "s"} ${mixed.length === 1 ? "is" : "are"} sending mixed signals`);
  }

  const topline = parts.length
    ? parts.join("; ") + "."
    : "The dashboard is mixed, with no single cycle dominating.";

  const downCount = weak.length;
  const upCount = firm.length;
  const mixedCount = mixed.length;
  const total = stories.length;
  const balanceLabel =
    downCount > upCount + 1
      ? "The weight of evidence leans negative."
      : upCount > downCount + 1
        ? "The weight of evidence leans positive."
        : "The balance of signals is roughly even \u2014 positive and negative forces are offsetting.";

  synthesisSection.innerHTML = `
    <div class="synthesis-card">
      <p class="synthesis-kicker">Cross-cycle bottom line</p>
      <p class="synthesis-topline">${topline}</p>
      <p class="synthesis-balance">${escapeHtml(balanceLabel)} Of ${total} cycles tracked, ${downCount} read negative, ${upCount} read positive, and ${mixedCount} are mixed.</p>
    </div>
  `;
}

function render() {
  const cyclePayloads = buildCyclePayloads();
  renderSummary(cyclePayloads);
  renderPulseBoard(cyclePayloads);
  renderInsights(cyclePayloads);
  renderSynthesis(cyclePayloads);
  renderCycleNav(cyclePayloads);
  renderCycles(cyclePayloads);
}

function attachEvents() {
  if (searchInput) {
    searchInput.addEventListener("input", (event) => {
      state.search = event.target.value.trim().toLowerCase();
      render();
    });
  }

  if (cadenceFilter) {
    cadenceFilter.addEventListener("change", (event) => {
      state.cadence = event.target.value;
      render();
    });
  }

  toggleButtons.forEach((button) => {
    button.addEventListener("click", () => {
      state.filterMode = button.dataset.filter;
      toggleButtons.forEach((candidate) =>
        candidate.classList.toggle("is-active", candidate === button)
      );
      render();
    });
  });
}

fillCadenceOptions();
renderSources();
renderLiveSources();
renderSnapshotNotes();
attachEvents();
render();
