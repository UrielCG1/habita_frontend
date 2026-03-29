(function () {
  const payloadNode = document.getElementById("owner-dashboard-chart-data");
  if (!payloadNode || typeof Chart === "undefined") return;

  const payload = JSON.parse(payloadNode.textContent);

  const palette = {
    primary: "#004C6D",
    accent: "#F6C324",
    dark: "#3A3A3A",
    softBlue: "#C9E8FF",
    softGray: "#F2F2F2",
    green: "#10B981",
    yellow: "#F59E0B",
    red: "#EF4444",
    border: "rgba(0, 76, 109, 0.08)",
    text: "#3A3A3A",
    muted: "#6B7280",
    white: "#FFFFFF",
  };

  Chart.defaults.font.family = "Inter, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
  Chart.defaults.color = palette.muted;
  Chart.defaults.borderColor = palette.border;

  function buildDoughnut(canvasId, labels, data, colors) {
    const el = document.getElementById(canvasId);
    if (!el) return;

    new Chart(el, {
      type: "doughnut",
      data: {
        labels,
        datasets: [
          {
            data,
            backgroundColor: colors,
            borderColor: palette.white,
            borderWidth: 2,
            hoverOffset: 6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "66%",
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              usePointStyle: true,
              pointStyle: "circle",
              boxWidth: 10,
              padding: 16,
            },
          },
          tooltip: {
            backgroundColor: "#0F172A",
            titleColor: "#fff",
            bodyColor: "#fff",
            padding: 12,
          },
        },
      },
    });
  }

  function buildHorizontalBar(canvasId, labels, requests, pending) {
    const el = document.getElementById(canvasId);
    if (!el) return;

    new Chart(el, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Solicitudes",
            data: requests,
            backgroundColor: palette.primary,
            borderRadius: 8,
            barThickness: 18,
          },
          {
            label: "Pendientes",
            data: pending,
            backgroundColor: palette.accent,
            borderRadius: 8,
            barThickness: 18,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            beginAtZero: true,
            ticks: {
              precision: 0,
            },
            grid: {
              color: "rgba(0, 76, 109, 0.06)",
            },
          },
          y: {
            grid: {
              display: false,
            },
          },
        },
        plugins: {
          legend: {
            position: "top",
            align: "start",
            labels: {
              usePointStyle: true,
              pointStyle: "circle",
              boxWidth: 10,
            },
          },
          tooltip: {
            backgroundColor: "#0F172A",
            titleColor: "#fff",
            bodyColor: "#fff",
            padding: 12,
          },
        },
      },
    });
  }

  function buildVerticalBar(canvasId, labels, data) {
    const el = document.getElementById(canvasId);
    if (!el) return;

    new Chart(el, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Calificaciones",
            data,
            backgroundColor: [
              palette.primary,
              palette.softBlue,
              palette.accent,
              "#D1D5DB",
              "#E5E7EB",
            ],
            borderRadius: 8,
            maxBarThickness: 42,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              precision: 0,
            },
            grid: {
              color: "rgba(0, 76, 109, 0.06)",
            },
          },
          x: {
            grid: {
              display: false,
            },
          },
        },
        plugins: {
          legend: {
            display: false,
          },
          tooltip: {
            backgroundColor: "#0F172A",
            titleColor: "#fff",
            bodyColor: "#fff",
            padding: 12,
          },
        },
      },
    });
  }

  buildDoughnut(
    "portfolioStatusChart",
    payload.portfolio_status.labels,
    payload.portfolio_status.data,
    [palette.green, palette.primary, palette.softBlue]
  );

  buildDoughnut(
    "requestFlowChart",
    payload.request_flow.labels,
    payload.request_flow.data,
    [palette.accent, palette.green, palette.primary]
  );

  buildHorizontalBar(
    "topPropertiesChart",
    payload.top_properties.labels,
    payload.top_properties.requests,
    payload.top_properties.pending
  );

  buildVerticalBar(
    "ratingBreakdownChart",
    payload.rating_breakdown.labels,
    payload.rating_breakdown.data
  );
})();