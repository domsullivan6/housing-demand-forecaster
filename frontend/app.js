// Frontend controller for loading API data and rendering the dashboard.

let housingChart;

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
loadDashboard();
