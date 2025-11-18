let mainChart = document.getElementById('main-chart');
Plotly.newPlot(mainChart, [{
x: [1, 2, 3, 4, 5],
y: [1, 2, 4, 8, 16] }], {
margin: { t: 0 } } );