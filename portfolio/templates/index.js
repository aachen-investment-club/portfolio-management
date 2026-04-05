const mainChart = document.getElementById("main-chart");

// Portfolio NAV (from Flask → index.html)
const NAV = NAV_TS;
const buyDate = document.getElementById("sim-date");
const ticker = document.getElementById("sim-ticker-select");
const amount = document.getElementById("sim-cash");
const sim_ticker_select = document.getElementById("sim-ticker-select");
const sim_ticker = document.getElementById("sim-ticker");


const preview_select = document.getElementById("preview-select");
const preview_filter = document.getElementById("preview-filter");





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



const portfolioUpload = document.getElementById('portfolioUpload');

if (portfolioUpload){
portfolioUpload.addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (!file) return;

    const statusDiv = document.getElementById('uploadStatus');
    statusDiv.innerHTML = '<span class="text-info">Uploading...</span>';

    const formData = new FormData();
    formData.append('file', file);

    axios.post('/upload_portfolio', formData, {
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

}

const removePortfolioButton = document.getElementById('removePortfolioButton')

if (removePortfolioButton){
removePortfolioButton.addEventListener('click', function () {
    const select = document.getElementById('removePortfolioSelection');
    const key = select.value;

    if (!key) return;

    if (!confirm('Are you sure you want to remove this portfolio?')) {
        return;
    }

    const statusDiv = document.getElementById('removeStatus');
    statusDiv.innerHTML = '<span class="text-info">Removing...</span>';

    const formData = new FormData();
    formData.append('portfolio', key);

    axios.post('/remove_portfolio', formData)
        .then(response => {
            statusDiv.innerHTML = '<span class="text-success">Removed!</span>';
            setTimeout(() => window.location.reload(), 1500);
        })
        .catch(error => {
            console.error(error);
            statusDiv.innerHTML = '<span class="text-danger">Removal failed.</span>';
        });
});

}
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




function queryFilterHandler(e, selector) {
  const val = e.target.value.toLowerCase().trim();
  const entries = Object.entries(TICKER_TO_NAME).filter(([t, name]) =>
    !val || t.toLowerCase().includes(val) || name.toLowerCase().includes(val)
  );
  selector.innerHTML = "";
  for (const [ticker, name] of entries) {
    const option = document.createElement("option");
    option.value = ticker;
    option.innerHTML = name;
    selector.appendChild(option);
  }
}




function setCookie(name, value, days = 7) {
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax`;
}

function getCookie(name) {
  return document.cookie
    .split("; ")
    .find(row => row.startsWith(name + "="))
    ?.split("=")[1];
}

function deleteCookie(name) {
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
}


function initializeMetricPopovers() {
  const popoverElements = document.querySelectorAll('[data-bs-toggle="popover"]');
  popoverElements.forEach((element) => {
    new bootstrap.Popover(element, {
      container: "body",
      html: true
    });
  });
}

initializeMetricPopovers();

async function showPreview() {

  const ticker = preview_select.value;
  //await cookieStore.set("preview", ticker);
  await setCookie("preview", ticker);
  window.location.reload();
}
async function clearPreview() {
  await deleteCookie("preview");
  window.location.reload();
}

preview_filter.addEventListener("input", (e) => queryFilterHandler(e, preview_select));
sim_ticker.addEventListener("input", (e) => queryFilterHandler(e, sim_ticker_select));

if (PREVIEW_DATA) {
  Plotly.addTraces(mainChart, PREVIEW_DATA);
}
