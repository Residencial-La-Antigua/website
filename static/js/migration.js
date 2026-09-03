(() => {
  const root = document.documentElement;
  const themeButton = document.querySelector('[data-mig-theme-toggle]');
  const savedTheme = localStorage.getItem('siteTheme');
  const preferredTheme = window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light';

  function applyTheme(theme, persist = false) {
    root.dataset.theme = theme;
    document.body.dataset.theme = theme;
    if (persist) {
      localStorage.setItem('siteTheme', theme);
    }
    if (themeButton) {
      const nextTheme = theme === 'dark' ? 'claro' : 'oscuro';
      themeButton.setAttribute('aria-label', `Cambiar al tema ${nextTheme}`);
      themeButton.setAttribute('title', `Cambiar al tema ${nextTheme}`);
    }
  }

  applyTheme(savedTheme === 'dark' || savedTheme === 'light' ? savedTheme : preferredTheme);

  themeButton?.addEventListener('click', () => {
    applyTheme(root.dataset.theme === 'dark' ? 'light' : 'dark', true);
  });

  const menu = document.querySelector('[data-mig-menu]');
  const menuButton = document.querySelector('[data-mig-menu-toggle]');

  function closeMenu() {
    menu?.classList.remove('is-open');
    menuButton?.setAttribute('aria-expanded', 'false');
    menuButton?.setAttribute('aria-label', 'Abrir menú');
  }

  menuButton?.addEventListener('click', () => {
    const isOpen = menu?.classList.toggle('is-open') ?? false;
    menuButton.setAttribute('aria-expanded', String(isOpen));
    menuButton.setAttribute('aria-label', isOpen ? 'Cerrar menú' : 'Abrir menú');
  });

  menu?.addEventListener('click', (event) => {
    if (event.target.closest('a')) {
      closeMenu();
    }
  });

  document.addEventListener('click', (event) => {
    if (!menu?.contains(event.target) && !menuButton?.contains(event.target)) {
      closeMenu();
    }
  });

  const overlay = document.querySelector('[data-mig-dialog-overlay]');
  const dialog = overlay?.querySelector('[data-mig-dialog]');
  const content = overlay?.querySelector('[data-mig-dialog-content]');
  const closeButton = overlay?.querySelector('[data-mig-dialog-close]');
  let lastFocusedElement = null;

  if (!overlay || !dialog || !content || !closeButton) {
    return;
  }

  const focusableSelector = [
    'a[href]',
    'button:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
  ].join(',');

  function closeDialog() {
    overlay.hidden = true;
    document.body.classList.remove('mig-dialog-open');
    content.replaceChildren();
    lastFocusedElement?.focus();
    lastFocusedElement = null;
  }

  function openDialog(trigger) {
    const templateId = trigger.dataset.dialogTemplate;
    const template = templateId ? document.getElementById(templateId) : null;
    if (!(template instanceof HTMLTemplateElement)) {
      return;
    }

    lastFocusedElement = trigger;
    content.replaceChildren(template.content.cloneNode(true));
    dialog.classList.toggle('mig-dialog--wide', trigger.dataset.dialogWide === 'true');
    overlay.hidden = false;
    document.body.classList.add('mig-dialog-open');
    closeButton.focus();
  }

  document.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-dialog-template]');
    if (trigger) {
      event.preventDefault();
      openDialog(trigger);
    }
  });

  closeButton.addEventListener('click', closeDialog);
  overlay.addEventListener('click', (event) => {
    if (event.target === overlay) {
      closeDialog();
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && menu?.classList.contains('is-open')) {
      closeMenu();
      menuButton?.focus();
      return;
    }
    if (overlay.hidden) {
      return;
    }
    if (event.key === 'Escape') {
      closeDialog();
      return;
    }
    if (event.key !== 'Tab') {
      return;
    }

    const focusableElements = [...dialog.querySelectorAll(focusableSelector)];
    const first = focusableElements[0];
    const last = focusableElements.at(-1);
    if (!first || !last) {
      event.preventDefault();
    } else if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });
})();