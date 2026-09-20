import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../services/api.service';
import { NavComponent } from '../shared/nav.component';
import {
  BehaviorOverview, AuthorSegment, ThemeReaction, PageComparison, HourlyActivity,
} from '../models/api.models';

/** Libellés lisibles : les tables stockent des identifiants sans accent. */
const SEGMENT_LABELS: Record<string, string> = {
  ponctuel: 'Ponctuel', occasionnel: 'Occasionnel', regulier: 'Régulier',
  engage: 'Engagé', hyperactif: 'Hyperactif',
};

const SEGMENT_HINTS: Record<string, string> = {
  ponctuel: '1 commentaire', occasionnel: '2 commentaires', regulier: '3 à 4',
  engage: '5 à 9', hyperactif: '10 et plus',
};

interface HourPoint { hour: number; count: number; x: number; y: number; }

@Component({
  selector: 'app-behavior',
  standalone: true,
  imports: [CommonModule, NavComponent],
  template: `
    <app-nav />
    <div class="page">

      <header class="head">
        <div>
          <span class="eyebrow">Axe 1 — Comportement des utilisateurs</span>
          <h1>Comment le public réagit aux publications</h1>
        </div>
        @if (overview(); as o) {
          <div class="period">
            <span class="eyebrow">Période observée</span>
            <strong>{{ o.period_start | date: 'd MMM yyyy' }} — {{ o.period_end | date: 'd MMM yyyy' }}</strong>
          </div>
        }
      </header>

      <!-- Un tableau de bord donne aux chiffres une autorité qu'un rapport
           nuance mieux : l'avertissement de portée est donc placé AVANT toute
           donnée, pas en note de bas de page. -->
      <div class="scope" role="note">
        <span class="scope-icon" aria-hidden="true">!</span>
        <p>
          <strong>Corpus de substitution.</strong> Ces données proviennent des pages
          Facebook <strong>BBC</strong> et <strong>CNN</strong> (juillet 2017, 99,3 % anglophone).
          Elles ne décrivent <strong>pas</strong> l'audience de l'Institut Saint-Jean : elles
          servent à valider la chaîne d'analyse, dont la structure est identique.
        </p>
      </div>

      @if (error()) {
        <div class="card empty">
          <h2>Aucune donnée comportementale</h2>
          <p class="card-note">{{ error() }}</p>
          <code>python manage.py build-behavior</code>
        </div>
      } @else if (!overview()) {
        <div class="card empty"><p class="card-note">Chargement…</p></div>
      } @else {

        <!-- ---------- Chiffres d'en-tête ---------- -->
        @if (overview(); as o) {
          <section class="tiles">
            <div class="tile">
              <span class="eyebrow">Délai médian de réaction</span>
              <span class="figure">{{ o.median_delay_hours | number: '1.2-2' }}<span class="unit">h</span></span>
              <span class="sub">entre la publication et le commentaire</span>
            </div>
            <div class="tile">
              <span class="eyebrow">Réactions dans l'heure</span>
              <span class="figure">{{ o.pct_within_1h | number: '1.1-1' }}<span class="unit">%</span></span>
              <span class="sub">{{ o.pct_within_6h | number: '1.0-0' }} % dans les six heures</span>
            </div>
            <div class="tile">
              <span class="eyebrow">Commentaires analysés</span>
              <span class="figure">{{ o.comment_count | number }}</span>
              <span class="sub">tous rattachés à leur publication</span>
            </div>
            <div class="tile">
              <span class="eyebrow">Auteurs distincts</span>
              <span class="figure">{{ o.author_count | number }}</span>
              <span class="sub">sur {{ o.post_count | number }} publications</span>
            </div>
          </section>
        }

        <!-- ---------- Segments d'auteurs ---------- -->
        <section class="card">
          <div class="card-title">
            <h2>Qui produit les commentaires</h2>
          </div>
          <p class="card-note">
            Part des auteurs comparée à leur part du volume. Les deux mesures sont
            des pourcentages du même total, donc lisibles sur une échelle unique.
          </p>

          <div class="legend">
            <span class="key"><i class="swatch s1"></i>Part des auteurs</span>
            <span class="key"><i class="swatch s2"></i>Part des commentaires</span>
          </div>

          <div class="bars">
            @for (s of segments(); track s.segment) {
              <div class="bar-group">
                <div class="bar-head">
                  <span class="bar-name">{{ label(s.segment) }}</span>
                  <span class="bar-hint">{{ hint(s.segment) }}</span>
                </div>
                <div class="bar-rows">
                  <div class="bar-row" [title]="s.author_count + ' auteurs'">
                    <div class="track">
                      <div class="fill s1" [style.width.%]="scale(s.author_share)"></div>
                    </div>
                    <span class="bar-value">{{ s.author_share | number: '1.1-1' }} %</span>
                  </div>
                  <div class="bar-row" [title]="s.comment_count + ' commentaires'">
                    <div class="track">
                      <div class="fill s2" [style.width.%]="scale(s.comment_share)"></div>
                    </div>
                    <span class="bar-value">{{ s.comment_share | number: '1.1-1' }} %</span>
                  </div>
                </div>
              </div>
            }
          </div>

          @if (concentration(); as c) {
            <p class="insight">
              <strong>{{ c.authors | number: '1.1-1' }} %</strong> des auteurs — les segments
              engagé et hyperactif — produisent <strong>{{ c.comments | number: '1.1-1' }} %</strong>
              des commentaires. Confondre leur voix avec celle du public fausserait toute
              lecture de la tonalité.
            </p>
          }

          <div class="scroll-x detail">
            <table class="data">
              <thead>
                <tr>
                  <th>Segment</th>
                  <th class="num">Auteurs</th>
                  <th class="num">Commentaires</th>
                  <th class="num">Délai médian</th>
                  <th class="num">Longueur moy.</th>
                  <th class="num">Thèmes / auteur</th>
                </tr>
              </thead>
              <tbody>
                @for (s of segments(); track s.segment) {
                  <tr>
                    <td class="key">{{ label(s.segment) }}</td>
                    <td class="num">{{ s.author_count | number }}</td>
                    <td class="num">{{ s.comment_count | number }}</td>
                    <td class="num">{{ s.median_delay_hours | number: '1.2-2' }} h</td>
                    <td class="num">{{ s.avg_comment_length | number: '1.0-0' }}</td>
                    <td class="num">{{ s.avg_distinct_themes | number: '1.2-2' }}</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
          <p class="insight subtle">
            Les quatre colonnes de droite progressent ensemble du segment ponctuel au
            segment hyperactif : plus un auteur commente, plus il réagit vite, écrit
            long, et couvre de sujets.
          </p>
        </section>

        <!-- ---------- Réaction par thème ---------- -->
        <section class="card">
          <div class="card-title">
            <h2>Le sujet du post change la réaction</h2>
          </div>
          <p class="card-note">
            Délai médian de réaction par thème — c'est la lecture du commentaire
            <em>à travers</em> la publication qui l'a provoqué. Barre courte = réaction rapide.
          </p>

          <div class="bars themes">
            @for (t of themes(); track t.theme) {
              <div class="theme-row" [title]="t.comment_count + ' commentaires sur ' + t.post_count + ' publications'">
                <span class="theme-name" [class.unclassified]="t.theme === 'non_classe'">
                  {{ prettyTheme(t.theme) }}
                </span>
                <div class="track">
                  <div class="fill s3" [style.width.%]="scaleDelay(t.median_delay_hours)"></div>
                </div>
                <span class="bar-value">{{ t.median_delay_hours | number: '1.2-2' }} h</span>
              </div>
            }
          </div>

          <p class="insight subtle">
            La colonne « commentaires par publication » n'apparaît pas ici : la source
            plafonne à 100 commentaires par post, ce qui tasse tous les thèmes entre 87
            et 100 et rend l'indicateur inutilisable pour comparer l'intérêt suscité.
          </p>
        </section>

        <!-- ---------- Rythme horaire ---------- -->
        <section class="card">
          <div class="card-title">
            <h2>Rythme d'usage sur la journée</h2>
          </div>
          <p class="card-note">
            Volume de commentaires par heure, toutes publications confondues.
          </p>

          @if (hourPoints().length > 0) {
            <div class="chart-wrap"
                 (mousemove)="trackHover($event)"
                 (mouseleave)="hovered.set(null)">
              <svg viewBox="0 0 720 230" preserveAspectRatio="none" class="line-chart" role="img"
                   [attr.aria-label]="'Activité horaire, pic à ' + peak()?.hour + ' heures'">
                <!-- grille horizontale, volontairement discrète -->
                @for (g of gridLines(); track g.y) {
                  <line [attr.x1]="40" [attr.x2]="710" [attr.y1]="g.y" [attr.y2]="g.y"
                        class="grid" />
                  <text [attr.x]="34" [attr.y]="g.y + 4" class="axis-label end">{{ g.label }}</text>
                }
                <path [attr.d]="areaPath()" class="area" />
                <path [attr.d]="linePath()" class="line" />
                @if (hovered(); as h) {
                  <line [attr.x1]="h.x" [attr.x2]="h.x" [attr.y1]="10" [attr.y2]="190" class="crosshair" />
                  <circle [attr.cx]="h.x" [attr.cy]="h.y" r="5" class="marker" />
                }
                @for (t of hourTicks(); track t.hour) {
                  <text [attr.x]="t.x" [attr.y]="212" class="axis-label mid">{{ t.hour }} h</text>
                }
              </svg>
              @if (hovered(); as h) {
                <div class="tooltip" [style.left.%]="tooltipLeft(h)">
                  <strong>{{ h.hour }} h</strong>
                  <span>{{ h.count | number }} commentaires</span>
                </div>
              }
            </div>

            <div class="peaks">
              <span><i class="dot up"></i>Pic à <strong>{{ peak()?.hour }} h</strong> ({{ peak()?.count | number }})</span>
              <span><i class="dot down"></i>Creux à <strong>{{ trough()?.hour }} h</strong> ({{ trough()?.count | number }})</span>
              <span>Amplitude <strong>×{{ amplitude() | number: '1.1-1' }}</strong></span>
            </div>
          }
        </section>

        <!-- ---------- Comparaison des pages ---------- -->
        <section class="card">
          <div class="card-title">
            <h2>Comparaison des deux pages</h2>
          </div>
          <p class="card-note">
            Même nombre de publications de part et d'autre : c'est le schéma qui servira
            à comparer l'Institut à un établissement concurrent.
          </p>
          <div class="pages">
            @for (p of pages(); track p.page_name; let i = $index) {
              <div class="page-card" [class.alt]="i === 1">
                <div class="page-head">
                  <i class="swatch" [class.s1]="i === 0" [class.s2]="i === 1"></i>
                  <strong>{{ p.page_name }}</strong>
                </div>
                <dl>
                  <div><dt>Délai médian</dt><dd>{{ p.median_delay_hours | number: '1.2-2' }} h</dd></div>
                  <div><dt>Commentaires</dt><dd>{{ p.comment_count | number }}</dd></div>
                  <div><dt>Auteurs</dt><dd>{{ p.author_count | number }}</dd></div>
                  <div><dt>Longueur moy.</dt><dd>{{ p.avg_comment_length | number: '1.0-0' }} car.</dd></div>
                </dl>
              </div>
            }
          </div>
        </section>
      }
    </div>
  `,
  styles: [`
    .head {
      display: flex; align-items: flex-end; justify-content: space-between;
      gap: var(--space-4); flex-wrap: wrap; margin-bottom: var(--space-4);
    }
    .head h1 { margin-top: var(--space-1); }
    .period { text-align: right; display: flex; flex-direction: column; }
    .period strong { font-size: 14px; font-variant-numeric: tabular-nums; }


    .empty { text-align: center; }
    .empty code {
      display: inline-block; margin-top: var(--space-3);
      background: var(--surface-sunken); border: 1px solid var(--border);
      padding: var(--space-2) var(--space-3); border-radius: var(--radius-sm);
      font-size: 13px; color: var(--ink-primary);
    }


    section.card { margin-bottom: var(--space-4); }


    /* ----- Barres ----- */
    .bars { display: flex; flex-direction: column; gap: var(--space-4); }
    .bar-group { display: grid; grid-template-columns: 150px 1fr; gap: var(--space-4); align-items: center; }
    .bar-head { display: flex; flex-direction: column; }
    .bar-name { font-size: 13px; font-weight: 600; }
    .bar-hint { font-size: 11px; color: var(--ink-muted); }
    .bar-rows { display: flex; flex-direction: column; gap: 3px; }
    .bar-row { display: grid; grid-template-columns: 1fr 56px; gap: var(--space-3); align-items: center; }


    .themes { gap: var(--space-2); }
    .theme-row { display: grid; grid-template-columns: 178px 1fr 56px; gap: var(--space-3); align-items: center; }
    .theme-name { font-size: 12.5px; text-align: right; color: var(--ink-primary); }
    .theme-name.unclassified { color: var(--ink-muted); font-style: italic; }

    .detail { margin-top: var(--space-5); }

    /* ----- Courbe horaire ----- */
    .chart-wrap { position: relative; margin-top: var(--space-2); }
    .line-chart { width: 100%; height: 230px; display: block; overflow: visible; }
    .grid { stroke: var(--gridline); stroke-width: 1; }
    .area { fill: var(--series-1-soft); opacity: .55; }
    .line { fill: none; stroke: var(--series-1); stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
    .crosshair { stroke: var(--baseline); stroke-width: 1; stroke-dasharray: 3 3; }
    .marker { fill: var(--series-1); stroke: var(--surface); stroke-width: 2; }
    .axis-label { fill: var(--ink-muted); font-size: 10px; font-family: var(--font-sans); }
    .axis-label.end { text-anchor: end; }
    .axis-label.mid { text-anchor: middle; }

    .tooltip {
      position: absolute; top: 0; transform: translateX(-50%);
      background: var(--surface-inverse); color: var(--ink-on-inverse);
      border-radius: var(--radius-sm); padding: 6px 10px; font-size: 12px;
      display: flex; flex-direction: column; pointer-events: none; white-space: nowrap;
      box-shadow: 0 4px 12px rgba(0,0,0,.18);
    }

    .peaks { display: flex; gap: var(--space-5); flex-wrap: wrap; margin-top: var(--space-3); font-size: 12.5px; color: var(--ink-secondary); }
    .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 6px; }
    .dot.up { background: var(--series-1); }
    .dot.down { background: var(--baseline); }

    /* ----- Pages ----- */
    .pages { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: var(--space-3); }
    .page-card { border: 1px solid var(--border); border-radius: var(--radius); padding: var(--space-4); background: var(--surface-sunken); }
    .page-head { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-3); font-size: 15px; }
    .page-card dl { margin: 0; display: flex; flex-direction: column; gap: var(--space-2); }
    .page-card dl > div { display: flex; justify-content: space-between; gap: var(--space-3); }
    .page-card dt { color: var(--ink-muted); font-size: 12px; }
    .page-card dd { margin: 0; font-variant-numeric: tabular-nums; font-weight: 500; font-size: 13px; }

    @media (max-width: 640px) {
      .bar-group { grid-template-columns: 1fr; gap: var(--space-2); }
      .theme-row { grid-template-columns: 120px 1fr 52px; }
      .theme-name { font-size: 11.5px; }
      .head { flex-direction: column; align-items: flex-start; }
      .period { text-align: left; }
    }
  `],
})
export class BehaviorComponent implements OnInit {
  overview = signal<BehaviorOverview | null>(null);
  segments = signal<AuthorSegment[]>([]);
  themes = signal<ThemeReaction[]>([]);
  pages = signal<PageComparison[]>([]);
  hourly = signal<HourlyActivity[]>([]);
  hovered = signal<HourPoint | null>(null);
  error = signal<string | null>(null);

