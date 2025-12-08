const mainChart = document.getElementById('main-chart');
const SPDR = {{ spdr }};
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

let portfolioData = undefined;

submitButton.onclick = async (e) => {
    const file = inputFile.files[0];
    const text = JSON.parse(await file.text());
    const res = await axios.post("{{ api_route }}/portfolio", text);
    portfolioData = res.data["portfolio"] ?? [];
    historicalData = res.data["historical"]["asset"];
    inputFileForm.style.display = "none";

    for (const data of portfolioData) {
        const ticker = document.createElement("div");
        ticker.innerText = data["ticker"];
        const currentPrice = document.createElement("div");
        currentPrice.innerText = data["price close"];
        const shares = document.createElement("div");
        shares.innerText = data["shares"];
        const assetValue = document.createElement("div");
        assetValue.innerText = data["asset_value"];

        mainTable.appendChild(ticker);
        mainTable.appendChild(currentPrice);
        mainTable.appendChild(shares);
        mainTable.appendChild(assetValue);
    }


    const ratio = historicalData[0]["price close"] / SPDR["SPY"][0]["price close"];
    console.log(ratio)
    data = [{
        x: SPDR["SPY"].map(x => x["date"]),
        y: SPDR["SPY"].map(x => x["price close"] * ratio),
        name: "SPDR"
    }, {
        x: historicalData.map(x => x["date"]),
        y: historicalData.map(x => x["price close"]),
        name: "Asset"
    }];
    
    Plotly.newPlot(mainChart, data, { margin: { t: 0 }});
};