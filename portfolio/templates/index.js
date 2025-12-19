const mainChart = document.getElementById('main-chart');
const SPDR = {{ spdr }};
const historicalData = {{ historical_data }}
let data = [{
    x: SPDR["SPY"].map(x => x["date"]),
    y: SPDR["SPY"].map(x => x["price close"]),
    name: "SPDR"
}];


Plotly.react(mainChart, data, {
margin: { t: 0 } } );

const mainTable = document.getElementById('main-table');
const inputFileForm = document.getElementById('input-file-form');
const submitButton = document.getElementById('submit-button');
const inputFile = document.getElementById('input-file');
const darkLayout = {
    paper_bgcolor: '#3A3A3A',
    plot_bgcolor: '#3A3A3A',
    font: { color: 'white' },

    xaxis: {
        type: "date",  
        color: "#dddddd",
        gridcolor: '#666'
    },
    yaxis: {
        color: "#dddddd",
        gridcolor: '#666'
    },
    legend: {
        font: { color: 'white' },
        bgcolor: '#3A3A3A'
    }
};
const layout = {
    ...darkLayout,
    margin: { t: 0 }
};

const ratio = historicalData[0]["price close"] / SPDR["SPY"][0]["price close"];
data = [{
    x: SPDR["SPY"].map(x => x["date"]),
    y: SPDR["SPY"].map(x => x["price close"] * ratio),
    name: "SPDR"
}, {
    x: historicalData.map(x => x["date"]),
    y: historicalData.map(x => x["price close"]),
    name: "Asset"
}];

Plotly.newPlot(mainChart, data, {
    ...darkLayout,
    margin: { t: 0 }
}, { responsive: true });

axios.get("/api/portfolio/metrics")
  .then(res => {
    const m = res.data;
    
    document.getElementById("total-portfolio-value").innerText =
      `$${m.total_value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
    document.getElementById("kpi-total-return").innerText = `${m.total_return.toFixed(2)}%`;
    document.getElementById("kpi-cagr").innerText = `${m.cagr.toFixed(2)}%`;
    document.getElementById("kpi-volatility").innerText = `${(m.volatility * 100).toFixed(2)}%`;
    document.getElementById("kpi-sharpe").innerText = m.sharpe.toFixed(2);
    document.getElementById("kpi-beta").innerText = m.beta.toFixed(2);
    document.getElementById("kpi-jalpha").innerText = `${m.alpha.toFixed(2)}%`;
    document.getElementById("kpi-maxdrawdown").innerText = `${m.max_drawdown.toFixed(2)}%`;
    document.getElementById("kpi-var").innerText = `${m.value_at_risk.toFixed(2)}`;
  });

  axios.get("/api/portfolio/positions")
  .then(res => {
    const positions = res.data;
    const container = document.getElementById("positions-list");

    container.innerHTML = "";

    positions.forEach(p => {
      const price = Number(p.price);
      const value = Number(p.value);

      if (!Number.isFinite(price) || !Number.isFinite(value)) {
        console.warn("Skipping invalid position:", p);
        return;
      }

      const row = document.createElement("div");
      row.className = "d-flex justify-content-between py-2 border-bottom";

      row.innerHTML = `
        <div>
          <div class="fs-5 fw-semibold">${p.ticker}</div>
          <small>${p.shares} shares</small>
        </div>
        <div class="text-end">
          <div>$${price.toFixed(2)}</div>
          <small class="text-muted">$${value.toLocaleString()}</small>
        </div>
      `;

      container.appendChild(row);
    });
  })
  .catch(err => {
    console.error("Positions error:", err);
  });

