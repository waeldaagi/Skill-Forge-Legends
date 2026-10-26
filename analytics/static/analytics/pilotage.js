// Graphique du tableau de pilotage. Les valeurs viennent de json_script : aucun script en ligne.
document.addEventListener("DOMContentLoaded", function () {
  const source = document.getElementById("analytics-chart-data");
  const canvas = document.getElementById("analytics-chart");
  if (!source || !canvas || !window.Chart) {
    return;
  }
  const values = JSON.parse(source.textContent);
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  new window.Chart(canvas, {
    type: "bar",
    data: {
      labels: Object.keys(values),
      datasets: [{ label: "Valeur", data: Object.values(values), backgroundColor: "#6D28D9" }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: reducedMotion ? false : undefined,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
    },
  });
});
