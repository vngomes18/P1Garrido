// Graficos do dashboard (Aula 17). Os dados chegam da view via json_script: o Django continua dono dos dados.
(function () {
    function lerDados(id) {
        const el = document.getElementById(id);
        return el ? JSON.parse(el.textContent) : [];
    }

    const moeda = (v) => 'R$ ' + Number(v).toFixed(2).replace('.', ',');

    const porMes = lerDados('dados-mes');
    const canvasMes = document.getElementById('grafico-mes');
    if (canvasMes && porMes.length) {
        new Chart(canvasMes, {
            type: 'bar',
            data: {
                labels: porMes.map((d) => d.mes),
                datasets: [{ label: 'Faturamento', data: porMes.map((d) => d.total), backgroundColor: '#2c3e50' }],
            },
            options: {
                plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => moeda(c.parsed.y) } } },
                scales: { y: { beginAtZero: true, ticks: { callback: (v) => moeda(v) } } },
            },
        });
    }

    const porCategoria = lerDados('dados-categoria');
    const canvasCategoria = document.getElementById('grafico-categoria');
    if (canvasCategoria && porCategoria.length) {
        new Chart(canvasCategoria, {
            type: 'bar',
            data: {
                labels: porCategoria.map((d) => d.categoria),
                datasets: [{ label: 'Itens vendidos', data: porCategoria.map((d) => d.total), backgroundColor: '#3a7ca5' }],
            },
            options: {
                indexAxis: 'y',
                plugins: { legend: { display: false } },
                scales: { x: { beginAtZero: true, ticks: { precision: 0 } } },
            },
        });
    }
})();
