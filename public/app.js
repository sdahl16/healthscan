const form = document.querySelector("#search-form");
const procedureInput = document.querySelector("#procedure");
const locationInput = document.querySelector("#location");
const radiusInput = document.querySelector("#radius");
const sortInput = document.querySelector("#sort");
const priceTypeInput = document.querySelector("#price-type");
const statusRegion = document.querySelector("#status-region");
const resultsRegion = document.querySelector("#results-region");
const disclaimerTemplate = document.querySelector("#disclaimer-template");

let lastSelected = null;

const priceLabels = {
  cash: "Cash price",
  negotiated: "Negotiated rate",
  negotiated_min: "Negotiated minimum",
};

function money(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function clear() {
  statusRegion.replaceChildren();
  resultsRegion.replaceChildren();
}

function notice(message, kind = "") {
  const node = document.createElement("div");
  node.className = `notice ${kind}`.trim();
  node.textContent = message;
  statusRegion.replaceChildren(node);
}

function appendDisclaimers() {
  resultsRegion.append(disclaimerTemplate.content.cloneNode(true));
}

function currentPayload(selected = lastSelected) {
  return {
    procedure: procedureInput.value.trim(),
    location: locationInput.value.trim(),
    radius: Number(radiusInput.value),
    sort: sortInput.value,
    priceType: priceTypeInput.value,
    selected,
  };
}

async function search(selected = lastSelected) {
  clear();
  const loading = document.createElement("div");
  loading.className = "loading";
  loading.textContent = "Translating the procedure and checking hospital price files...";
  statusRegion.append(loading);

  const response = await fetch("/api/search", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(currentPayload(selected)),
  });
  const result = await response.json();
  clear();
  render(result);
}

function render(result) {
  if (result.status === "error") {
    notice(result.message || "Something went wrong.", "warning");
    return;
  }
  if (result.status === "location_not_found") {
    notice(result.message, "warning");
    return;
  }
  if (result.status === "clarification") {
    renderClarification(result);
    return;
  }
  if (result.status === "unavailable") {
    renderEmpty("Unavailable procedure", result.message || "This procedure has no indexed prices yet.", result);
    return;
  }
  if (result.status === "no_results_near_location") {
    renderNoNearby(result);
    return;
  }
  renderResults(result);
}

function renderClarification(result) {
  const panel = document.createElement("section");
  panel.className = "notice";
  const heading = document.createElement("strong");
  heading.textContent = result.translation.prompt || "Which procedure did you mean?";
  const grid = document.createElement("div");
  grid.className = "clarify-grid";

  for (const option of result.translation.options || []) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = `${option.label} (${option.code_type} ${option.procedure_code})`;
    button.addEventListener("click", () => {
      lastSelected = option;
      procedureInput.value = option.label;
      search(option);
    });
    grid.append(button);
  }

  panel.append(heading, grid);
  resultsRegion.append(panel);
}

function renderEmpty(title, message, result) {
  const panel = document.createElement("section");
  panel.className = "empty-state";
  panel.innerHTML = `<h2>${title}</h2><p>${message}</p>`;
  if (result.codes?.length) {
    const codes = document.createElement("p");
    codes.className = "meta";
    codes.textContent = `Checked ${result.codes.map((code) => `${code.code_type} ${code.procedure_code}`).join(", ")}.`;
    panel.append(codes);
  }
  resultsRegion.append(panel);
  appendDisclaimers();
}

function renderNoNearby(result) {
  const panel = document.createElement("section");
  panel.className = "empty-state";
  const canExpand = Number(result.radius) < 100;
  panel.innerHTML = `<h2>No results near ${result.location.label}</h2><p>${result.message}</p>`;
  if (canExpand) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "button-secondary";
    button.textContent = "Expand to 100 miles";
    button.addEventListener("click", () => {
      radiusInput.value = "100";
      search();
    });
    panel.append(button);
  }
  resultsRegion.append(panel);
  appendDisclaimers();
}

function renderResults(result) {
  const summary = document.createElement("section");
  summary.className = result.status === "limited_coverage" ? "notice warning" : "notice success";
  const label = result.translation?.candidates?.[0]?.description || procedureInput.value;
  const statusText =
    result.status === "limited_coverage"
      ? "Limited coverage: fewer than 3 hospitals matched this search."
      : "Results found";
  summary.innerHTML = `
    <div class="summary-row">
      <h2>${label}</h2>
      <span class="pill ${result.status === "limited_coverage" ? "warning" : ""}">${statusText}</span>
    </div>
    <p>${result.hospitals.length} hospital${result.hospitals.length === 1 ? "" : "s"} within ${result.radius} miles of ${result.location.label}. Coverage is currently strongest in Southern California.</p>
  `;
  resultsRegion.append(summary);
  appendDisclaimers();

  const list = document.createElement("section");
  list.className = "hospital-list";
  for (const hospital of result.hospitals) {
    list.append(renderHospital(hospital));
  }
  resultsRegion.append(list);
}

function renderHospital(hospital) {
  const card = document.createElement("article");
  card.className = "hospital-card";

  const info = document.createElement("div");
  info.innerHTML = `
    <h3>${hospital.name}</h3>
    <p class="meta">
      <span>${hospital.address || "Address unavailable"}</span>
      <span>${hospital.distance_miles} miles away</span>
      <span>${hospital.code_type} ${hospital.procedure_code}</span>
    </p>
  `;

  const price = document.createElement("div");
  price.className = "price-block";
  price.innerHTML = `
    <p class="price">${money(hospital.headline_price.amount)}</p>
    <p class="price-label">${priceLabels[hospital.headline_price.type] || hospital.headline_price.type}</p>
    <p class="price-label">Updated ${hospital.headline_price.last_updated || "unknown"}</p>
  `;

  const details = document.createElement("details");
  details.className = "details";
  details.innerHTML = `
    <summary>Price details</summary>
    <table class="price-table">
      <thead><tr><th>Type</th><th>Amount</th><th>Payer / plan</th><th>Updated</th></tr></thead>
      <tbody>
        ${hospital.prices
          .map(
            (priceRow) => `
              <tr>
                <td>${priceLabels[priceRow.type] || priceRow.type}</td>
                <td>${money(priceRow.amount)}</td>
                <td>${[priceRow.payer_name, priceRow.plan_name].filter(Boolean).join(" / ") || "Not listed"}</td>
                <td>${priceRow.last_updated || "unknown"}</td>
              </tr>
            `,
          )
          .join("")}
      </tbody>
    </table>
  `;
  if (hospital.suppressed_price_count > 0) {
    const suppressed = document.createElement("p");
    suppressed.textContent = `${hospital.suppressed_price_count} flagged price row${hospital.suppressed_price_count === 1 ? " was" : "s were"} suppressed from the headline price.`;
    details.append(suppressed);
  }

  card.append(info, price, details);
  return card;
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  lastSelected = null;
  search(null).catch((error) => {
    clear();
    notice(error.message, "warning");
  });
});

for (const control of [radiusInput, sortInput, priceTypeInput]) {
  control.addEventListener("change", () => {
    if (procedureInput.value.trim() && locationInput.value.trim()) {
      search().catch((error) => {
        clear();
        notice(error.message, "warning");
      });
    }
  });
}
