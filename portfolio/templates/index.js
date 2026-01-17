const mainChart = document.getElementById("main-chart");

// Portfolio NAV (from Flask → index.html)
const NAV = NAV_TS;
const buyDate = document.getElementById("sim-date");
const ticker = document.getElementById("sim-ticker-select");
const amount = document.getElementById("sim-cash");

const SIM_METRICS = SIM_METRICS_TS;
const SIM_NAV = SIM_NAV_TS;

const data = NAV_TS; 


const layout = {
    paper_bgcolor: "#3A3A3A",
    plot_bgcolor: "#3A3A3A",
    font: { color: "white" },
    margin: { t: 40, r: 30, l: 60, b: 60 }, // Increased margins to make room for titles
    xaxis: { 
        title: {
            text: "Date",
            font: { size: 14, color: "#adb5bd" }
        },
        gridcolor: "#666",
        zeroline: false
    },
    yaxis: { 
        title: {
            text: "Net Asset Value (USD)",
            font: { size: 14, color: "#adb5bd" }
        },
        gridcolor: "#666",
        zeroline: false
    },
    yaxis2: {
        title: {
            text: "Asset Preview",
            font: { size: 14, color: "#adb5bd" }
        },
        overlaying: "y",
        side: "right",
        gridcolor: "#444",
        zeroline: false, 
    },
    hovermode: "x unified"
};

Plotly.newPlot(mainChart, data, layout, { responsive: true });
let simulatedTraceIndex = null;
let simulationActive = false;

document.getElementById('portfolioUpload').addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (!file) return;

    const statusDiv = document.getElementById('uploadStatus');
    statusDiv.innerHTML = '<span class="text-info">Uploading...</span>';

    const formData = new FormData();
    formData.append('file', file);

    axios.post('/upload-portfolio', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    })
    .then(response => {
        statusDiv.innerHTML = '<span class="text-success">Upload successful!</span>';
        setTimeout(() => window.location.reload(), 1500);
    })
    .catch(error => {
        console.error(error);
        statusDiv.innerHTML = '<span class="text-danger">Upload failed.</span>';
    });
});

function drawSimulationLine(nav) {
  const trace = {
    x: nav.map(x => x.date),
    y: nav.map(x => x.nav),
    name: "Simulation",
    line: { width: 3, color: "#f5c542" }
  };

  if (simulatedTraceIndex === null) {
    Plotly.addTraces(mainChart, trace);
    simulatedTraceIndex = mainChart.data.length - 1;
  } else {
    Plotly.restyle(mainChart, {
      x: [trace.x],
      y: [trace.y]
    }, [simulatedTraceIndex]);
  }

  simulationActive = true;
}

function clearSimulationLine() {
  if (simulatedTraceIndex !== null) {
    Plotly.deleteTraces(mainChart, simulatedTraceIndex);
    simulatedTraceIndex = null;
  }
  simulationActive = false;
}

function showSimulationMetrics(metrics) {
  for (const key in metrics) {
    const el = document.getElementById("kpi-" + key.replace("_", "-"));
    if (!el) continue;

    const simLine = el.querySelector(".metric-sim");
    simLine.innerText = metrics[key];
    simLine.classList.remove("d-none");
  }
}

function clearSimulationMetrics() {
  document.querySelectorAll(".metric-sim").forEach(el => {
    el.innerText = "";
    el.classList.add("d-none");
  });
}

async function simulate() {
  if (!ticker.value || !buyDate.value || !amount.value) {
    alert("Please enter date, ticker and cash amount");
    return;
  }

  const res = await fetch("/api/simulate/purchase", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({
      date: buyDate.value,
      ticker: ticker.value.toUpperCase(),
      cash: amount.value
    })
  });

  if (!res.ok) {
    const err = await res.text();
    alert(err);
    return;
  }

  window.location.reload();
}


async function undo() {
  await fetch("/api/simulate/reset", { method:"POST" });
  window.location.reload();
}

if (SIM_METRICS && SIM_NAV) {
  drawSimulationLine(SIM_NAV);
  showSimulationMetrics(SIM_METRICS);
}


const sim_ticker_select = document.getElementById("sim-ticker-select");
const sim_ticker = document.getElementById("sim-ticker");
const preview_select = document.getElementById("preview-select");
const preview_filter = document.getElementById("preview-filter");

function tickerOnChangeHandler(e, selector) {
    const val = e.target.value.toUpperCase();
    const filteredTickers = val.length > 0 ? tickers.filter(x => x.includes(val)) : tickers;
    selector.innerHTML = '';
    for (const ticker of filteredTickers) {
        const option = document.createElement("option")
        option.value = ticker;
        option.innerHTML = ticker;
        selector.appendChild(option);
    }
}

async function showPreview() {
  const ticker = preview_select.value;
  await cookieStore.set("preview", ticker);
  window.location.reload();
}
async function clearPreview() {
  await cookieStore.delete("preview");
  window.location.reload();
}

sim_ticker.addEventListener("input", (e) => tickerOnChangeHandler(e, sim_ticker_select));
preview_filter.addEventListener("input", (e) => tickerOnChangeHandler(e, preview_select));

if (PREVIEW_DATA) {
  Plotly.addTraces(mainChart, PREVIEW_DATA);
}