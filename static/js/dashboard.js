(function () {
  const root = getComputedStyle(document.documentElement);
  const color = (name) => root.getPropertyValue(name).trim();

  const palette = [
    color("--series-1"),
    color("--series-2"),
    color("--series-3"),
    color("--series-4"),
    color("--series-5"),
    color("--series-6"),
    color("--series-7"),
    color("--series-8"),
  ];

  const textSecondary = color("--text-secondary");
  const gridline = color("--gridline");

  Chart.defaults.font.family = "system-ui, -apple-system, 'Segoe UI', sans-serif";
  Chart.defaults.color = textSecondary;
  Chart.defaults.borderColor = gridline;

  const moeda = (valor) =>
    new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(valor || 0);

  const numero = (valor) => new Intl.NumberFormat("pt-BR").format(valor || 0);

  const charts = {};

  function renderBar(id, labels, data, { horizontal = false, colorIndex = 0 } = {}) {
    const ctx = document.getElementById(id).getContext("2d");
    if (charts[id]) charts[id].destroy();
    charts[id] = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            data,
            backgroundColor: palette[colorIndex],
            borderRadius: 4,
            maxBarThickness: 36,
          },
        ],
      },
      options: {
        indexAxis: horizontal ? "y" : "x",
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: horizontal } },
          y: { grid: { display: !horizontal } },
        },
      },
    });
  }

  function renderLine(id, labels, data) {
    const ctx = document.getElementById(id).getContext("2d");
    if (charts[id]) charts[id].destroy();
    charts[id] = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            data,
            borderColor: palette[0],
            backgroundColor: palette[0] + "1a",
            fill: true,
            tension: 0.25,
            pointRadius: 3,
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
      },
    });
  }

  function renderDoughnut(id, labels, data) {
    const ctx = document.getElementById(id).getContext("2d");
    if (charts[id]) charts[id].destroy();
    charts[id] = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels,
        datasets: [{ data, backgroundColor: palette, borderWidth: 2, borderColor: color("--surface-1") }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom" } },
      },
    });
  }

  function renderTrend(id, atual, anterior, { inverso = false } = {}) {
    const el = document.getElementById(id);
    if (!el) return;
    if (anterior === null || anterior === undefined || anterior === 0) {
      el.textContent = "";
      el.className = "kpi-trend";
      return;
    }
    const delta = ((atual - anterior) / Math.abs(anterior)) * 100;
    const subiu = delta >= 0;
    const bom = inverso ? !subiu : subiu;
    el.className = "kpi-trend " + (bom ? "up" : "down");
    const seta = subiu ? "▲" : "▼";
    el.textContent = `${seta} ${Math.abs(delta).toFixed(1)}% vs periodo anterior`;
  }

  function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value == null ? "" : String(value);
    return div.innerHTML;
  }

  function badgeSituacao(situacao, percDesconto) {
    if (situacao && situacao.trim()) {
      return `<span class="badge badge-admin">${escapeHtml(situacao)}</span>`;
    }
    if (percDesconto >= 50) {
      return `<span class="badge" style="background: rgba(208,59,59,0.12); color: var(--critical);">Desconto alto</span>`;
    }
    return "-";
  }

  function renderTabelaAuditoria(pedidos) {
    const tbody = document.getElementById("tabela-auditoria");
    if (!pedidos.length) {
      tbody.innerHTML = '<tr><td colspan="9" style="color: var(--text-muted);">Nenhum pedido sinalizado neste periodo.</td></tr>';
      return;
    }
    tbody.innerHTML = pedidos
      .map(
        (p) => `
      <tr>
        <td data-label="Pedido"><a class="table-link" href="/pedidos/${p.loja}/${p.pedido}">${p.pedido}</a></td>
        <td data-label="Data">${p.data}</td>
        <td data-label="Vendedor">${escapeHtml(p.vendedor) || "-"}</td>
        <td data-label="Cliente">${escapeHtml(p.cliente) || "-"}</td>
        <td data-label="Total">${moeda(p.total)}</td>
        <td data-label="% Desconto">${p.perc_desconto.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}%</td>
        <td data-label="Valor desconto">${moeda(p.valor_desconto)}</td>
        <td data-label="Valor liquido">${moeda(p.valor_liquido)}</td>
        <td data-label="Situacao">${badgeSituacao(p.situacao, p.perc_desconto)}</td>
      </tr>`
      )
      .join("");
  }

  async function carregarFiltros() {
    const resp = await fetch("/api/dashboard/filtros");
    if (!resp.ok) return;
    const data = await resp.json();

    const selectVendedor = document.getElementById("filtro-vendedor");
    data.vendedores.forEach((nome) => {
      const option = document.createElement("option");
      option.value = nome;
      option.textContent = nome;
      selectVendedor.appendChild(option);
    });

    const selectPagamento = document.getElementById("filtro-pagamento");
    data.formas_pagamento.forEach((tipo) => {
      const option = document.createElement("option");
      option.value = tipo;
      option.textContent = tipo;
      selectPagamento.appendChild(option);
    });
  }

  async function carregar(params) {
    const query = new URLSearchParams(params).toString();
    const resp = await fetch(`/api/dashboard/resumo?${query}`);
    if (!resp.ok) return;
    const data = await resp.json();
    const anterior = data.kpis_anterior;

    document.getElementById("kpi-pedidos").textContent = numero(data.kpis.total_pedidos);
    document.getElementById("kpi-valor").textContent = moeda(data.kpis.valor_total_liquido);
    document.getElementById("kpi-ticket").textContent = moeda(data.kpis.ticket_medio);
    document.getElementById("kpi-desconto").textContent = moeda(data.kpis.total_desconto);
    document.getElementById("kpi-itens").textContent = numero(data.kpis.total_itens_vendidos);
    document.getElementById("kpi-custo").textContent = moeda(data.kpis.custo_total);
    document.getElementById("kpi-margem").textContent = moeda(data.kpis.margem_bruta);
    document.getElementById("kpi-margem-percentual").textContent = `${data.kpis.margem_percentual.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}% de margem`;

    renderTrend("kpi-pedidos-trend", data.kpis.total_pedidos, anterior && anterior.total_pedidos);
    renderTrend("kpi-valor-trend", data.kpis.valor_total_liquido, anterior && anterior.valor_total_liquido);
    renderTrend("kpi-ticket-trend", data.kpis.ticket_medio, anterior && anterior.ticket_medio);
    renderTrend("kpi-desconto-trend", data.kpis.total_desconto, anterior && anterior.total_desconto, { inverso: true });
    renderTrend("kpi-itens-trend", data.kpis.total_itens_vendidos, anterior && anterior.total_itens_vendidos);
    renderTrend("kpi-custo-trend", data.kpis.custo_total, anterior && anterior.custo_total, { inverso: true });
    renderTrend("kpi-margem-trend", data.kpis.margem_bruta, anterior && anterior.margem_bruta);

    renderLine(
      "chart-vendas-dia",
      data.vendas_por_dia.map((p) => p.chave),
      data.vendas_por_dia.map((p) => p.valor)
    );

    renderDoughnut(
      "chart-pagamento",
      data.formas_pagamento.map((p) => p.chave),
      data.formas_pagamento.map((p) => p.valor)
    );

    renderBar(
      "chart-vendedor",
      data.vendas_por_vendedor.map((p) => p.chave),
      data.vendas_por_vendedor.map((p) => p.valor),
      { horizontal: true, colorIndex: 0 }
    );

    renderBar(
      "chart-produtos",
      data.top_produtos.map((p) => p.chave),
      data.top_produtos.map((p) => p.valor),
      { horizontal: true, colorIndex: 4 }
    );

    renderBar(
      "chart-grupos",
      data.top_grupos.map((p) => p.chave),
      data.top_grupos.map((p) => p.valor),
      { horizontal: true, colorIndex: 2 }
    );

    renderBar(
      "chart-margem",
      data.margem_por_grupo.map((p) => p.chave),
      data.margem_por_grupo.map((p) => p.valor),
      { horizontal: true, colorIndex: 5 }
    );

    renderBar(
      "chart-cidade",
      data.pedidos_por_cidade.map((p) => p.chave),
      data.pedidos_por_cidade.map((p) => p.valor),
      { horizontal: true, colorIndex: 1 }
    );

    renderDoughnut(
      "chart-cliente",
      data.identificacao_cliente.map((p) => p.chave),
      data.identificacao_cliente.map((p) => p.valor)
    );

    document.getElementById("kpi-auditoria-total").textContent = numero(data.auditoria_resumo.total_pedidos);
    document.getElementById("kpi-auditoria-valor").textContent = moeda(data.auditoria_resumo.valor_desconto_total);

    renderBar(
      "chart-auditoria-vendedor",
      data.auditoria_por_vendedor.map((p) => p.chave),
      data.auditoria_por_vendedor.map((p) => p.valor),
      { horizontal: true, colorIndex: 1 }
    );

    renderTabelaAuditoria(data.auditoria_pedidos);
  }

  const form = document.getElementById("filtros-form");
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    const params = Object.fromEntries(formData.entries());
    Object.keys(params).forEach((key) => {
      if (!params[key]) delete params[key];
    });
    carregar(params);
  });

  document.getElementById("btn-limpar").addEventListener("click", () => {
    form.reset();
    carregar({});
  });

  carregarFiltros();
  carregar({});
})();
