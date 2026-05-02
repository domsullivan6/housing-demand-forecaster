// Frontend controller for loading API data and rendering the dashboard.

let housingChart;
let predictionChart;
let lagFeatures = [];

const featureLabels = {
  housing_starts: "Housing starts",
  building_permits: "Building permits",
  mortgage_rate: "Mortgage rate",
  home_price_change: "Home price change",
  housing_starts_change: "Housing starts change",
  building_permits_change: "Building permits change",
  mortgage_rate_change: "Mortgage rate change",
};

const formatNumber = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 0,
});

const formatDecimal = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 2,
});

function setStatus(message) {
  // Keep loading and error messages in one consistent place.
  document.getElementById("status").textContent = message;
}

async function fetchJson(url) {
  // Small helper so API errors show up clearly in the dashboard.
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

function updateLatestValues(latest) {
  // Populate the top metric cards with the latest joined observation.
  document.getElementById("housingStarts").textContent = formatNumber.format(latest.housing_starts);
  document.getElementById("buildingPermits").textContent = formatNumber.format(latest.building_permits);
  document.getElementById("mortgageRate").textContent = `${formatDecimal.format(latest.mortgage_rate)}%`;
  document.getElementById("homePriceIndex").textContent = formatDecimal.format(latest.home_price_index);
  document.getElementById("latestDate").textContent = `Latest month: ${latest.date}`;
}

function drawChart(records) {
  // The API already sends a recent window, keeping the first render quick.
  const recentRecords = records;
  const labels = recentRecords.map((row) => row.date.slice(0, 7));
  const chartData = {
    labels,
    datasets: [
      {
        label: "Mortgage Rate (%)",
        data: recentRecords.map((row) => row.mortgage_rate),
        borderColor: "#0f766e",
        backgroundColor: "#0f766e",
        yAxisID: "rateAxis",
        tension: 0.25,
        pointRadius: 0,
      },
      {
        label: "Housing Starts",
        data: recentRecords.map((row) => row.housing_starts),
        borderColor: "#2563eb",
        backgroundColor: "#2563eb",
        yAxisID: "volumeAxis",
        tension: 0.25,
        pointRadius: 0,
      },
      {
        label: "Building Permits",
        data: recentRecords.map((row) => row.building_permits),
        borderColor: "#b45309",
        backgroundColor: "#b45309",
        yAxisID: "volumeAxis",
        tension: 0.25,
        pointRadius: 0,
      },
      {
        label: "Home Price Index",
        data: recentRecords.map((row) => row.home_price_index),
        borderColor: "#7c3aed",
        backgroundColor: "#7c3aed",
        yAxisID: "priceAxis",
        tension: 0.25,
        pointRadius: 0,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    interaction: {
      mode: "index",
      intersect: false,
    },
    plugins: {
      legend: {
        position: "bottom",
      },
    },
    scales: {
      rateAxis: {
        type: "linear",
        position: "left",
        title: {
          display: true,
          text: "Mortgage rate",
        },
      },
      volumeAxis: {
        type: "linear",
        position: "right",
        grid: {
          drawOnChartArea: false,
        },
        title: {
          display: true,
          text: "Starts / permits",
        },
      },
      priceAxis: {
        type: "linear",
        display: false,
      },
    },
  };

  if (housingChart) {
    housingChart.destroy();
  }

  housingChart = new Chart(document.getElementById("housingChart"), {
    type: "line",
    data: chartData,
    options,
  });
}

function updateForecast(forecast) {
  // Show the model output and a compact explanation of what drove it.
  const sign = forecast.forecast_next_home_price_change_pct >= 0 ? "+" : "";
  document.getElementById("forecastOutput").innerHTML = `
    <div class="forecast-number">${sign}${forecast.forecast_next_home_price_change_pct}%</div>
    <div class="forecast-meta">
      Forecast next monthly Case-Shiller index change from data through ${forecast.latest_model_date}.
      Test MAE: ${forecast.test_mae_pct_points} percentage points. R²: ${forecast.test_r2}.
    </div>
  `;

  document.getElementById("featureImportance").innerHTML = forecast.feature_importance
    .map(
      (item) => `
        <div class="feature-row">
          <span>${item.feature.replaceAll("_", " ")}</span>
          <strong>${formatDecimal.format(item.importance)}</strong>
        </div>
      `,
    )
    .join("");
}

function updateInsights(insights) {
  // Render rule-based commentary cards from the backend.
  document.getElementById("insightsList").innerHTML = insights
    .map(
      (insight) => `
        <article class="insight-card ${insight.tone}">
          <h3>${insight.title}</h3>
          <p>${insight.message}</p>
        </article>
      `,
    )
    .join("");
}

function setupTabs() {
  // Swap between the dashboard and model hub without leaving the page.
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".tab-button").forEach((tabButton) => tabButton.classList.remove("active"));
      document.querySelectorAll(".tab-view").forEach((view) => view.classList.remove("active"));

      button.classList.add("active");
      document.getElementById(button.dataset.tabTarget).classList.add("active");
    });
  });
}

function renderLagList() {
  // Keep the lag feature chips in sync with the current model configuration.
  const lagList = document.getElementById("lagList");
  if (lagFeatures.length === 0) {
    lagList.innerHTML = `<span class="forecast-meta">No custom lag features yet.</span>`;
    return;
  }

  lagList.innerHTML = lagFeatures
    .map(
      (feature, index) => `
        <span class="lag-chip">
          ${featureLabels[feature.source]} lag ${feature.lag}
          <button type="button" aria-label="Remove ${featureLabels[feature.source]} lag ${feature.lag}" data-lag-index="${index}">x</button>
        </span>
      `,
    )
    .join("");

  lagList.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      lagFeatures.splice(Number(button.dataset.lagIndex), 1);
      renderLagList();
    });
  });
}

