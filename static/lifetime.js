(function () {
  const PROVIDER = "usat";
  const SEARCH_URL = "/api/lifetime/search";
  const COMPARE_URL = "/lifetime/compare";
  const MIN_QUERY_LENGTH = 3;

  const slots = {
    a: { id: null, profile: null },
    b: { id: null, profile: null },
  };

  const lifetimeSection = document.getElementById("lifetime-section");
  const searchInputs = {
    a: document.getElementById("search-a"),
    b: document.getElementById("search-b"),
  };
  const searchButtons = {
    a: document.getElementById("search-btn-a"),
    b: document.getElementById("search-btn-b"),
  };
  const resultLists = {
    a: document.getElementById("results-a"),
    b: document.getElementById("results-b"),
  };
  const selectedLabels = {
    a: document.getElementById("selected-a"),
    b: document.getElementById("selected-b"),
  };
  const hints = {
    a: document.getElementById("hint-a"),
    b: document.getElementById("hint-b"),
  };
  const statuses = {
    a: document.getElementById("status-a"),
    b: document.getElementById("status-b"),
  };
  const athleteSlots = {
    a: document.querySelector('.athlete-slot[data-slot="a"]'),
    b: document.querySelector('.athlete-slot[data-slot="b"]'),
  };
  const compareBtn = document.getElementById("lifetime-compare-btn");
  const compareBtnLabel = compareBtn.querySelector(".btn-label");

  let searchControllers = { a: null, b: null };
  let searchLoading = { a: false, b: false };
  let compareLoading = false;

  function formatProfile(profile) {
    const parts = [profile.display_name];
    if (profile.location) parts.push(profile.location);
    if (profile.age != null) parts.push(`${profile.age} yrs`);
    if (profile.gender) parts.push(profile.gender);
    return parts.join(" · ");
  }

  function isBusy() {
    return compareLoading || searchLoading.a || searchLoading.b;
  }

  function updateCompareButton() {
    compareBtn.disabled = compareLoading || !(slots.a.id && slots.b.id && slots.a.id !== slots.b.id);
  }

  function clearResults(slot) {
    resultLists[slot].innerHTML = "";
    resultLists[slot].hidden = true;
  }

  function clearStatus(slot) {
    const status = statuses[slot];
    status.hidden = true;
    status.textContent = "";
    status.classList.remove("is-error");
    status.replaceChildren();
  }

  function setSearchLoading(slot, loading) {
    searchLoading[slot] = loading;
    athleteSlots[slot].classList.toggle("is-searching", loading);
    searchInputs[slot].disabled = loading || compareLoading;
    searchButtons[slot].disabled = loading || compareLoading;
    if (loading) {
      searchButtons[slot].textContent = "Searching…";
    } else {
      searchButtons[slot].textContent = "Search";
    }
    updateCompareButton();
  }

  function setCompareLoading(loading) {
    compareLoading = loading;
    lifetimeSection.classList.toggle("is-comparing", loading);
    compareBtn.classList.toggle("is-loading", loading);
    compareBtnLabel.textContent = loading ? "Loading comparison…" : "Compare shared races";
    for (const slot of ["a", "b"]) {
      searchInputs[slot].disabled = loading || searchLoading[slot];
      searchButtons[slot].disabled = loading || searchLoading[slot];
    }
    updateCompareButton();
  }

  function showStatus(slot, message, { error = false, loading = false } = {}) {
    const status = statuses[slot];
    status.replaceChildren();
    if (loading) {
      const spinner = document.createElement("span");
      spinner.className = "spinner";
      spinner.setAttribute("aria-hidden", "true");
      status.appendChild(spinner);
    }
    status.appendChild(document.createTextNode(message));
    status.classList.toggle("is-error", error);
    status.hidden = false;
  }

  function selectAthlete(slot, profile) {
    slots[slot].id = profile.athlete_id;
    slots[slot].profile = profile;
    searchInputs[slot].value = profile.display_name;
    selectedLabels[slot].textContent = formatProfile(profile);
    selectedLabels[slot].hidden = false;
    hints[slot].hidden = true;
    clearResults(slot);
    clearStatus(slot);
    updateCompareButton();
  }

  function renderResults(slot, results) {
    const list = resultLists[slot];
    list.innerHTML = "";
    if (!results.length) {
      list.hidden = true;
      showStatus(slot, "No matches found. Try a different spelling or more of the name.", { error: true });
      return;
    }
    clearStatus(slot);
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
    if (results.length === 1) {
      showStatus(slot, "One match — select it below, or refine your search.");
    } else {
      showStatus(slot, `${results.length} matches — select the correct athlete below.`);
    }
  }

  async function searchAthletes(slot) {
    if (searchLoading[slot] || compareLoading) return;

    const query = searchInputs[slot].value.trim();
    clearResults(slot);
    clearStatus(slot);

    if (query.length < MIN_QUERY_LENGTH) {
      showStatus(slot, `Enter at least ${MIN_QUERY_LENGTH} characters, then press Search or Enter.`, {
        error: true,
      });
      return;
    }

    if (searchControllers[slot]) {
      searchControllers[slot].abort();
    }
    const controller = new AbortController();
    searchControllers[slot] = controller;

    setSearchLoading(slot, true);
    showStatus(slot, "Searching USAT results…", { loading: true });

    const params = new URLSearchParams({ q: query, provider: PROVIDER });
    try {
      const response = await fetch(`${SEARCH_URL}?${params.toString()}`, {
        signal: controller.signal,
      });
      if (controller.signal.aborted) return;

      let payload = {};
      try {
        payload = await response.json();
      } catch (_error) {
        payload = {};
      }

      if (response.status === 429) {
        showStatus(slot, payload.error || "USAT is temporarily limiting requests; try again in a minute.", {
          error: true,
        });
        return;
      }
      if (!response.ok) {
        showStatus(slot, payload.error || "Search failed. Please try again.", { error: true });
        return;
      }

      renderResults(slot, payload.results || []);
    } catch (error) {
      if (error.name === "AbortError") return;
      showStatus(slot, "Search failed. Please try again.", { error: true });
    } finally {
      if (searchControllers[slot] === controller) {
        searchControllers[slot] = null;
      }
      setSearchLoading(slot, false);
    }
  }

  function resetSlotSelection(slot) {
    slots[slot].id = null;
    slots[slot].profile = null;
    selectedLabels[slot].hidden = true;
    hints[slot].hidden = false;
    clearResults(slot);
    clearStatus(slot);
    updateCompareButton();
  }

  function handleSearchInput(slot) {
    const input = searchInputs[slot];
    input.addEventListener("input", () => {
      if (slots[slot].id || slots[slot].profile) {
        resetSlotSelection(slot);
      } else {
        clearResults(slot);
        clearStatus(slot);
      }
    });
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        searchAthletes(slot);
      }
    });
  }

  function handleSearchButton(slot) {
    searchButtons[slot].addEventListener("click", () => {
      searchAthletes(slot);
    });
  }

  compareBtn.addEventListener("click", () => {
    if (compareBtn.disabled || isBusy()) return;
    setCompareLoading(true);
    const params = new URLSearchParams({
      a: slots.a.id,
      b: slots.b.id,
      provider: PROVIDER,
    });
    window.location.href = `${COMPARE_URL}?${params.toString()}`;
  });

  handleSearchInput("a");
  handleSearchInput("b");
  handleSearchButton("a");
  handleSearchButton("b");
})();
