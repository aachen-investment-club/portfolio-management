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

Plotly.newPlot(mainChart, data, { margin: { t: 0 }});
