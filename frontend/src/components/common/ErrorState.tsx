import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  message = 'Unable to load your latest health insights. Please try again.',
  onRetry,
}) => {
  return (
    <div className="rounded-xl border border-rose-200 bg-rose-50/50 p-6 text-slate-800">
      <div className="flex items-start gap-3">
        <AlertTriangle className="h-5 w-5 shrink-0 text-rose-600" />
        <div className="flex-1">
          <h4 className="text-sm font-semibold text-rose-900">Service Communication Notice</h4>
          <p className="mt-1 text-xs text-rose-700">{message}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-rose-300 bg-white px-3 py-1 text-xs font-semibold text-rose-800 shadow-sm hover:bg-rose-50"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Retry Connection
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
