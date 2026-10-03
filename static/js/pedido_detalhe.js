(function () {
  const { moeda, numero, percentual, escapeHtml, badgeSituacao } = window.Fmt;

  function renderCabecalho(p) {
    return `
    <div class="grid grid-kpis" style="margin-bottom: 16px;">
      <div class="card kpi-card">
        <span class="kpi-label">Cliente</span>
        <div class="kpi-value" style="font-size: 16px;">${escapeHtml(p.cliente) || "Nao identificado"}</div>
      </div>
      <div class="card kpi-card">
        <span class="kpi-label">Vendedor</span>
        <div class="kpi-value" style="font-size: 16px;">${escapeHtml(p.vendedor) || "-"}</div>
      </div>
      <div class="card kpi-card">
        <span class="kpi-label">Data / hora</span>
        <div class="kpi-value" style="font-size: 16px;">${p.data} ${p.hora}</div>
      </div>
      <div class="card kpi-card">
        <span class="kpi-label">Cidade / bairro</span>
        <div class="kpi-value" style="font-size: 16px;">${escapeHtml(p.cidade) || "-"} ${p.bairro ? "/ " + escapeHtml(p.bairro) : ""}</div>
      </div>
      <div class="card kpi-card">
        <span class="kpi-label">Total</span>
        <div class="kpi-value">${moeda(p.total)}</div>
      </div>
      <div class="card kpi-card">
        <span class="kpi-label">Desconto</span>
        <div class="kpi-value">${moeda(p.valor_desconto)}</div>
        <div class="kpi-trend">${percentual(p.perc_desconto)}</div>
      </div>
      <div class="card kpi-card">
        <span class="kpi-label">Valor liquido</span>
        <div class="kpi-value">${moeda(p.valor_liquido)}</div>
      </div>
      <div class="card kpi-card">
        <span class="kpi-label">Situacao</span>
        <div class="kpi-value" style="font-size: 16px;">${badgeSituacao(p.situacao, p.perc_desconto)}</div>
      </div>
    </div>`;
  }

  function renderItens(itens) {
    if (!itens.length) {
      return '<p style="color: var(--text-muted);">Nenhum item neste pedido.</p>';
    }
    const linhas = itens
      .map((i) => {
        const corMargem = i.margem < 0 ? "var(--critical)" : "var(--good)";
        return `
      <tr>
        <td data-label="Cod.">${i.cod_prod}</td>
        <td data-label="Produto">${escapeHtml(i.produto)}</td>
        <td data-label="Grupo">${escapeHtml(i.grupo) || "-"}</td>
        <td data-label="Qtd.">${numero(i.quantidade)} ${escapeHtml(i.unidade) || ""}</td>
        <td data-label="Valor unit.">${moeda(i.valor_unitario)}</td>
        <td data-label="Valor total">${moeda(i.valor_total)}</td>
        <td data-label="Custo">${moeda(i.custo)}</td>
        <td data-label="Margem" style="color: ${corMargem}; font-weight: 600;">${moeda(i.margem)}</td>
        <td data-label="Margem %" style="color: ${corMargem}; font-weight: 600;">${percentual(i.margem_percentual)}</td>
      </tr>`;
      })
      .join("");
    return `
    <div class="card table-scroll" style="margin-bottom: 16px;">
      <p class="chart-title">Itens vendidos</p>
      <table>
        <thead>
          <tr>
            <th>Cod.</th><th>Produto</th><th>Grupo</th><th>Qtd.</th><th>Valor unit.</th><th>Valor total</th><th>Custo</th><th>Margem</th><th>Margem %</th>
          </tr>
        </thead>
        <tbody>${linhas}</tbody>
      </table>
    </div>`;
  }

  function renderPagamentos(pagamentos) {
    if (!pagamentos.length) {
      return '<p style="color: var(--text-muted);">Nenhum pagamento registrado.</p>';
    }
    const linhas = pagamentos
      .map(
        (p) =>
          `<tr><td data-label="Forma">${escapeHtml(p.tipo_pagamento)}</td><td data-label="Valor">${moeda(p.valor)}</td></tr>`
      )
      .join("");
    return `
    <div class="card table-scroll">
      <p class="chart-title">Pagamentos</p>
      <table>
        <thead><tr><th>Forma</th><th>Valor</th></tr></thead>
        <tbody>${linhas}</tbody>
      </table>
    </div>`;
  }

  async function carregar() {
    const { loja, pedido } = window.__PEDIDO__;
    const resp = await fetch(`/pedidos/api/${loja}/${pedido}`);
    const container = document.getElementById("conteudo-pedido");
    if (!resp.ok) {
      container.innerHTML = '<div class="alert alert-error">Pedido nao encontrado.</div>';
      return;
    }
    const data = await resp.json();
    container.innerHTML = renderCabecalho(data) + renderItens(data.itens) + renderPagamentos(data.pagamentos);
  }

  carregar();
})();
