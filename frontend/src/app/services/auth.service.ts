import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../environments/environment';
import { CurrentUser } from '../models/api.models';

const TOKEN_KEY = 'access_token';

@Injectable({ providedIn: 'root' })
export class AuthService {
  // Signal réactif : les composants qui le lisent se mettent à jour automatiquement
  currentUser = signal<CurrentUser | null>(null);

  constructor(private http: HttpClient) {}

  login(username: string, password: string): Observable<{ access_token: string; token_type: string }> {
    const body = new URLSearchParams();
    body.set('username', username);
    body.set('password', password);

    return this.http
      .post<{ access_token: string; token_type: string }>(`${environment.apiUrl}/auth/login`, body.toString(), {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      .pipe(
        tap((res) => {
          localStorage.setItem(TOKEN_KEY, res.access_token);
          this.fetchCurrentUser().subscribe();
        })
      );
  }

  fetchCurrentUser(): Observable<CurrentUser> {
    return this.http.get<CurrentUser>(`${environment.apiUrl}/auth/me`).pipe(
      tap((user) => this.currentUser.set(user))
    );
  }

  logout(): void {
    localStorage.removeItem(TOKEN_KEY);
    this.currentUser.set(null);
  }

  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  isLoggedIn(): boolean {
    return !!this.getToken();
  }
}
