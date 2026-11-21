// Prévia acessível da severidade (UC-03, passo 7). O cálculo é feito no servidor (ADR-06).
(function () {
  var script = document.currentScript || document.querySelector('script[data-url]');
  var url = script && script.getAttribute('data-url');
  var impacto = document.getElementById('id_impacto');
  var alcance = document.getElementById('id_alcance');
  var saida = document.getElementById('previa-severidade');
  if (!url || !impacto || !alcance || !saida) return;
  function atualizar() {
    if (!impacto.value || !alcance.value) { return; }
    fetch(url + '?impacto=' + encodeURIComponent(impacto.value) + '&alcance=' + encodeURIComponent(alcance.value), { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { if (d) { saida.textContent = 'Severidade calculada: ' + d.rotulo + ' (pontuação ' + d.pontuacao + ').'; } });
  }
  impacto.addEventListener('change', atualizar);
  alcance.addEventListener('change', atualizar);
})();
