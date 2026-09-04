import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  SocialPost, ModelRun, ModelMetric, DQCheck,
  SentimentPrediction, SentimentSummary, SourceDataset, Platform,
} from '../models/api.models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  constructor(private http: HttpClient) {}

  listPosts(sourceId?: number, platformId?: number, limit = 50, offset = 0): Observable<SocialPost[]> {
    const params = new URLSearchParams();
    if (sourceId) params.set('source_id', String(sourceId));
    if (platformId) params.set('platform_id', String(platformId));
    params.set('limit', String(limit));
    params.set('offset', String(offset));
    return this.http.get<SocialPost[]>(`${environment.apiUrl}/posts?${params.toString()}`);
  }

  getPost(postId: number): Observable<SocialPost> {
    return this.http.get<SocialPost>(`${environment.apiUrl}/posts/${postId}`);
  }

  getPostSentiment(postId: number): Observable<SentimentPrediction[]> {
    return this.http.get<SentimentPrediction[]>(`${environment.apiUrl}/posts/${postId}/sentiment`);
  }

  listScopedPosts(): Observable<SocialPost[]> {
    return this.http.get<SocialPost[]>(`${environment.apiUrl}/posts/scoped/me`);
  }

  listModelRuns(): Observable<ModelRun[]> {
    return this.http.get<ModelRun[]>(`${environment.apiUrl}/model-runs`);
  }

  getRunMetrics(runId: number): Observable<ModelMetric[]> {
    return this.http.get<ModelMetric[]>(`${environment.apiUrl}/model-runs/${runId}/metrics`);
  }

  listDqChecks(): Observable<DQCheck[]> {
    return this.http.get<DQCheck[]>(`${environment.apiUrl}/dq-checks`);
  }

  sentimentSummary(): Observable<SentimentSummary[]> {
    return this.http.get<SentimentSummary[]>(`${environment.apiUrl}/sentiment-summary`);
  }

  listSources(): Observable<SourceDataset[]> {
    return this.http.get<SourceDataset[]>(`${environment.apiUrl}/sources`);
  }

  listPlatforms(): Observable<Platform[]> {
    return this.http.get<Platform[]>(`${environment.apiUrl}/platforms`);
  }
}
