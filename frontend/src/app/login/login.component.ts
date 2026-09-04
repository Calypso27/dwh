import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="login-box">
      <h2>Connexion</h2>
      <p class="hint">
        Comptes de démo : <code>admin_global / admin123</code> (voit tout) ou
        <code>admin_sji / sji123</code> (voit seulement sa source)
      </p>

      <input [(ngModel)]="username" placeholder="Nom d'utilisateur" />
      <input [(ngModel)]="password" type="password" placeholder="Mot de passe" />
      <button (click)="onLogin()">Se connecter</button>

      @if (error()) {
        <p class="error">{{ error() }}</p>
      }
    </div>
  `,
  styles: [`
    .login-box { max-width: 320px; margin: 60px auto; display: flex; flex-direction: column; gap: 10px; font-family: sans-serif; }
    input, button { padding: 8px; font-size: 14px; }
    button { cursor: pointer; background: #1a1a2e; color: white; border: none; border-radius: 4px; }
    .error { color: #c0392b; }
    .hint { font-size: 12px; color: #666; }
  `],
})
export class LoginComponent {
  username = '';
  password = '';
  error = signal<string | null>(null);

  constructor(private auth: AuthService, private router: Router) {}

  onLogin(): void {
    this.error.set(null);
    this.auth.login(this.username, this.password).subscribe({
      next: () => this.router.navigate(['/dashboard']),
      error: (err) => this.error.set(err.status === 401 ? 'Identifiants incorrects' : 'Erreur de connexion à l\'API'),
    });
  }
}
