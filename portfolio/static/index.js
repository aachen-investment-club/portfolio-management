const mainChart = document.getElementById('main-chart');
Plotly.react(mainChart, [{
x: [1, 2, 3, 4, 5],
y: [1, 2, 4, 8, 16] }], {
margin: { t: 0 } } );

const mainTable = document.getElementById('main-table');
const inputFileForm = document.getElementById('input-file-form');
const submitButton = document.getElementById('submit-button');
const inputFile = document.getElementById('input-file');

let portfolioData = undefined;
let historicalData = {};

submitButton.onclick = async (e) => {
    const file = inputFile.files[0];
    const text = JSON.parse(await file.text());
    const res = await axios.post("http://localhost:5000/api/portfolio", text);
    portfolioData = res.data.portfolio;
    historicalData = Object.entries(res.data.historical_data).map(
        ([ticker, value]) => 
        ({
            name: ticker,
            x: value.timestamp,
            y: value.open,
            mode: "lines+markers"
        })
    );
    Plotly.react(mainChart, historicalData, { margin: { t: 0 } })
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
};