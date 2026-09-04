import { Routes } from '@angular/router';
import { LoginComponent } from './login/login.component';
import { DashboardComponent } from './dashboard/dashboard.component';
import { PostsComponent } from './posts/posts.component';
import { ModelsPageComponent } from './models-page/models-page.component';
import { QualityComponent } from './quality/quality.component';

export const routes: Routes = [
  { path: '', redirectTo: 'login', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },
  { path: 'dashboard', component: DashboardComponent },
  { path: 'posts', component: PostsComponent },
  { path: 'models', component: ModelsPageComponent },
  { path: 'quality', component: QualityComponent },
];
