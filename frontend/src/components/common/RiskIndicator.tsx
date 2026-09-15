import React from 'react';

interface RiskIndicatorProps {
  score: number; // 0.0 to 1.0 or 0 to 100
  showScale?: boolean;
}

export const RiskIndicator: React.FC<RiskIndicatorProps> = ({ score, showScale = true }) => {
  // Normalize score to percentage 0..100
  const scorePct = score <= 1.0 ? score * 100 : score;
  const clampedPct = Math.min(Math.max(scorePct, 0), 100);

  // Band calculation
  let bandLabel = 'Low';
  let barColor = 'bg-emerald-600';
  let textColor = 'text-emerald-700';

  if (clampedPct >= 65) {
    bandLabel = 'High';
    barColor = 'bg-rose-600';
    textColor = 'text-rose-700';
  } else if (clampedPct >= 35) {
    bandLabel = 'Medium';
    barColor = 'bg-amber-600';
    textColor = 'text-amber-700';
  }

  return (
    <div className="w-full space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-slate-700">Model-Estimated Risk Score</span>
        <div className="flex items-baseline gap-1.5">
          <span className={`text-lg font-bold ${textColor}`}>{clampedPct.toFixed(2)}%</span>
          <span className="text-xs font-semibold text-slate-500">({bandLabel})</span>
        </div>
      </div>

      {/* Progress Bar Container */}
      <div className="relative h-3 w-full overflow-hidden rounded-full bg-slate-200">
        <div
          className={`h-full transition-all duration-500 ease-out ${barColor}`}
          style={{ width: `${clampedPct}%` }}
        />
      </div>

      {showScale && (
        <div className="grid grid-cols-3 gap-1 pt-1 text-center text-xs font-medium text-slate-500">
          <div className="border-r border-slate-200 pr-1 text-left">
            <span className="block font-semibold text-emerald-700">Low</span>
            <span>0% – 35%</span>
          </div>
          <div className="border-r border-slate-200 px-1 text-center">
            <span className="block font-semibold text-amber-700">Medium</span>
            <span>35% – 65%</span>
          </div>
          <div className="pl-1 text-right">
            <span className="block font-semibold text-rose-700">High</span>
            <span>65% – 100%</span>
          </div>
        </div>
      )}
    </div>
  );
};
