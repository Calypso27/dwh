import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { NavComponent } from '../shared/nav.component';
import { ApiService } from '../services/api.service';
import { SocialPost, SourceDataset, Platform, SentimentPrediction } from '../models/api.models';

@Component({
  selector: 'app-posts',
  standalone: true,
  imports: [CommonModule, FormsModule, NavComponent],
  template: `
    <app-nav />
    <div class="page">
      <h2>Publications</h2>
      <p class="hint">
        Teste <code>GET /posts</code> avec filtres, <code>GET /sources</code>,
        <code>GET /platforms</code> et <code>GET /posts/{{ '{id}' }}/sentiment</code>.
      </p>

      <div class="filters">
        <select [(ngModel)]="sourceId" (change)="reload()">
          <option [ngValue]="undefined">Toutes les sources</option>
          @for (s of sources(); track s.source_id) {
            <option [ngValue]="s.source_id">{{ s.source_name }}</option>
          }
        </select>

        <select [(ngModel)]="platformId" (change)="reload()">
          <option [ngValue]="undefined">Toutes les plateformes</option>
          @for (p of platforms(); track p.platform_id) {
            <option [ngValue]="p.platform_id">{{ p.platform_name }}</option>
          }
        </select>

        <span class="count">{{ posts().length }} résultat(s)</span>
      </div>

      <table>
        <thead>
          <tr><th>ID</th><th>Source</th><th>Plateforme</th><th>Texte</th><th>Publié le</th><th>Sentiment</th></tr>
        </thead>
        <tbody>
          @for (post of posts(); track post.post_id) {
            <tr (click)="showSentiment(post.post_id)" class="clickable">
              <td>{{ post.post_id }}</td>
              <td>{{ sourceName(post.source_id) }}</td>
              <td>{{ platformName(post.platform_id) }}</td>
              <td class="text">{{ post.text_content }}</td>
              <td>{{ post.published_at | date: 'short' }}</td>
              <td>
                @if (sentimentByPost()[post.post_id]; as s) {
                  <span class="tag" [class]="s.sentiment_label">{{ s.sentiment_label }}</span>
                } @else {
                  <span class="tag muted">clic pour voir</span>
                }
              </td>
            </tr>
          }
        </tbody>
      </table>
    </div>
  `,
  styles: [`
    .page { max-width: 1000px; margin: 20px auto; font-family: sans-serif; padding: 0 16px; }
    .hint { font-size: 12px; color: #666; }
    .filters { display: flex; gap: 12px; align-items: center; margin: 16px 0; }
    select { padding: 6px; }
    .count { font-size: 13px; color: #666; margin-left: auto; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border: 1px solid #ddd; padding: 8px 10px; text-align: left; font-size: 13px; }
    th { background: #f4f4f4; }
    .text { max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .clickable { cursor: pointer; }
    .clickable:hover { background: #fafafa; }
    .tag { padding: 2px 8px; border-radius: 10px; font-size: 11px; }
    .tag.positive { background: #d1fae5; color: #065f46; }
    .tag.negative { background: #fee2e2; color: #991b1b; }
    .tag.neutral { background: #e5e7eb; color: #374151; }
    .tag.muted { background: #f3f4f6; color: #9ca3af; }
  `],
})
export class PostsComponent implements OnInit {
  posts = signal<SocialPost[]>([]);
  sources = signal<SourceDataset[]>([]);
  platforms = signal<Platform[]>([]);
  sentimentByPost = signal<Record<number, SentimentPrediction>>({});

  sourceId?: number;
  platformId?: number;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.listSources().subscribe((s) => this.sources.set(s));
    this.api.listPlatforms().subscribe((p) => this.platforms.set(p));
    this.reload();
  }

  reload(): void {
    this.api.listPosts(this.sourceId, this.platformId).subscribe((p) => this.posts.set(p));
  }

  sourceName(id: number): string {
    return this.sources().find((s) => s.source_id === id)?.source_name ?? `#${id}`;
  }

  platformName(id: number): string {
    return this.platforms().find((p) => p.platform_id === id)?.platform_name ?? `#${id}`;
  }

  showSentiment(postId: number): void {
    this.api.getPostSentiment(postId).subscribe((preds) => {
      if (preds.length > 0) {
        this.sentimentByPost.update((map) => ({ ...map, [postId]: preds[0] }));
      }
    });
  }
}
