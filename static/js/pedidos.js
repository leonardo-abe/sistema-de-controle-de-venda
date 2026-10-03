(function () {
  const { moeda, percentual, escapeHtml, badgeSituacao } = window.Fmt;
  let paginaAtual = 1;
  let totalPaginas = 1;

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

  function renderTabela(itens) {
    const tbody = document.getElementById("tabela-pedidos");
    if (!itens.length) {
      tbody.innerHTML = '<tr><td colspan="8" style="color: var(--text-muted);">Nenhum pedido encontrado.</td></tr>';
      return;
    }
    tbody.innerHTML = itens
      .map(
        (p) => `
      <tr>
        <td data-label="Pedido"><a class="table-link" href="/pedidos/${p.loja}/${p.pedido}">${p.pedido}</a></td>
        <td data-label="Data">${p.data}</td>
        <td data-label="Vendedor">${escapeHtml(p.vendedor) || "-"}</td>
        <td data-label="Cliente">${escapeHtml(p.cliente) || "-"}</td>
        <td data-label="Total">${moeda(p.total)}</td>
        <td data-label="% Desconto">${percentual(p.perc_desconto)}</td>
        <td data-label="Valor liquido">${moeda(p.valor_liquido)}</td>
        <td data-label="Situacao">${badgeSituacao(p.situacao, p.perc_desconto)}</td>
      </tr>`
      )
      .join("");
  }

  function renderPaginacao(pagina) {
    paginaAtual = pagina.pagina;
    totalPaginas = Math.max(1, Math.ceil(pagina.total / pagina.por_pagina));
    document.getElementById("paginacao-info").textContent = `${pagina.total} pedidos - pagina ${paginaAtual} de ${totalPaginas}`;
    document.getElementById("btn-anterior").disabled = paginaAtual <= 1;
    document.getElementById("btn-proxima").disabled = paginaAtual >= totalPaginas;
  }

  async function carregar(params, pagina) {
    const query = new URLSearchParams({ ...params, pagina }).toString();
    const resp = await fetch(`/pedidos/api?${query}`);
    if (!resp.ok) return;
    const data = await resp.json();
    renderTabela(data.itens);
    renderPaginacao(data);
  }

  function filtrosAtuais() {
    const form = document.getElementById("filtros-form");
    const formData = new FormData(form);
    const params = Object.fromEntries(formData.entries());
    Object.keys(params).forEach((key) => {
      if (!params[key]) delete params[key];
    });
    return params;
  }

  const form = document.getElementById("filtros-form");
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    carregar(filtrosAtuais(), 1);
  });

  document.getElementById("btn-limpar").addEventListener("click", () => {
    form.reset();
    carregar({}, 1);
  });

  document.getElementById("btn-anterior").addEventListener("click", () => {
    if (paginaAtual > 1) carregar(filtrosAtuais(), paginaAtual - 1);
  });

  document.getElementById("btn-proxima").addEventListener("click", () => {
    if (paginaAtual < totalPaginas) carregar(filtrosAtuais(), paginaAtual + 1);
  });

  const buscaInicial = new URLSearchParams(window.location.search).get("busca");
  if (buscaInicial) {
    document.querySelector('#filtros-form input[name="busca"]').value = buscaInicial;
  }

  carregarFiltros();
  carregar(buscaInicial ? { busca: buscaInicial } : {}, 1);
})();