  // Géométrie de la courbe, en unités du viewBox.
  private readonly X0 = 40;
  private readonly X1 = 710;
  private readonly Y0 = 20;
  private readonly Y1 = 190;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.behaviorOverview().subscribe({
      next: (o) => this.overview.set(o),
      error: () => this.error.set(
        "La couche comportementale n'a pas encore été construite dans l'entrepôt."
      ),
    });
    this.api.behaviorSegments().subscribe((s) => this.segments.set(s));
    this.api.behaviorThemes().subscribe((t) => this.themes.set(t));
    this.api.behaviorPages().subscribe((p) => this.pages.set(p));
    this.api.behaviorHourly().subscribe((h) => this.hourly.set(h));
  }

  label = (key: string) => SEGMENT_LABELS[key] ?? key;
  hint = (key: string) => SEGMENT_HINTS[key] ?? '';

  /** « politique_gouvernement » -> « Politique gouvernement ». */
  prettyTheme(theme: string): string {
    if (theme === 'non_classe') return 'Non classé';
    const words = theme.replace(/_/g, ' ');
    return words.charAt(0).toUpperCase() + words.slice(1);
  }

  /** Les parts sont des pourcentages : on cadre sur le maximum observé pour
      que les petits segments restent visibles, sans jamais dépasser 100. */
  scale(share: number): number {
    const max = Math.max(
      ...this.segments().flatMap((s) => [s.author_share, s.comment_share]), 1);
    return (share / max) * 100;
  }

  scaleDelay(delay: number | null): number {
    const max = Math.max(...this.themes().map((t) => t.median_delay_hours ?? 0), 0.1);
    return ((delay ?? 0) / max) * 100;
  }

  concentration = computed(() => {
    const actifs = this.segments().filter((s) => s.segment === 'engage' || s.segment === 'hyperactif');
    if (!actifs.length) return null;
    return {
      authors: actifs.reduce((sum, s) => sum + s.author_share, 0),
      comments: actifs.reduce((sum, s) => sum + s.comment_share, 0),
    };
  });

  private maxCount = computed(() => Math.max(...this.hourly().map((h) => h.comment_count), 1));

  hourPoints = computed<HourPoint[]>(() => {
    const data = this.hourly();
    if (!data.length) return [];
    const max = this.maxCount();
    const step = (this.X1 - this.X0) / Math.max(data.length - 1, 1);
    return data.map((h, i) => ({
      hour: h.hour,
      count: h.comment_count,
      x: this.X0 + i * step,
      y: this.Y1 - (h.comment_count / max) * (this.Y1 - this.Y0),
    }));
  });

  linePath = computed(() =>
    this.hourPoints().map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' '));

  areaPath = computed(() => {
    const pts = this.hourPoints();
    if (!pts.length) return '';
    return `${this.linePath()} L${pts[pts.length - 1].x.toFixed(1)},${this.Y1} L${pts[0].x.toFixed(1)},${this.Y1} Z`;
  });

  /** Quatre repères suffisent : une grille dense concurrence les données. */
  gridLines = computed(() => {
    const max = this.maxCount();
    return [0, 0.5, 1].map((ratio) => ({
      y: this.Y1 - ratio * (this.Y1 - this.Y0),
      label: Math.round(max * ratio / 100) * 100,
    }));
  });

  /** Une graduation sur quatre : au-delà, les libellés se chevauchent. */
  hourTicks = computed(() => this.hourPoints().filter((p) => p.hour % 4 === 0));

  peak = computed(() =>
    this.hourPoints().reduce((best, p) => (!best || p.count > best.count ? p : best), null as HourPoint | null));

  trough = computed(() =>
    this.hourPoints().reduce((worst, p) => (!worst || p.count < worst.count ? p : worst), null as HourPoint | null));

  amplitude = computed(() => {
    const hi = this.peak()?.count ?? 0;
    const lo = this.trough()?.count ?? 0;
    return lo ? hi / lo : 0;
  });

  /** La cible de survol est l'ensemble du graphique, pas chaque point : on
      cherche le point le plus proche horizontalement du curseur. */
  trackHover(event: MouseEvent): void {
    const pts = this.hourPoints();
    if (!pts.length) return;
    const box = (event.currentTarget as HTMLElement).getBoundingClientRect();
    const ratio = (event.clientX - box.left) / box.width;
    const viewX = ratio * 720;
    const nearest = pts.reduce((best, p) =>
      Math.abs(p.x - viewX) < Math.abs(best.x - viewX) ? p : best, pts[0]);
    this.hovered.set(nearest);
  }

  tooltipLeft = (point: HourPoint) => (point.x / 720) * 100;
}
