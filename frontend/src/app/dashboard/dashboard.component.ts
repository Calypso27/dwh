import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../services/api.service';
import { NavComponent } from '../shared/nav.component';
import { BarChartComponent, BarDatum } from '../shared/bar-chart.component';
import { SocialPost, ModelRun, PlatformKpi, Recommendation, Alert } from '../models/api.models';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, NavComponent, BarChartComponent],
  template: `
    <app-nav />
    <div class="dashboard">
      <header>
        <h2>Tableau de bord</h2>
      </header>

      @if (sentimentData().length > 0) {
        <section>
          <h3>Répartition du sentiment (toutes sources visibles)</h3>
          <app-bar-chart [data]="sentimentData()" />
        </section>
      }

      <section>
        <h3>Performance par plateforme</h3>
        @if (platformKpis().length === 0) {
          <p class="hint">Aucun KPI disponible. Chargez les données puis exécutez build-analytics.</p>
        } @else {
          <table>
            <thead><tr><th>Plateforme</th><th>Publications</th><th>Engagement moyen</th><th>Taux / 1k</th><th>Viralité</th></tr></thead>
            <tbody>
              @for (kpi of platformKpis(); track kpi.platform_name) {
                <tr><td>{{ kpi.platform_name }}</td><td>{{ kpi.post_count }}</td><td>{{ kpi.average_engagement | number:'1.0-2' }}</td><td>{{ kpi.average_engagement_rate | number:'1.0-2' }}</td><td>{{ kpi.viral_post_count }}</td></tr>
              }
            </tbody>
          </table>
        }
      </section>

      <section>
        <h3>Recommandations</h3>
        @for (recommendation of recommendations(); track recommendation.recommendation_id) {
          <p><strong>{{ recommendation.platform_name }}</strong> — {{ recommendation.recommendation_text }}</p>
        } @empty {
          <p class="hint">Aucune recommandation générée.</p>
        }
      </section>

      <section>
        <h3>Alertes</h3>
        @for (alert of alerts(); track alert.alert_id) {
          <p class="alert"><strong>{{ alert.severity }}</strong> — {{ alert.alert_text }}</p>
        } @empty {
          <p class="hint">Aucune alerte active.</p>
        }
      </section>

      <section>
        <h3>Publications visibles ({{ posts().length }})</h3>
        <p class="hint">
          <code>GET /posts</code> — les publications sont consultables directement depuis le tableau de bord.
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
  platformKpis = signal<PlatformKpi[]>([]);
  recommendations = signal<Recommendation[]>([]);
  alerts = signal<Alert[]>([]);

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.listPosts().subscribe((p) => this.posts.set(p));
    this.api.listModelRuns().subscribe((r) => this.runs.set(r));
    this.api.sentimentSummary().subscribe((summary) => {
      const colors: Record<string, string> = { positive: '#10b981', negative: '#ef4444', neutral: '#9ca3af' };
      this.sentimentData.set(
        summary.map((s) => ({ label: s.sentiment_label, value: s.count, color: colors[s.sentiment_label] }))
      );
    });
    this.api.platformKpis().subscribe((kpis) => this.platformKpis.set(kpis));
    this.api.listRecommendations().subscribe((items) => this.recommendations.set(items));
    this.api.listAlerts().subscribe((items) => this.alerts.set(items));
  }
}
