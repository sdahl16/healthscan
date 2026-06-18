const form = document.querySelector("#search-form");
const procedureInput = document.querySelector("#procedure");
const locationInput = document.querySelector("#location");
const radiusInput = document.querySelector("#radius");
const sortInput = document.querySelector("#sort");
const priceTypeInput = document.querySelector("#price-type");
const insuranceFilterInput = document.querySelector("#insurance-filter");
const statusRegion = document.querySelector("#status-region");
const resultsRegion = document.querySelector("#results-region");
const disclaimerTemplate = document.querySelector("#disclaimer-template");
const feedbackTemplate = document.querySelector("#feedback-template");
const procedureOptions = document.querySelector("#procedure-options");
const locationOptions = document.querySelector("#location-options");

let lastSelected = null;

const priceLabels = {
  cash: "Self-pay / cash price",
  negotiated: "Insurance negotiated rate",
  negotiated_min: "Insurance negotiated minimum",
};

const fallbackProcedures = [
  { plain_name: "Appendectomy", procedure_code: "44970", code_type: "CPT" },
  { plain_name: "Appendectomy (inpatient)", procedure_code: "341", code_type: "DRG" },
  { plain_name: "Breast lumpectomy", procedure_code: "19301", code_type: "CPT" },
  { plain_name: "C-section", procedure_code: "783", code_type: "DRG" },
  { plain_name: "Cardiac catheterization", procedure_code: "287", code_type: "DRG" },
  { plain_name: "Carpal tunnel surgery", procedure_code: "64721", code_type: "CPT" },
  { plain_name: "Cataract surgery", procedure_code: "66984", code_type: "CPT" },
  { plain_name: "Colonoscopy", procedure_code: "45378", code_type: "CPT" },
  { plain_name: "Coronary bypass (CABG)", procedure_code: "231", code_type: "DRG" },
  { plain_name: "CT scan abdomen", procedure_code: "74178", code_type: "CPT" },
  { plain_name: "Echocardiogram", procedure_code: "93306", code_type: "CPT" },
  { plain_name: "EKG", procedure_code: "93000", code_type: "CPT" },
  { plain_name: "Emergency department visit", procedure_code: "99285", code_type: "CPT" },
  { plain_name: "Gallbladder removal", procedure_code: "47562", code_type: "CPT" },
  { plain_name: "Gallbladder removal (open)", procedure_code: "47563", code_type: "CPT" },
  { plain_name: "Hernia repair", procedure_code: "49505", code_type: "CPT" },
  { plain_name: "Hip replacement", procedure_code: "470", code_type: "DRG" },
  { plain_name: "Knee arthroscopy", procedure_code: "29881", code_type: "CPT" },
  { plain_name: "Knee replacement", procedure_code: "470", code_type: "DRG" },
  { plain_name: "Mammogram", procedure_code: "77067", code_type: "CPT" },
  { plain_name: "Mastectomy", procedure_code: "19303", code_type: "CPT" },
  { plain_name: "MRI brain", procedure_code: "70551", code_type: "CPT" },
  { plain_name: "MRI spine", procedure_code: "72148", code_type: "CPT" },
  { plain_name: "Screening colonoscopy", procedure_code: "G0121", code_type: "HCPCS" },
  { plain_name: "Shoulder arthroscopy", procedure_code: "29827", code_type: "CPT" },
  { plain_name: "Sleep study", procedure_code: "95810", code_type: "CPT" },
  { plain_name: "Tonsillectomy", procedure_code: "42826", code_type: "CPT" },
  { plain_name: "Tonsillectomy (child)", procedure_code: "42825", code_type: "CPT" },
  { plain_name: "Upper endoscopy", procedure_code: "43239", code_type: "CPT" },
  { plain_name: "Upper endoscopy with biopsy", procedure_code: "43235", code_type: "CPT" },
  { plain_name: "Vaginal delivery", procedure_code: "807", code_type: "DRG" },
];

const fallbackLocations = [
  { value: "Los Angeles, CA", label: "City" },
  { value: "San Diego, CA", label: "City" },
  { value: "Chula Vista, CA", label: "City" },
  { value: "La Jolla, CA 92037", label: "Scripps Green area" },
  { value: "Los Angeles, CA 90033", label: "Keck USC area" },
  { value: "Los Angeles, CA 90089", label: "USC area" },
  { value: "Los Angeles, CA 90095", label: "UCLA area" },
  { value: "San Diego, CA 92103", label: "UCSD Hillcrest area" },
  { value: "San Diego, CA 92123", label: "Rady area" },
  { value: "Chula Vista, CA 91910", label: "Chula Vista area" },
  { value: "Chula Vista, CA 91911", label: "Sharp Chula Vista area" },
  { value: "San Francisco, CA", label: "Out-of-area test" },
  { value: "San Francisco, CA 94102", label: "Out-of-area test" },
];

