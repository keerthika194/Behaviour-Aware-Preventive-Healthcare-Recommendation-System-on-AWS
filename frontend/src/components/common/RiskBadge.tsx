import React from 'react';

interface RiskBadgeProps {
  level?: 'Low' | 'Medium' | 'High' | string;
  size?: 'sm' | 'md' | 'lg';
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ level = 'Low', size = 'md' }) => {
  const normLevel = level ? level.toString().trim() : 'Low';
  const isLow = normLevel.toLowerCase().includes('low');
  const isMedium = normLevel.toLowerCase().includes('med');
  const isHigh = normLevel.toLowerCase().includes('high');

  let colorClasses = 'bg-slate-100 text-slate-700 border-slate-200';
  if (isLow) {
    colorClasses = 'bg-emerald-50 text-emerald-800 border-emerald-200';
  } else if (isMedium) {
    colorClasses = 'bg-amber-50 text-amber-800 border-amber-200';
  } else if (isHigh) {
    colorClasses = 'bg-rose-50 text-rose-800 border-rose-200';
  }

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs font-medium',
    md: 'px-2.5 py-1 text-xs font-semibold',
    lg: 'px-3.5 py-1.5 text-sm font-semibold',
  }[size];

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-md border ${colorClasses} ${sizeClasses}`}>
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          isLow ? 'bg-emerald-600' : isMedium ? 'bg-amber-600' : isHigh ? 'bg-rose-600' : 'bg-slate-400'
        }`}
      />
      {normLevel} Risk
    </span>
  );
};
