import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterLinkActive } from '@angular/router';

type Theme = 'light' | 'dark' | 'system';

const STORAGE_KEY = 'sj-theme';

@Component({
  selector: 'app-nav',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive],
  template: `
    <nav>
      <div class="inner">
        <a class="brand" routerLink="/dashboard">
          <span class="mark" aria-hidden="true"></span>
          <span>Saint Jean <span class="brand-sub">Analyse de communautés</span></span>
        </a>

        <div class="links">
          <a routerLink="/dashboard" routerLinkActive="active">Tableau de bord</a>
          <a routerLink="/behavior" routerLinkActive="active">Comportement</a>
          <a routerLink="/posts" routerLinkActive="active">Publications</a>
          <a routerLink="/models" routerLinkActive="active">Modèles ML</a>
          <a routerLink="/quality" routerLinkActive="active">Qualité des données</a>
        </div>

        <button type="button" class="theme" (click)="cycleTheme()"
                [attr.aria-label]="'Thème : ' + themeLabel() + '. Cliquer pour changer.'"
                [title]="'Thème : ' + themeLabel()">
          <span aria-hidden="true">{{ themeIcon() }}</span>
        </button>
      </div>
    </nav>
  `,
  styles: [`
    nav {
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      position: sticky; top: 0; z-index: 10;
    }
    .inner {
      max-width: 1160px; margin: 0 auto;
      padding: var(--space-3) var(--space-5);
      display: flex; align-items: center; gap: var(--space-5);
      flex-wrap: wrap;
    }
    .brand {
      display: flex; align-items: center; gap: var(--space-2);
      font-weight: 600; font-size: 14px; color: var(--ink-primary);
      text-decoration: none; white-space: nowrap;
    }
    .brand-sub { color: var(--ink-muted); font-weight: 400; }
    .mark {
      width: 9px; height: 18px; border-radius: 3px; flex: none;
      background: linear-gradient(var(--series-1) 55%, var(--series-2) 55%);
    }

    .links { display: flex; gap: var(--space-4); flex-wrap: wrap; margin-left: auto; }
    .links a {
      color: var(--ink-secondary); text-decoration: none; font-size: 13px;
      padding: 5px 0; border-bottom: 2px solid transparent;
      transition: color .15s ease, border-color .15s ease;
    }
    .links a:hover { color: var(--ink-primary); }
    /* L'état actif ne repose pas sur la seule couleur : le trait sous le
       libellé le signale aussi, ce qui reste lisible en daltonisme. */
    .links a.active { color: var(--ink-primary); border-bottom-color: var(--series-1); font-weight: 500; }

    .theme {
      border: 1px solid var(--border); background: var(--surface-sunken);
      color: var(--ink-secondary); border-radius: var(--radius-sm);
      width: 30px; height: 30px; cursor: pointer; font-size: 14px; line-height: 1;
      display: inline-flex; align-items: center; justify-content: center;
      transition: border-color .15s ease;
    }
    .theme:hover { border-color: var(--border-strong); }

    @media (max-width: 720px) {
      .links { margin-left: 0; width: 100%; gap: var(--space-3); }
      .links a { font-size: 12.5px; }
    }
  `],
})
export class NavComponent {
  theme = signal<Theme>(this.readStored());

  constructor() {
    this.apply(this.theme());
  }

  /** Trois états plutôt que deux : « système » doit rester atteignable, sinon
      l'utilisateur ne peut plus rendre la main au réglage de son OS. */
  cycleTheme(): void {
    const order: Theme[] = ['system', 'light', 'dark'];
    const next = order[(order.indexOf(this.theme()) + 1) % order.length];
    this.theme.set(next);
    this.apply(next);
    try { localStorage.setItem(STORAGE_KEY, next); } catch { /* navigation privée */ }
  }

  themeIcon = () => ({ system: '◐', light: '☀', dark: '☾' })[this.theme()];
  themeLabel = () => ({ system: 'système', light: 'clair', dark: 'sombre' })[this.theme()];

  private apply(theme: Theme): void {
    const root = document.documentElement;
    if (theme === 'system') root.removeAttribute('data-theme');
    else root.setAttribute('data-theme', theme);
  }

  private readStored(): Theme {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === 'light' || stored === 'dark' || stored === 'system') return stored;
    } catch { /* localStorage indisponible : on retombe sur 'system' */ }
    return 'system';
  }
}
