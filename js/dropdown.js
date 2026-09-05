/**
 * StreamRip Core - Custom Themed Dropdown Controller
 * Seamlessly replaces raw OS select popup menus with a Cal.com monochrome
 * custom dropdown while keeping underlying <select> state fully synchronized.
 */

function initCustomDropdowns() {
  document.querySelectorAll('.select-wrap').forEach((wrap) => {
    const select = wrap.querySelector('select');
    if (!select || wrap.dataset.customized) return;
    wrap.dataset.customized = 'true';

    // Visually hide native select while keeping it in the DOM for forms/engines
    select.style.display = 'none';

    // Hide existing static SVG chevron
    const oldChevron = wrap.querySelector('.select-chevron');
    if (oldChevron) oldChevron.style.display = 'none';

    // 1. Create custom trigger
    const trigger = document.createElement('button');
    trigger.type = 'button';
    trigger.className = 'custom-select-trigger';
    trigger.setAttribute('aria-haspopup', 'listbox');
    trigger.setAttribute('aria-expanded', 'false');

    const label = document.createElement('span');
    label.className = 'custom-select-label';

    const updateLabel = () => {
      const selectedOption = select.options[select.selectedIndex] || select.options[0];
      label.textContent = selectedOption ? selectedOption.text : '';
    };
    updateLabel();

    const arrow = document.createElement('span');
    arrow.className = 'custom-select-arrow';
    arrow.innerHTML = `<svg width="10" height="6" viewBox="0 0 10 6" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M1 1L5 5L9 1"/></svg>`;

    trigger.appendChild(label);
    trigger.appendChild(arrow);
    wrap.appendChild(trigger);

    // 2. Create floating custom menu
    const menu = document.createElement('div');
    menu.className = 'custom-select-menu';
    menu.setAttribute('role', 'listbox');

    function renderItems() {
      menu.innerHTML = '';
      Array.from(select.options).forEach((opt, idx) => {
        const item = document.createElement('div');
        item.className = 'custom-select-item';
        item.setAttribute('role', 'option');

        const isSelected = idx === select.selectedIndex;
        if (isSelected) {
          item.classList.add('selected');
        }

        const textSpan = document.createElement('span');
        textSpan.textContent = opt.text;
        item.appendChild(textSpan);

        if (isSelected) {
          const check = document.createElement('span');
          check.className = 'custom-select-check';
          check.innerHTML = `<svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 6L5 9L10 3"/></svg>`;
          item.appendChild(check);
        }

        item.addEventListener('click', (e) => {
          e.stopPropagation();
          select.selectedIndex = idx;
          updateLabel();
          select.dispatchEvent(new Event('change', { bubbles: true }));
          closeMenu();
          renderItems();
        });

        menu.appendChild(item);
      });
    }

    renderItems();
    wrap.appendChild(menu);

    // Auto-update if options are modified dynamically (e.g. video vs audio format switch)
    const observer = new MutationObserver(() => {
      updateLabel();
      renderItems();
    });
    observer.observe(select, { childList: true });

    function checkPosition() {
      const rect = trigger.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      if (spaceBelow < 230 && rect.top > 230) {
        menu.classList.add('drop-up');
      } else {
        menu.classList.remove('drop-up');
      }
    }

    function openMenu() {
      // Close any other open custom dropdowns across the page
      document.querySelectorAll('.custom-select-menu.open').forEach((m) => {
        if (m !== menu) {
          m.classList.remove('open');
          m.closest('.select-wrap')?.querySelector('.custom-select-trigger')?.classList.remove('active');
        }
      });
      checkPosition();
      menu.classList.add('open');
      trigger.classList.add('active');
      trigger.setAttribute('aria-expanded', 'true');
    }

    function closeMenu() {
      menu.classList.remove('open');
      trigger.classList.remove('active');
      trigger.setAttribute('aria-expanded', 'false');
    }

    trigger.addEventListener('click', (e) => {
      e.stopPropagation();
      if (menu.classList.contains('open')) {
        closeMenu();
      } else {
        openMenu();
      }
    });

    select.addEventListener('change', () => {
      updateLabel();
      renderItems();
    });
  });

  // Global click outside listener
  document.addEventListener('click', () => {
    document.querySelectorAll('.custom-select-menu.open').forEach((m) => {
      m.classList.remove('open');
      m.closest('.select-wrap')?.querySelector('.custom-select-trigger')?.classList.remove('active');
    });
  });

  // Global Escape key listener
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.custom-select-menu.open').forEach((m) => {
        m.classList.remove('open');
        m.closest('.select-wrap')?.querySelector('.custom-select-trigger')?.classList.remove('active');
      });
    }
  });
}