function renderProcedureOptions(procedures) {
  const options = procedures.map((procedure) => {
    const option = document.createElement("option");
    option.value = procedure.plain_name;
    option.label = `${procedure.code_type} ${procedure.procedure_code}`;
    return option;
  });
  procedureOptions.replaceChildren(...options);
}

function renderLocationOptions(locations) {
  const options = locations.map((location) => {
    const option = document.createElement("option");
    option.value = location.value;
    option.label = location.label;
    return option;
  });
  locationOptions.replaceChildren(...options);
}

function renderInsuranceOptions(options = [], selectedValue = insuranceFilterInput.value) {
  const allOption = document.createElement("option");
  allOption.value = "all";
  allOption.textContent = "All insurance";
  const payerOptions = options.map((payer) => {
    const option = document.createElement("option");
    option.value = payer.value;
    option.textContent = payer.count ? `${payer.label} (${payer.count} rows)` : payer.label;
    return option;
  });
  insuranceFilterInput.replaceChildren(allOption, ...payerOptions);
  const values = new Set(["all", ...options.map((payer) => payer.value)]);
  insuranceFilterInput.value = values.has(selectedValue) ? selectedValue : "all";
}

async function loadProcedureOptions() {
  renderProcedureOptions(fallbackProcedures);
  try {
    const response = await fetch("/api/procedures");
    if (!response.ok) {
      return;
    }
    const procedures = await response.json();
    renderProcedureOptions(procedures);
  } catch {
    renderProcedureOptions(fallbackProcedures);
  }
}

async function loadLocationOptions() {
  renderLocationOptions(fallbackLocations);
  try {
    const response = await fetch("/api/locations");
    if (!response.ok) {
      return;
    }
    const locations = await response.json();
    renderLocationOptions(locations);
  } catch {
    renderLocationOptions(fallbackLocations);
  }
}

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

function appendFeedback(prompts = []) {
  if (!feedbackTemplate) {
    return;
  }
  const fragment = feedbackTemplate.content.cloneNode(true);
  const card = fragment.querySelector(".feedback-card");
  if (card && prompts.length) {
    const details = document.createElement("details");
    details.className = "feedback-prompts";
    details.innerHTML = `
      <summary>Suggested tester questions</summary>
      <ul>${prompts.map((prompt) => `<li>${tooltipText(prompt)}</li>`).join("")}</ul>
    `;
    card.append(details);
  }
  resultsRegion.append(fragment);
}

