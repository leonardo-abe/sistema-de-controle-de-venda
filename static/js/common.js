window.Fmt = (function () {
  const moeda = (valor) =>
    new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(valor || 0);

  const numero = (valor) => new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 }).format(valor || 0);

  const percentual = (valor) => `${(valor || 0).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}%`;

  const escapeHtml = (value) => {
    const div = document.createElement("div");
    div.textContent = value == null ? "" : String(value);
    return div.innerHTML;
  };

  function badgeSituacao(situacao, percDesconto) {
    if (situacao && situacao.trim()) {
      return `<span class="badge badge-admin">${escapeHtml(situacao)}</span>`;
    }
    if (percDesconto >= 50) {
      return `<span class="badge badge-flag">Desconto alto</span>`;
    }
    return "-";
  }

  return { moeda, numero, percentual, escapeHtml, badgeSituacao };
})();
