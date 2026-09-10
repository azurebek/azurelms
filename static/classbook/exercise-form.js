(() => {
  const kind = document.querySelector('[data-exercise-kind]');
  const help = document.getElementById('definitionHelp');
  const mapNode = document.getElementById('exerciseHelpMap');
  if (!kind || !help || !mapNode) return;
  const helpMap = JSON.parse(mapNode.textContent);
  const update = () => { help.textContent = helpMap[kind.value] || 'Mashq ma’lumotlarini kiriting.'; };
  kind.addEventListener('change', update);
  update();
})();