function currentPayload(selected = lastSelected) {
  return {
    procedure: procedureInput.value.trim(),
    location: locationInput.value.trim(),
    radius: Number(radiusInput.value),
    sort: sortInput.value,
    priceType: priceTypeInput.value,
    insuranceFilter: insuranceFilterInput.value,
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

function renderExamples(panel, examples = []) {
  if (!examples.length) {
    return;
  }
  const wrapper = document.createElement("div");
  wrapper.className = "example-searches";
  const label = document.createElement("p");
  label.className = "meta";
  label.textContent = "Try a supported alpha search:";
  const buttons = document.createElement("div");
  buttons.className = "clarify-grid";
  for (const example of examples) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = example;
    button.addEventListener("click", () => {
      procedureInput.value = example;
      search(null).catch((error) => {
        clear();
        notice(error.message, "warning");
      });
    });
    buttons.append(button);
  }
  wrapper.append(label, buttons);
  panel.append(wrapper);
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
  const why = document.createElement("div");
  why.className = "empty-next-steps";
  why.innerHTML = `
    <strong>What to try next</strong>
    <ul>
      <li>Try a supported alpha example below.</li>
      <li>Try a nearby Southern California ZIP/city that is currently covered.</li>
      <li>If this was a user test, note the exact procedure/location so coverage gaps can be prioritized.</li>
    </ul>
  `;
  panel.append(why);
  renderExamples(panel, result.examples || []);
  resultsRegion.append(panel);
  appendDisclaimers();
  appendFeedback(result.testing_prompts || []);
}

function renderNoNearby(result) {
  renderInsuranceOptions(result.insurance_filters || [], result.insurance_filter || insuranceFilterInput.value);
  const panel = document.createElement("section");
  panel.className = "empty-state";
  const canExpand = Number(result.radius) < 100;
  panel.innerHTML = `<h2>No results near ${result.location.label}</h2><p>${result.message}</p>`;
  const nextSteps = document.createElement("div");
  nextSteps.className = "empty-next-steps";
  nextSteps.innerHTML = `
    <strong>Why this can happen</strong>
    <ul>
      <li>The procedure exists in the index, but not for hospitals inside this radius.</li>
      <li>The selected price type may hide otherwise available rows.</li>
      <li>Alpha coverage currently emphasizes selected Southern California hospitals.</li>
    </ul>
  `;
  panel.append(nextSteps);
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
  renderExamples(panel, result.examples || []);
  resultsRegion.append(panel);
  appendDisclaimers();
  appendFeedback(result.testing_prompts || []);
}

function renderPriceRanges(ranges = {}) {
  const entries = [ranges.cash, ranges.negotiated].filter(Boolean);
  if (!entries.length) {
    return "";
  }
  return `
    <div class="price-ranges" aria-label="Price ranges by context">
      ${entries
        .map(
          (range) => `
            <div class="range-card">
              <span>${tooltipText(range.label)}</span>
              <strong>${money(range.min)}${range.min === range.max ? "" : `–${money(range.max)}`}</strong>
            </div>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderResults(result) {
  renderInsuranceOptions(result.insurance_filters || [], result.insurance_filter || insuranceFilterInput.value);
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
    <p class="summary-source-note"><strong>${result.price_filter_label || "Selected price view"}:</strong> ${result.hospitals[0]?.selection_explanation || "Prices are selected from eligible, non-flagged hospital-published rows."}</p>
    ${renderPriceRanges(result.price_ranges)}
    <p class="summary-source-note">Each result includes a hospital-published MRF source link and the best available date label. Use the source/date line to decide whether you trust a result.</p>
  `;
  resultsRegion.append(summary);
  appendDisclaimers();

  const list = document.createElement("section");
  list.className = "hospital-list";
  for (const hospital of result.hospitals) {
    list.append(renderHospital(hospital, result.price_details_help));
  }
  resultsRegion.append(list);
  appendFeedback(result.testing_prompts || []);
}

function tooltipText(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll('"', "&quot;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function renderHospital(hospital, priceDetailsHelp = "Hospitals can publish the same dollar amount for different payer or plan contracts. HealthScan keeps distinct payer/plan rows and removes exact duplicates.") {
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
  const source = hospital.headline_price.source || {};
  const sourceLink = source.url || hospital.source_url;
  const headlinePayerPlan = hospital.headline_price.payer_plan_display || "Not listed in source file";
  price.innerHTML = `
    <p class="price">${money(hospital.headline_price.amount)}</p>
    <p class="price-label">${priceLabels[hospital.headline_price.type] || hospital.headline_price.type}</p>
    <p class="price-label payer-plan-line"><strong>Payer / plan:</strong> ${tooltipText(headlinePayerPlan)}</p>
    <p class="price-label source-date-line">${source.timestamp_label || "Indexed by HealthScan"}: ${source.display_timestamp || "unknown"}${sourceLink ? ` · <a href="${sourceLink}" target="_blank" rel="noreferrer">View MRF source</a>` : ""}</p>
  `;

  const details = document.createElement("details");
  details.className = "details";
  const detailsHelp = tooltipText(priceDetailsHelp);
  details.innerHTML = `
    <summary>Price details <span class="info-tooltip" tabindex="0" role="note" aria-label="Repeated price explanation">ⓘ<span class="tooltip-popover">${detailsHelp}</span></span></summary>
    <p class="meta">${hospital.selection_explanation || "HealthScan selected the displayed row from eligible, non-flagged price rows."}</p>
    <p class="repeated-price-help"><strong>Why repeat prices?</strong> ${detailsHelp}</p>
    <p class="meta">Source: ${hospital.source_url ? `<a href="${hospital.source_url}" target="_blank" rel="noreferrer">hospital-published MRF row</a>` : "source URL unavailable"}</p>
    <table class="price-table">
      <thead><tr><th>Type</th><th>Amount</th><th>Payer / plan</th><th>Date/source shown</th></tr></thead>
      <tbody>
        ${hospital.prices
          .map(
            (priceRow) => `
              <tr>
                <td>${priceLabels[priceRow.type] || priceRow.type}</td>
                <td>${money(priceRow.amount)}${priceRow.display_amount_note ? ` <span class="repeated-amount-badge" title="${tooltipText(priceRow.display_amount_note)}">same amount ×${priceRow.display_amount_group_count}</span>` : ""}</td>
                <td>${priceRow.payer_plan_display || "Not listed"}</td>
                <td>${priceRow.source?.display_timestamp || priceRow.last_updated || "unknown"}${priceRow.source?.url ? ` · <a href="${priceRow.source.url}" target="_blank" rel="noreferrer">source</a>` : ""}</td>
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

for (const control of [radiusInput, sortInput, priceTypeInput, insuranceFilterInput]) {
  control.addEventListener("change", () => {
    if (procedureInput.value.trim() && locationInput.value.trim()) {
      search().catch((error) => {
        clear();
        notice(error.message, "warning");
      });
    }
  });
}

loadProcedureOptions();
loadLocationOptions();
