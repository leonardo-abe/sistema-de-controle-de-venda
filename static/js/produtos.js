(function () {
  const { moeda, numero, escapeHtml } = window.Fmt;
  let paginaAtual = 1;
  let totalPaginas = 1;

  async function carregarFiltros() {
    const resp = await fetch("/produtos/api/filtros");
    if (!resp.ok) return;
    const data = await resp.json();

    const selectGrupo = document.getElementById("filtro-grupo");
    data.grupos.forEach((nome) => {
      const option = document.createElement("option");
      option.value = nome;
      option.textContent = nome;
      selectGrupo.appendChild(option);
    });

    const selectMarca = document.getElementById("filtro-marca");
    data.marcas.forEach((nome) => {
      const option = document.createElement("option");
      option.value = nome;
      option.textContent = nome;
      selectMarca.appendChild(option);
    });
  }

  function renderTabela(itens) {
    const tbody = document.getElementById("tabela-produtos");
    if (!itens.length) {
      tbody.innerHTML = '<tr><td colspan="7" style="color: var(--text-muted);">Nenhum produto encontrado.</td></tr>';
      return;
    }
    tbody.innerHTML = itens
      .map(
        (p) => `
      <tr>
        <td data-label="Cod.">${p.cod_prod}</td>
        <td data-label="Produto">${escapeHtml(p.nome)}</td>
        <td data-label="Grupo">${escapeHtml(p.grupo) || "-"}</td>
        <td data-label="Marca">${escapeHtml(p.marca) || "-"}</td>
        <td data-label="Qtd. vendida">${numero(p.quantidade_vendida)}</td>
        <td data-label="Valor vendido">${moeda(p.valor_vendido)}</td>
        <td data-label="Margem">${moeda(p.margem)}</td>
      </tr>`
      )
      .join("");
  }

  function renderPaginacao(pagina) {
    paginaAtual = pagina.pagina;
    totalPaginas = Math.max(1, Math.ceil(pagina.total / pagina.por_pagina));
    document.getElementById("paginacao-info").textContent = `${pagina.total} produtos - pagina ${paginaAtual} de ${totalPaginas}`;
    document.getElementById("btn-anterior").disabled = paginaAtual <= 1;
    document.getElementById("btn-proxima").disabled = paginaAtual >= totalPaginas;
  }

  async function carregar(params, pagina) {
    const query = new URLSearchParams({ ...params, pagina }).toString();
    const resp = await fetch(`/produtos/api?${query}`);
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

  carregarFiltros();
  carregar({}, 1);
})();
