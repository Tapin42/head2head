(function () {
  const config = window.HEAD2HEAD || {};
  let rows = (config.initialRows || []).map((row) => ({
    athlete: row.athlete,
    isBaseline: row.is_baseline,
    cells: row.cells,
  }));

  const body = document.getElementById("compare-body");
  const searchInput = document.getElementById("search");
  const searchResults = document.getElementById("search-results");
  const addForm = document.getElementById("add-athlete-form");
  const hiddenSplitsToggle = document.getElementById("toggle-hidden-splits");
  const compareGrid = document.getElementById("compare-grid");
  const columnGroups = config.columnGroups || [];
  const columnHiddenByDefault = config.columnHiddenByDefault || [];

  function formatDelta(seconds) {
    if (seconds == null) return "—";
    const sign = seconds > 0 ? "+" : seconds < 0 ? "-" : "";
    const value = Math.abs(seconds);
    const hours = Math.floor(value / 3600);
    const minutes = Math.floor((value % 3600) / 60);
    const secs = value % 60;
    if (hours) return `${sign}${hours}:${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
    return `${sign}${minutes}:${String(secs).padStart(2, "0")}`;
  }

  function deltaSign(text) {
    if (!text || text === "—") return "";
    if (text.startsWith("+")) return "positive";
    if (text.startsWith("-")) return "negative";
    return "";
  }

  function expandDisplayCells(cells, isBaseline) {
    const displayCells = [];
    cells.forEach((cell) => {
      displayCells.push({
        kind: "clock",
        value: cell.clock_time,
        seconds: cell.clock_seconds,
        delta: isBaseline ? null : cell.clock_delta,
        delta_seconds: isBaseline ? null : cell.clock_delta_seconds,
        hidden_by_default: Boolean(cell.hidden_by_default),
      });
      displayCells.push({
        kind: "leg",
        value: cell.leg_time,
        seconds: cell.leg_seconds,
        delta: isBaseline ? null : cell.leg_delta,
        delta_seconds: isBaseline ? null : cell.leg_delta_seconds,
        hidden_by_default: Boolean(cell.hidden_by_default),
      });
    });
    return displayCells;
  }

  function recomputeDeltas() {
    if (!rows.length) return;
    const baseline = rows[0];
    rows.forEach((row, index) => {
      row.isBaseline = index === 0;
      row.cells = row.cells.map((cell, cellIndex) => {
        const baseCell = baseline.cells[cellIndex] || {};
        if (row.isBaseline) {
          return {
            ...cell,
            clock_delta: null,
            leg_delta: null,
            clock_delta_seconds: null,
            leg_delta_seconds: null,
          };
        }
        const clockDelta =
          cell.clock_seconds != null && baseCell.clock_seconds != null
            ? cell.clock_seconds - baseCell.clock_seconds
            : null;
        const legDelta =
          cell.leg_seconds != null && baseCell.leg_seconds != null
            ? cell.leg_seconds - baseCell.leg_seconds
            : null;
        return {
          ...cell,
          clock_delta_seconds: clockDelta,
          leg_delta_seconds: legDelta,
          clock_delta: formatDelta(clockDelta),
          leg_delta: formatDelta(legDelta),
        };
      });
    });
  }

  function renderValueCell(cell) {
    const deltaHtml = cell.delta
      ? `<div class="delta" data-sign="${deltaSign(cell.delta)}">${cell.delta}</div>`
      : "";
    return `
      <td class="value-cell" data-kind="${cell.kind}" data-hidden-by-default="${cell.hidden_by_default ? "true" : "false"}">
        <div class="value">${cell.value || "—"}</div>
        ${deltaHtml}
      </td>`;
  }

  function renderRows() {
    recomputeDeltas();
    body.innerHTML = rows
      .map((row) => {
        const displayCells = expandDisplayCells(row.cells, row.isBaseline);
        return `
      <tr data-profile-id="${row.athlete.profile_id}" data-entry-id="${row.athlete.entry_id}" draggable="true">
        <th scope="row" class="athlete-col">
          <div class="athlete-cell">
            <div class="athlete-primary">
              <span class="drag-handle" aria-hidden="true">⋮⋮</span>
              <span class="athlete-name">${row.athlete.name}</span>
              ${row.athlete.bib ? `<span class="bib">#${row.athlete.bib}</span>` : ""}
            </div>
            ${row.isBaseline ? `<span class="baseline-badge">Baseline</span>` : ""}
          </div>
        </th>
        ${displayCells.map(renderValueCell).join("")}
      </tr>`;
      })
      .join("");
    bindDragAndDrop();
    syncUrl();
  }

  function syncUrl() {
    const params = new URLSearchParams();
    const pids = rows.map((row) => row.athlete.profile_id).join(",");
    if (pids) params.set("pids", pids);
    if (config.selectedCourse) params.set("course", config.selectedCourse);
    if (config.appId) params.set("appid", config.appId);
    if (config.sportstatsRid) params.set("rid", config.sportstatsRid);
    if (config.sportstatsSlug) params.set("slug", config.sportstatsSlug);
    const next = `${window.location.pathname}?${params.toString()}`;
    window.history.replaceState({}, "", next);
  }

  function bindDragAndDrop() {
    let draggedIndex = null;
    body.querySelectorAll("tr").forEach((rowEl, index) => {
      rowEl.addEventListener("dragstart", () => {
        draggedIndex = index;
        rowEl.classList.add("dragging");
      });
      rowEl.addEventListener("dragend", () => {
        rowEl.classList.remove("dragging");
        draggedIndex = null;
      });
      rowEl.addEventListener("dragover", (event) => event.preventDefault());
      rowEl.addEventListener("drop", (event) => {
        event.preventDefault();
        if (draggedIndex == null || draggedIndex === index) return;
        const moved = rows.splice(draggedIndex, 1)[0];
        rows.splice(index, 0, moved);
        renderRows();
      });
    });
  }

  async function fetchAthlete(profileId) {
    const params = new URLSearchParams({ pid: profileId });
    if (config.appId) params.set("appid", config.appId);
    if (config.selectedCourse) params.set("course", config.selectedCourse);
    if (config.sportstatsRid) params.set("rid", config.sportstatsRid);
    if (config.sportstatsSlug) params.set("slug", config.sportstatsSlug);
    const response = await fetch(`/api/athlete?${params.toString()}`);
    if (!response.ok) throw new Error("Could not load athlete");
    return response.json();
  }

  function isStartSegment(segmentId, label) {
    if ((segmentId || "").toUpperCase() === "START") return true;
    return (label || "").trim().toLowerCase() === "start";
  }

  function alignToColumns(splits) {
    const byId = Object.fromEntries(splits.map((split) => [split.segment_id, split]));
    return (config.columns || [])
      .map((segmentId, index) => {
        const label = (config.columnLabels || [])[index] || "";
        return { segmentId, label };
      })
      .filter(({ segmentId, label }) => !isStartSegment(segmentId, label))
      .map(({ segmentId }, index) => {
        const split = byId[segmentId];
        const hiddenByDefault = Boolean(columnHiddenByDefault[index]);
        if (!split) {
          return {
            clock_time: null,
            leg_time: null,
            clock_seconds: null,
            leg_seconds: null,
            hidden_by_default: hiddenByDefault,
          };
        }
        return {
          clock_time: split.clock_time,
          leg_time: split.leg_time,
          clock_seconds: split.clock_seconds,
          leg_seconds: split.leg_seconds,
          hidden_by_default: hiddenByDefault,
        };
      });
  }

  function bindHiddenSplitToggle() {
    if (!hiddenSplitsToggle || !compareGrid) return;
    const syncVisibility = () => {
      compareGrid.classList.toggle("show-hidden-splits", hiddenSplitsToggle.checked);
    };
    hiddenSplitsToggle.addEventListener("change", syncVisibility);
    syncVisibility();
  }

  async function addAthlete(profileId) {
    if (rows.some((row) => row.athlete.profile_id === profileId)) return;
    const payload = await fetchAthlete(profileId);
    rows.push({
      athlete: payload.athlete,
      isBaseline: false,
      cells: alignToColumns(payload.splits),
    });
    renderRows();
  }

  async function searchAthletes(query) {
    const params = new URLSearchParams({ q: query });
    if (config.appId) params.set("appid", config.appId);
    if (config.sportstatsRid) params.set("rid", config.sportstatsRid);
    if (config.sportstatsSlug) params.set("slug", config.sportstatsSlug);
    const response = await fetch(`/api/search?${params.toString()}`);
    if (!response.ok) return [];
    const payload = await response.json();
    return payload.results || [];
  }

  addForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const query = searchInput.value.trim();
    if (query.length < 2) return;
    const results = await searchAthletes(query);
    if (!results.length) {
      searchResults.hidden = false;
      searchResults.innerHTML = "<button type='button' disabled>No matches</button>";
      return;
    }
    if (results.length === 1) {
      await addAthlete(results[0].profile_id);
      searchInput.value = "";
      searchResults.hidden = true;
      return;
    }
    searchResults.hidden = false;
    searchResults.innerHTML = results
      .map(
        (result) =>
          `<button type="button" data-profile-id="${result.profile_id}">${result.name}${
            result.bib ? ` #${result.bib}` : ""
          }</button>`
      )
      .join("");
    searchResults.querySelectorAll("button[data-profile-id]").forEach((button) => {
      button.addEventListener("click", async () => {
        await addAthlete(button.dataset.profileId);
        searchInput.value = "";
        searchResults.hidden = true;
      });
    });
  });

  rows = rows.map((row) => ({
    ...row,
    cells: row.cells.map((cell, index) => ({
      ...cell,
      clock_seconds: cell.clock_seconds ?? null,
      leg_seconds: cell.leg_seconds ?? null,
      hidden_by_default: Boolean(cell.hidden_by_default ?? columnHiddenByDefault[index]),
    })),
  }));

  bindDragAndDrop();
  bindHiddenSplitToggle();
})();
