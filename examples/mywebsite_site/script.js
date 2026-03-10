(function () {
  const buttons = document.querySelectorAll('button[data-rc-button]');
  buttons.forEach((btn) => {
    btn.addEventListener('click', () => {
      alert(btn.textContent || 'Clicked!');
    });
  });

  const forms = document.querySelectorAll('form[data-rc-form]');
  forms.forEach((form) => {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const data = new FormData(form);
      const obj = {};
      for (const [k, v] of data.entries()) obj[k] = v;
      alert('Form submitted (demo):
' + JSON.stringify(obj, null, 2));
    });
  });
})();
