import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

export interface BarDatum {
  label: string;
  value: number;
  color?: string;
}

@Component({
  selector: 'app-bar-chart',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="chart">
      @for (d of data; track d.label) {
        <div class="row">
          <span class="label">{{ d.label }}</span>
          <div class="track">
            <div class="fill" [style.width.%]="pct(d.value)" [style.background]="d.color || defaultColor"></div>
          </div>
          <span class="value">{{ d.value | number: '1.2-3' }}</span>
        </div>
      }
    </div>
  `,
  styles: [`
    .chart { display: flex; flex-direction: column; gap: 8px; font-family: sans-serif; }
    .row { display: grid; grid-template-columns: 140px 1fr 60px; align-items: center; gap: 8px; }
    .label { font-size: 13px; color: #333; text-align: right; }
    .track { background: #eee; border-radius: 4px; height: 16px; overflow: hidden; }
    .fill { height: 100%; border-radius: 4px; transition: width 0.3s; }
    .value { font-size: 12px; color: #555; }
  `],
})
export class BarChartComponent {
  @Input() data: BarDatum[] = [];
  @Input() max?: number;
  defaultColor = '#14213d';

  pct(value: number): number {
    const maxVal = this.max ?? Math.max(...this.data.map((d) => d.value), 1);
    return maxVal ? (value / maxVal) * 100 : 0;
  }
}
