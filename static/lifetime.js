(function () {
  const PROVIDER = "usat";
  const SEARCH_URL = "/api/lifetime/search";
  const COMPARE_URL = "/lifetime/compare";
  const DEBOUNCE_MS = 300;

  const slots = {
    a: { id: null, profile: null },
    b: { id: null, profile: null },
  };

  const searchInputs = {
    a: document.getElementById("search-a"),
    b: document.getElementById("search-b"),
  };
  const resultLists = {
    a: document.getElementById("results-a"),
    b: document.getElementById("results-b"),
  };
  const selectedLabels = {
    a: document.getElementById("selected-a"),
    b: document.getElementById("selected-b"),
  };
  const compareBtn = document.getElementById("lifetime-compare-btn");

  let debounceTimers = { a: null, b: null };

  function formatProfile(profile) {
    const parts = [profile.display_name];
    if (profile.location) parts.push(profile.location);
    if (profile.age != null) parts.push(`${profile.age} yrs`);
    if (profile.gender) parts.push(profile.gender);
    return parts.join(" · ");
  }

  function updateCompareButton() {
    compareBtn.disabled = !(slots.a.id && slots.b.id && slots.a.id !== slots.b.id);
  }

  function clearResults(slot) {
    resultLists[slot].innerHTML = "";
    resultLists[slot].hidden = true;
  }

  function selectAthlete(slot, profile) {
    slots[slot].id = profile.athlete_id;
    slots[slot].profile = profile;
    searchInputs[slot].value = profile.display_name;
    selectedLabels[slot].textContent = formatProfile(profile);
    selectedLabels[slot].hidden = false;
    clearResults(slot);
    updateCompareButton();
  }

  function renderResults(slot, results) {
    const list = resultLists[slot];
    list.innerHTML = "";
    if (!results.length) {
      list.hidden = true;
      return;
    }
    for (const profile of results) {
      const item = document.createElement("li");
      const button = document.createElement("button");
      button.type = "button";
      button.className = "search-result-btn";
      button.textContent = formatProfile(profile);
      button.addEventListener("click", () => selectAthlete(slot, profile));
      item.appendChild(button);
      list.appendChild(item);
    }
    list.hidden = false;
  }

  async function searchAthletes(slot, query) {
    if (query.length < 2) {
      clearResults(slot);
      return;
    }
    const params = new URLSearchParams({ q: query, provider: PROVIDER });
    const response = await fetch(`${SEARCH_URL}?${params.toString()}`);
    if (!response.ok) {
      clearResults(slot);
      return;
    }
    const payload = await response.json();
    renderResults(slot, payload.results || []);
  }

  function handleSearchInput(slot) {
    const input = searchInputs[slot];
    input.addEventListener("input", () => {
      slots[slot].id = null;
      slots[slot].profile = null;
      selectedLabels[slot].hidden = true;
      updateCompareButton();
      clearTimeout(debounceTimers[slot]);
      debounceTimers[slot] = setTimeout(() => {
        searchAthletes(slot, input.value.trim());
      }, DEBOUNCE_MS);
    });
  }

  compareBtn.addEventListener("click", () => {
    if (compareBtn.disabled) return;
    const params = new URLSearchParams({
      a: slots.a.id,
      b: slots.b.id,
      provider: PROVIDER,
    });
    window.location.href = `${COMPARE_URL}?${params.toString()}`;
  });

  handleSearchInput("a");
  handleSearchInput("b");
})();
