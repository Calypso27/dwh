import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NavComponent } from '../shared/nav.component';
import { ApiService } from '../services/api.service';
import { DQCheck } from '../models/api.models';

@Component({
  selector: 'app-quality',
  standalone: true,
  imports: [CommonModule, NavComponent],
  template: `
    <app-nav />
    <div class="page">
      <h2>Journal de contrôle qualité</h2>
      <p class="hint">Teste <code>GET /dq-checks</code> — {{ checks().length }} contrôles journalisés.</p>

      <div class="summary">
        <div class="stat pass">{{ countByResult('PASS') }} PASS</div>
        <div class="stat warn">{{ countByResult('WARN') }} WARN</div>
        <div class="stat fail">{{ countByResult('FAIL') }} FAIL</div>
      </div>

      <table>
        <thead>
          <tr><th>Table</th><th>Contrôle</th><th>Résultat</th><th>Lignes vérifiées</th><th>Lignes en échec</th><th>Date</th></tr>
        </thead>
        <tbody>
          @for (c of checks(); track c.check_id) {
            <tr>
              <td>{{ c.table_name }}</td>
              <td>{{ c.check_name }}</td>
              <td><span class="tag" [class]="c.check_result.toLowerCase()">{{ c.check_result }}</span></td>
              <td>{{ c.rows_checked | number }}</td>
              <td>{{ c.rows_failed | number }}</td>
              <td>{{ c.checked_at | date: 'short' }}</td>
            </tr>
          }
        </tbody>
      </table>
    </div>
  `,
  styles: [`
    .page { max-width: 1000px; margin: 20px auto; font-family: sans-serif; padding: 0 16px; }
    .hint { font-size: 12px; color: #666; }
    .summary { display: flex; gap: 12px; margin: 16px 0; }
    .stat { padding: 8px 16px; border-radius: 6px; font-size: 14px; font-weight: 600; }
    .stat.pass { background: #d1fae5; color: #065f46; }
    .stat.warn { background: #fef3c7; color: #92400e; }
    .stat.fail { background: #fee2e2; color: #991b1b; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border: 1px solid #ddd; padding: 8px 10px; text-align: left; font-size: 13px; }
    th { background: #f4f4f4; }
    .tag { padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }
    .tag.pass { background: #d1fae5; color: #065f46; }
    .tag.warn { background: #fef3c7; color: #92400e; }
    .tag.fail { background: #fee2e2; color: #991b1b; }
  `],
})
export class QualityComponent implements OnInit {
  checks = signal<DQCheck[]>([]);

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.listDqChecks().subscribe((c) => this.checks.set(c));
  }

  countByResult(result: string): number {
    return this.checks().filter((c) => c.check_result === result).length;
  }
}
