// Drawn icons: one 24-unit grid, one stroke weight, round caps and joins.
// Same shapes as app/ui/icons.py in the desktop app.
const PATHS = {
  close: '<path d="M6 6l12 12M18 6L6 18"/>',
  arrow_right: '<path d="M4 12h16M14 6l6 6-6 6"/>',
  chevron_left: '<path d="M15 5l-7 7 7 7"/>',
  save: '<path d="M12 3v11M7 9.5l5 5 5-5"/><path d="M4 16v2a3 3 0 0 0 3 3h10a3 3 0 0 0 3-3v-2"/>',
  alert: '<circle cx="12" cy="12" r="9"/><path d="M12 7.5V13M12 16.6v.1"/>',
};

export const icon = (name, cls = "") =>
  `<svg class="icon ${cls}" viewBox="0 0 24 24" aria-hidden="true">${PATHS[name]}</svg>`;

/** Empty-state icon: a tinted disc with an arrow dropping into a tray. */
export const hero = () =>
  `<svg class="hero" viewBox="0 0 72 72" aria-hidden="true">
    <circle cx="36" cy="36" r="36" fill="var(--emerald-soft)"/>
    <g transform="translate(15.9 15.9) scale(1.68)" fill="none" stroke="var(--champagne)" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">${PATHS.save}</g>
  </svg>`;
