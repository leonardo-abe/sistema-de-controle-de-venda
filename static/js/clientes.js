(function () {
  const { moeda, numero, escapeHtml } = window.Fmt;
  let paginaAtual = 1;
  let totalPaginas = 1;

  function renderTabela(itens) {
    const tbody = document.getElementById("tabela-clientes");
    if (!itens.length) {
      tbody.innerHTML = '<tr><td colspan="6" style="color: var(--text-muted);">Nenhum cliente encontrado.</td></tr>';
      return;
    }
    tbody.innerHTML = itens
      .map(
        (c) => `
      <tr>
        <td data-label="Cliente"><a class="table-link" href="/pedidos?busca=${encodeURIComponent(c.cliente)}">${escapeHtml(c.cliente)}</a></td>
        <td data-label="Pedidos">${numero(c.total_pedidos)}</td>
        <td data-label="Valor total">${moeda(c.valor_total)}</td>
        <td data-label="Ticket medio">${moeda(c.ticket_medio)}</td>
        <td data-label="Ultima compra">${c.ultima_compra}</td>
        <td data-label="Sinalizados">${c.pedidos_sinalizados > 0 ? `<span class="badge badge-flag">${c.pedidos_sinalizados}</span>` : "-"}</td>
      </tr>`
      )
      .join("");
  }

  function renderPaginacao(pagina) {
    paginaAtual = pagina.pagina;
    totalPaginas = Math.max(1, Math.ceil(pagina.total / pagina.por_pagina));
    document.getElementById("paginacao-info").textContent = `${pagina.total} clientes - pagina ${paginaAtual} de ${totalPaginas}`;
    document.getElementById("btn-anterior").disabled = paginaAtual <= 1;
    document.getElementById("btn-proxima").disabled = paginaAtual >= totalPaginas;
  }

  async function carregar(params, pagina) {
    const query = new URLSearchParams({ ...params, pagina }).toString();
    const resp = await fetch(`/clientes/api?${query}`);
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

  carregar({}, 1);
})();
