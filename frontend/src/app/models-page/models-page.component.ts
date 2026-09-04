import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NavComponent } from '../shared/nav.component';
import { BarChartComponent, BarDatum } from '../shared/bar-chart.component';
import { ApiService } from '../services/api.service';
import { ModelRun, ModelMetric } from '../models/api.models';

@Component({
  selector: 'app-models-page',
  standalone: true,
  imports: [CommonModule, NavComponent, BarChartComponent],
  template: `
    <app-nav />
    <div class="page">
      <h2>Comparaison des modèles ML</h2>
      <p class="hint">
        Teste <code>GET /model-runs</code> et <code>GET /model-runs/&#123;id&#125;/metrics</code>
        — comparatif réel obtenu sur la tâche de prédiction de viralité (dataset YouTube).
      </p>

      @if (f1Data().length > 0) {
        <h3>F1-score par modèle (classe "viral")</h3>
        <app-bar-chart [data]="f1Data()" [max]="1" />
      }

      <h3>Détail des essais</h3>
      <table>
        <thead>
          <tr><th>Run</th><th>Modèle</th><th>Source</th><th>Tâche</th><th>Lignes train / test</th><th>F1</th><th>PR-AUC</th><th>Recall</th></tr>
        </thead>
        <tbody>
          @for (run of runsWithMetrics(); track run.run_id) {
            <tr>
              <td>{{ run.run_id }}</td>
              <td>{{ run.model_name }}</td>
              <td>{{ run.source_name }}</td>
              <td>{{ run.task_type }}</td>
              <td>{{ run.train_rows | number }} / {{ run.test_rows | number }}</td>
              <td>{{ run.metrics['f1_score'] | number: '1.3-3' }}</td>
              <td>{{ run.metrics['pr_auc'] | number: '1.3-3' }}</td>
              <td>{{ run.metrics['recall'] | number: '1.3-3' }}</td>
            </tr>
          }
        </tbody>
      </table>
    </div>
  `,
  styles: [`
    .page { max-width: 1000px; margin: 20px auto; font-family: sans-serif; padding: 0 16px; }
    .hint { font-size: 12px; color: #666; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    th, td { border: 1px solid #ddd; padding: 8px 10px; text-align: left; font-size: 13px; }
    th { background: #f4f4f4; }
    h3 { margin-top: 28px; }
  `],
})
export class ModelsPageComponent implements OnInit {
  runs = signal<ModelRun[]>([]);
  metricsByRun = signal<Record<number, ModelMetric[]>>({});

  runsWithMetrics = computed(() =>
    this.runs().map((r) => {
      const metrics: Record<string, number> = {};
      for (const m of this.metricsByRun()[r.run_id] ?? []) {
        metrics[m.metric_name] = m.metric_value;
      }
      return { ...r, metrics };
    })
  );

  f1Data = computed<BarDatum[]>(() =>
    this.runsWithMetrics()
      .filter((r) => r.metrics['f1_score'] !== undefined)
      .map((r) => ({ label: r.model_name, value: r.metrics['f1_score'] }))
  );

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.listModelRuns().subscribe((runs) => {
      this.runs.set(runs);
      for (const run of runs) {
        this.api.getRunMetrics(run.run_id).subscribe((metrics) => {
          this.metricsByRun.update((map) => ({ ...map, [run.run_id]: metrics }));
        });
      }
    });
  }
}
