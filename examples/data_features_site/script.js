(function () {
  const rcState = {};

  function setValueByName(name, value) {
    if (!name) return;
    const el = document.querySelector('[name="' + CSS.escape(name) + '"]');
    if (!el) return;
    if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT') {
      el.value = value == null ? '' : String(value);
    }
  }

  function renderShowAll(varName, idx, value) {
    const el = document.getElementById('rc-show-' + varName + '-' + idx);
    if (!el) return;
    try {
      el.textContent = JSON.stringify(value, null, 2);
    } catch (e) {
      el.textContent = String(value);
    }
  }

  async function handleFormSubmit(form) {
    const action = form.getAttribute('action');
    const method = (form.getAttribute('method') || 'get').toUpperCase();
    const data = new FormData(form);
    const obj = {};
    for (const [k, v] of data.entries()) obj[k] = v;

    if (!action) {
      alert('Form submitted (demo):
' + JSON.stringify(obj, null, 2));
      return;
    }

    try {
      const res = await fetch(action, { method, body: data });
      const text = await res.text();
      alert('Submitted to ' + action + ' (status ' + res.status + '):
' + text.slice(0, 500));
    } catch (err) {
      alert('Submit failed: ' + (err && err.message ? err.message : String(err)));
    }
  }

  function initForms() {
    const forms = document.querySelectorAll('form[data-rc-form]');
    forms.forEach((form) => {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        handleFormSubmit(form);
      });
    });
  }

  function runDataOps() {
    const ops = [{"op": "save", "key": "username", "value": "John", "var": null}, {"op": "get", "key": "username", "value": null, "var": "username"}, {"op": "delete", "key": "username", "value": null, "var": null}];
    ops.forEach((op) => {
      if (op.op === 'save') {
        localStorage.setItem(op.key, op.value);
      } else if (op.op === 'get') {
        const v = localStorage.getItem(op.key);
        if (op.var) {
          rcState[op.var] = v;
          setValueByName(op.var, v);
        }
      } else if (op.op === 'delete') {
        localStorage.removeItem(op.key);
      }
    });
  }

  async function runFetches() {
    const fetches = [{"url": "https://api.example.com/users", "var": "users"}];
    for (const f of fetches) {
      try {
        const res = await fetch(f.url);
        const ct = res.headers.get('content-type') || '';
        const data = ct.includes('application/json') ? await res.json() : await res.text();
        rcState[f.var] = data;
      } catch (err) {
        rcState[f.var] = { error: err && err.message ? err.message : String(err) };
      }
    }
  }

  function renderAllPanels() {
    const panels = [{"var": "users"}];
    panels.forEach((p, idx) => {
      renderShowAll(p.var, idx, rcState[p.var]);
    });
  }

  async function main() {
    initForms();
    runDataOps();
    await runFetches();
    renderAllPanels();
  }

  main();
})();