function addLagFeature() {
  // Add one user-defined month lag to the training payload.
  const source = document.getElementById("lagSourceSelect").value;
  const lag = Number(document.getElementById("lagMonthsInput").value);

  if (!Number.isInteger(lag) || lag < 1 || lag > 24) {
    document.getElementById("modelReportStatus").textContent = "Lag months must be a whole number from 1 to 24.";
    return;
  }

  const alreadyExists = lagFeatures.some((feature) => feature.source === source && feature.lag === lag);
  if (!alreadyExists) {
    lagFeatures.push({ source, lag });
  }
  renderLagList();
}

function selectedBaseFeatures() {
  // Read checked feature inputs from the model hub.
  return [...document.querySelectorAll('input[name="modelFeature"]:checked')].map((input) => input.value);
}

function updateModelReport(result) {
  // Render model fit metrics, coefficients/importances, and prediction chart.
  document.getElementById("modelReportStatus").textContent =
    `${result.algorithm} trained with ${result.training_rows} training rows and ${result.test_rows} test rows.`;

  document.getElementById("modelMetrics").innerHTML = `
    <div class="model-metric"><span>MAE</span><strong>${formatDecimal.format(result.metrics.mae)}</strong></div>
    <div class="model-metric"><span>RMSE</span><strong>${formatDecimal.format(result.metrics.rmse)}</strong></div>
    <div class="model-metric"><span>R²</span><strong>${formatDecimal.format(result.metrics.r2)}</strong></div>
  `;

  document.getElementById("explanationTitle").textContent = result.explanation_label;
  document.getElementById("modelExplanation").innerHTML = result.explanation
    .map(
      (row) => `
        <div class="explanation-row">
          <span>${row.feature.replaceAll("_", " ")}</span>
          <strong>${formatDecimal.format(row.value)}</strong>
        </div>
      `,
    )
    .join("");

  drawPredictionChart(result.predictions);
}

function drawPredictionChart(predictions) {
  // Plot the test-period actual values against model predictions.
  const labels = predictions.map((row) => row.date.slice(0, 7));
  const data = {
    labels,
    datasets: [
      {
        label: "Actual",
        data: predictions.map((row) => row.actual),
        borderColor: "#0f766e",
        backgroundColor: "#0f766e",
        pointRadius: 0,
        tension: 0.25,
      },
      {
        label: "Predicted",
        data: predictions.map((row) => row.predicted),
        borderColor: "#b45309",
        backgroundColor: "#b45309",
        pointRadius: 0,
        tension: 0.25,
      },
    ],
  };

  if (predictionChart) {
    predictionChart.destroy();
  }

  predictionChart = new Chart(document.getElementById("predictionChart"), {
    type: "line",
    data,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      interaction: {
        mode: "index",
        intersect: false,
      },
      plugins: {
        legend: {
          position: "bottom",
        },
      },
      scales: {
        y: {
          title: {
            display: true,
            text: "Monthly change (%)",
          },
        },
      },
    },
  });
}

async function trainInteractiveModel() {
  const trainButton = document.getElementById("trainModelButton");
  const payload = {
    algorithm: document.getElementById("algorithmSelect").value,
    features: selectedBaseFeatures(),
    lag_features: lagFeatures,
  };

  if (payload.features.length === 0 && payload.lag_features.length === 0) {
    document.getElementById("modelReportStatus").textContent = "Select at least one feature or lag feature.";
    return;
  }

  trainButton.disabled = true;
  trainButton.textContent = "Training...";
  document.getElementById("modelReportStatus").textContent = "Training model...";

  try {
    const response = await fetch("/api/model/train", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Model training failed.");
    }

    updateModelReport(await response.json());
  } catch (error) {
    console.error(error);
    document.getElementById("modelReportStatus").textContent = error.message;
  } finally {
    trainButton.disabled = false;
    trainButton.textContent = "Train Model";
  }
}

async function loadDashboard(refresh = false) {
  const params = new URLSearchParams({ months: "84" });
  if (refresh) {
    params.set("refresh", "true");
  }
  const suffix = `?${params.toString()}`;
  setStatus(refresh ? "Refreshing FRED data..." : "Loading public FRED data...");

  try {
    const data = await fetchJson(`/api/data${suffix}`);
    const [forecast, insightResponse] = await Promise.all([
      fetchJson("/api/forecast"),
      fetchJson("/api/insights"),
    ]);

    updateLatestValues(data.latest);
    drawChart(data.series);
    updateForecast(forecast);
    updateInsights(insightResponse.insights);
    setStatus(`${data.returned_rows} recent months shown from ${data.row_count} monthly observations.`);
  } catch (error) {
    console.error(error);
    setStatus("Could not load the dashboard. Check that the FastAPI server is running and has internet access for the first data download.");
  }
}

document.getElementById("refreshButton").addEventListener("click", () => loadDashboard(true));
document.getElementById("addLagButton").addEventListener("click", addLagFeature);
document.getElementById("trainModelButton").addEventListener("click", trainInteractiveModel);
setupTabs();
renderLagList();
loadDashboard();
