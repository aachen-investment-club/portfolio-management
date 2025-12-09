const mainChart = document.getElementById('main-chart');

const mainTable = document.getElementById('main-table');
const inputFileForm = document.getElementById('input-file-form');
const submitButton = document.getElementById('submit-button');
const inputFile = document.getElementById('input-file');
const darkLayout = {
    paper_bgcolor: '#3A3A3A',
    plot_bgcolor: '#3A3A3A',
    font: { color: 'white' },

    xaxis: {
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

Plotly.newPlot(mainChart, [{
    x: [1, 2, 3, 4, 5],
    y: [1, 2, 4, 8, 16]
}], layout, {responsive: true});

let portfolioData = undefined;

submitButton.onclick = async (e) => {
    const file = inputFile.files[0];
    const text = JSON.parse(await file.text());
    const res = await axios.post("http://localhost:5000/api/portfolio", text);
    portfolioData = res.data;
    inputFileForm.style.display = "none";

    for (const data of portfolioData) {
        const ticker = document.createElement("div");
        ticker.innerText = data["stock"];
        const currentPrice = document.createElement("div");
        currentPrice.innerText = data["current"];
        const shares = document.createElement("div");
        shares.innerText = data["shares"];
        const assetValue = document.createElement("div");
        assetValue.innerText = data["asset_value"];

        mainTable.appendChild(ticker);
        mainTable.appendChild(currentPrice);
        mainTable.appendChild(shares);
        mainTable.appendChild(assetValue);
    }

    const maxDD = portfolioData[0].max_drawdown;  // TEMPORARY SOURCE
    document.getElementById("kpi-maxdrawdown").innerText =
        (maxDD * 100).toFixed(0) + "%";
};