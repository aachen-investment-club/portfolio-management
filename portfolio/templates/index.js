const mainChart = document.getElementById("main-chart");



// Portfolio NAV (from Flask → index.html)
const NAV = NAV_TS;

const data = [
    {
        x: NAV.map(x => x.date),
        y: NAV.map(x => x.nav),
        name: "Portfolio NAV",
        line: { width: 3 }
    }
];

const layout = {
    paper_bgcolor: "#3A3A3A",
    plot_bgcolor: "#3A3A3A",
    font: { color: "white" },
    margin: { t: 0 },
    xaxis: { gridcolor: "#666" },
    yaxis: { gridcolor: "#666" },
};

Plotly.newPlot(mainChart, data, layout, { responsive: true });



