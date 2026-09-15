import React from 'react';

interface StatCardProps {
  title: string;
  value: React.ReactNode;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: {
    text: string;
    type: 'positive' | 'neutral' | 'attention';
  };
  children?: React.ReactNode;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  children,
}) => {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">{title}</span>
        {icon && <div className="rounded-lg bg-slate-100 p-2 text-slate-600">{icon}</div>}
      </div>

      <div className="mt-3">
        <div className="text-2xl font-bold tracking-tight text-slate-900">{value}</div>
        {subtitle && <p className="mt-1 text-xs text-slate-500">{subtitle}</p>}
      </div>

      {trend && (
        <div className="mt-3 flex items-center gap-1 text-xs">
          <span
            className={`font-medium ${
              trend.type === 'positive'
                ? 'text-emerald-600'
                : trend.type === 'attention'
                ? 'text-rose-600'
                : 'text-slate-600'
            }`}
          >
            {trend.text}
          </span>
        </div>
      )}

      {children && <div className="mt-4 border-t border-slate-100 pt-3">{children}</div>}
    </div>
  );
};
