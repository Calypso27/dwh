import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { ApiService } from '../services/api.service';
import { NavComponent } from '../shared/nav.component';
import { BarChartComponent, BarDatum } from '../shared/bar-chart.component';
import { SocialPost, ModelRun } from '../models/api.models';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, NavComponent, BarChartComponent],
  template: `
    <app-nav />
    <div class="dashboard">
      <header>
        <h2>Tableau de bord</h2>
        @if (auth.currentUser(); as user) {
          <p>
            Connecté en tant que <strong>{{ user.username }}</strong>
            — rôle : <span class="badge">{{ user.role }}</span>
            @if (user.scope_source_id) {
              <span class="badge">source #{{ user.scope_source_id }}</span>
            }
          </p>
        }
      </header>

      @if (sentimentData().length > 0) {
        <section>
          <h3>Répartition du sentiment (toutes sources visibles)</h3>
          <app-bar-chart [data]="sentimentData()" />
        </section>
      }

      <section>
        <h3>Publications visibles ({{ posts().length }})</h3>
        <p class="hint">
          <code>GET /posts/scoped/me</code> — cette liste change automatiquement selon le rôle du compte connecté.
        </p>
        <table>
          <thead>
            <tr><th>ID</th><th>Source</th><th>Plateforme</th><th>Texte</th></tr>
          </thead>
          <tbody>
            @for (post of posts(); track post.post_id) {
              <tr>
                <td>{{ post.post_id }}</td>
                <td>{{ post.source_id }}</td>
                <td>{{ post.platform_id }}</td>
                <td>{{ post.text_content }}</td>
              </tr>
            }
          </tbody>
        </table>
      </section>

      <section>
        <h3>Essais de modèles ML ({{ runs().length }})</h3>
        <table>
          <thead>
            <tr><th>Run</th><th>Modèle</th><th>Source</th><th>Tâche</th></tr>
          </thead>
          <tbody>
            @for (run of runs(); track run.run_id) {
              <tr>
                <td>{{ run.run_id }}</td>
                <td>{{ run.model_name }}</td>
                <td>{{ run.source_name }}</td>
                <td>{{ run.task_type }}</td>
              </tr>
            }
          </tbody>
        </table>
      </section>
    </div>
  `,
  styles: [`
    .dashboard { max-width: 900px; margin: 20px auto; font-family: sans-serif; padding: 0 16px; }
    .badge { background: #eee; padding: 2px 8px; border-radius: 10px; font-size: 12px; margin-left: 6px; }
    table { width: 100%; border-collapse: collapse; margin: 10px 0 30px; }
    th, td { border: 1px solid #ddd; padding: 6px 10px; text-align: left; font-size: 14px; }
    th { background: #f4f4f4; }
    .hint { font-size: 12px; color: #666; }
  `],
})
export class DashboardComponent implements OnInit {
  posts = signal<SocialPost[]>([]);
  runs = signal<ModelRun[]>([]);
  sentimentData = signal<BarDatum[]>([]);

  constructor(public auth: AuthService, private api: ApiService, private router: Router) {}

  ngOnInit(): void {
    if (!this.auth.isLoggedIn()) {
      this.router.navigate(['/login']);
      return;
    }
    this.auth.fetchCurrentUser().subscribe();
    this.api.listScopedPosts().subscribe((p) => this.posts.set(p));
    this.api.listModelRuns().subscribe((r) => this.runs.set(r));
    this.api.sentimentSummary().subscribe((summary) => {
      const colors: Record<string, string> = { positive: '#10b981', negative: '#ef4444', neutral: '#9ca3af' };
      this.sentimentData.set(
        summary.map((s) => ({ label: s.sentiment_label, value: s.count, color: colors[s.sentiment_label] }))
      );
    });
  }
}
