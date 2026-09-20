import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'app-nav',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive],
  template: `
    <nav>
      <div class="brand">Saint Jean — Analyse de communautés</div>
      <div class="links">
        <a routerLink="/dashboard" routerLinkActive="active">Tableau de bord</a>
        <a routerLink="/posts" routerLinkActive="active">Publications</a>
        <a routerLink="/models" routerLinkActive="active">Modèles ML</a>
        <a routerLink="/quality" routerLinkActive="active">Qualité des données</a>
      </div>
    </nav>
  `,
  styles: [`
    nav {
      display: flex; align-items: center; justify-content: space-between;
      padding: 12px 24px; background: #14213d; color: #fff; font-family: sans-serif;
      flex-wrap: wrap; gap: 10px;
    }
    .brand { font-weight: 600; }
    .links { display: flex; gap: 16px; }
    .links a { color: #cbd5e1; text-decoration: none; font-size: 14px; padding: 4px 0; border-bottom: 2px solid transparent; }
    .links a.active { color: #fff; border-bottom-color: #fca311; }
  `],
})
export class NavComponent {}
