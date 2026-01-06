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
    hovermode: "x unified"
};

Plotly.newPlot(mainChart, data, layout, { responsive: true });

document.getElementById('portfolioUpload').addEventListener('change', function(e) {
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
