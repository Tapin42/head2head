(function () {
  const table = document.getElementById("lifetime-table");
  if (!table) return;

  const tbody = table.querySelector("tbody");
  const sortableHeaders = table.querySelectorAll("th.sortable");
  let activeSort = { key: "date", direction: "desc" };

  function compareRows(a, b, key, direction) {
    const attr = key === "date" ? "date" : key === "event" ? "event" : "race";
    const left = a.dataset[attr] || "";
    const right = b.dataset[attr] || "";
    const cmp = left.localeCompare(right, undefined, { numeric: true, sensitivity: "base" });
    return direction === "asc" ? cmp : -cmp;
  }

  function sortRows() {
    const rows = Array.from(tbody.querySelectorAll("tr"));
    rows.sort((a, b) => compareRows(a, b, activeSort.key, activeSort.direction));
    rows.forEach((row) => tbody.appendChild(row));
  }

  function updateHeaderState() {
    sortableHeaders.forEach((header) => {
      const key = header.dataset.sortKey;
      const isActive = key === activeSort.key;
      header.setAttribute("aria-sort", isActive ? (activeSort.direction === "asc" ? "ascending" : "descending") : "none");
      header.classList.toggle("sort-active", isActive);
    });
  }

  sortableHeaders.forEach((header) => {
    header.addEventListener("click", () => {
      const key = header.dataset.sortKey;
      if (activeSort.key === key) {
        activeSort.direction = activeSort.direction === "asc" ? "desc" : "asc";
      } else {
        activeSort = { key, direction: key === "date" ? "desc" : "asc" };
      }
      sortRows();
      updateHeaderState();
    });
  });

  updateHeaderState();
})();
