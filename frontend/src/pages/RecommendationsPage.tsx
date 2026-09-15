import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Header } from '../components/layout/Header';
import { RiskBadge } from '../components/common/RiskBadge';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { getRecommendations, RecommendationResponse } from '../services/api';
import {
  Lightbulb,
  Calendar,
  Activity,
  ShieldCheck,
  CheckCircle2,
  Info,
  AlertCircle,
  ArrowRight,
} from 'lucide-react';
import { Link } from 'react-router-dom';

export const RecommendationsPage: React.FC = () => {
  const { user } = useAuth();
  const [data, setData] = useState<RecommendationResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  // Frontend-only acknowledge state — no backend changes
  const [acknowledgedSet, setAcknowledgedSet] = useState<Set<number>>(new Set());

  const fetchRecommendations = async () => {
    const userId = user?.userSub;
    if (!userId) {
      setError('User session not found. Please sign in again.');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    setAcknowledgedSet(new Set());
    try {
      const result = await getRecommendations(userId);
      if (Array.isArray(result) && result.length > 0) {
        setData(result[0]);
      } else {
        setData(null);
      }
    } catch (err: any) {
      setError(err.message || 'Unable to load preventive recommendations.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecommendations();
  }, [user]);

  // ── Derived values ────────────────────────────────────────────────────
  const hasData = data !== null;
  const activityName = data?.activity ?? null;
  const riskBand = data?.risk_band ?? null;
  const riskScore = data?.risk_score != null ? Number(data.risk_score) : null;
  const timestamp = data?.timestamp
    ? new Date(data.timestamp).toLocaleString()
    : data?.created_at
    ? new Date(data.created_at).toLocaleString()
    : null;

  // Build recommendation list
  const recList: string[] = (() => {
    if (!hasData) return [];
    if (data?.recommendations && data.recommendations.length > 0) {
      return data.recommendations;
    }
    const single = data?.recommendation_text || data?.recommendation;
    if (single) return [single];
    return [];
  })();

  const toggleAcknowledge = (idx: number) => {
    setAcknowledgedSet((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const acknowledgedCount = acknowledgedSet.size;
  const allAcknowledged = recList.length > 0 && acknowledgedCount >= recList.length;

  return (
    <div className="space-y-6">
      <Header
        title="Preventive Healthcare Recommendations"
        description="Tailored behavioural interventions synthesised from activity stream and predictive risk profile."
        onRefresh={fetchRecommendations}
        isRefreshing={loading}
      />

      {loading && <LoadingState message="Loading preventive recommendations..." />}
      {!loading && error && <ErrorState message={error} onRetry={fetchRecommendations} />}

      {!loading && !error && (
        <div className="space-y-5">
          {/* Context Strip */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <Activity className="h-5 w-5 shrink-0 text-teal-600" />
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  Associated Activity
                </p>
                <p className="mt-0.5 text-sm font-bold text-slate-900">
                  {hasData && activityName ? activityName : 'No data'}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <ShieldCheck className="h-5 w-5 shrink-0 text-blue-600" />
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  Risk Assessment Band
                </p>
                <div className="mt-1">
                  {hasData && riskBand ? <RiskBadge level={riskBand} size="md" /> : <span className="text-xs font-semibold text-slate-400">No data</span>}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <Calendar className="h-5 w-5 shrink-0 text-slate-400" />
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  Generated
                </p>
                <p className="mt-0.5 text-xs font-semibold text-slate-700">
                  {hasData && timestamp ? timestamp : 'N/A'}
                </p>
              </div>
            </div>
          </div>

          {/* Recommendations Card */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-5 flex items-start justify-between border-b border-slate-100 pb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-amber-200 bg-amber-50">
                  <Lightbulb className="h-5 w-5 text-amber-600" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    Your Preventive Recommendations
                  </h3>
                  <p className="text-[11px] text-slate-500">
                    Behaviour-based preventive strategies — based on available profile and recent activity
                  </p>
                </div>
              </div>

              {hasData && recList.length > 0 && (
                <div className="text-right">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    Acknowledged
                  </span>
                  <p className="mt-0.5 text-sm font-bold text-slate-900">
                    {acknowledgedCount} / {recList.length}
                  </p>
                </div>
              )}
            </div>

            {hasData && recList.length > 0 ? (
              <>
                {/* All acknowledged banner */}
                {allAcknowledged && (
                  <div className="mb-4 flex items-center gap-2.5 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-700">
                    <CheckCircle2 className="h-5 w-5 shrink-0" />
                    All recommendations acknowledged. Continue applying these strategies to maintain your preventive health.
                  </div>
                )}

                {/* Recommendation list */}
                <div className="space-y-3">
                  {recList.map((rec, idx) => {
                    const isAck = acknowledgedSet.has(idx);
                    return (
                      <div
                        key={idx}
                        className={`group flex items-start justify-between gap-5 rounded-xl border px-5 py-4 transition-all ${
                          isAck
                            ? 'border-emerald-200 bg-emerald-50/40'
                            : 'border-slate-100 bg-slate-50/40 hover:border-slate-200 hover:bg-white'
                        }`}
                      >
                        <div className="flex min-w-0 items-start gap-3">
                          <div
                            className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full ${
                              isAck ? 'bg-emerald-100' : 'bg-amber-100'
                            }`}
                          >
                            {isAck ? (
                              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                            ) : (
                              <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                            )}
                          </div>
                          <p
                            className={`text-sm leading-relaxed ${
                              isAck
                                ? 'text-slate-400 line-through'
                                : 'font-medium text-slate-700'
                            }`}
                          >
                            {rec}
                          </p>
                        </div>

                        <button
                          onClick={() => toggleAcknowledge(idx)}
                          className={`shrink-0 rounded-lg border px-3 py-1.5 text-xs font-semibold transition-colors ${
                            isAck
                              ? 'border-emerald-200 bg-white text-emerald-700 hover:bg-emerald-50'
                              : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50'
                          }`}
                        >
                          {isAck ? (
                            <span className="flex items-center gap-1">
                              <CheckCircle2 className="h-3.5 w-3.5" />
                              Acknowledged
                            </span>
                          ) : (
                            'Mark as Acknowledged'
                          )}
                        </button>
                      </div>
                    );
                  })}
                </div>

                {/* Risk score context */}
                {riskScore != null && riskBand && (
                  <div className="mt-5 rounded-lg bg-slate-50 border border-slate-100 px-4 py-3 text-xs text-slate-600">
                    <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
                      <span>
                        Risk score:{' '}
                        <strong className="text-slate-900">
                          {(riskScore * 100).toFixed(2)}%
                        </strong>
                      </span>
                      <span>
                        Risk band: <RiskBadge level={riskBand} size="sm" />
                      </span>
                      <span>
                        Source: <strong className="text-slate-900">XGBoost (BRFSS 2015)</strong>
                      </span>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="flex flex-col items-center justify-center py-10 text-center">
                <AlertCircle className="h-10 w-10 text-slate-300 mb-3" />
                <p className="text-sm font-bold text-slate-700">No preventive recommendations yet</p>
                <p className="text-xs text-slate-400 max-w-md mt-1 mb-4">
                  Complete your health profile on the Profile page, stream smartwatch telemetry, and run the ML processing pipeline to generate personalized recommendations.
                </p>
                <Link
                  to="/profile"
                  className="flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-teal-700 transition-colors"
                >
                  <span>Go to Profile Page</span>
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </div>
            )}
          </div>

          {/* Medical Disclaimer */}
          <div className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
            <Info className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />
            <p className="text-[11px] leading-relaxed text-slate-500">
              <strong className="font-semibold text-slate-700">Medical Disclaimer:</strong>{' '}
              These recommendations are generated by a machine learning model trained on the BRFSS 2015
              dataset for academic demonstration purposes only. They represent behaviour-based preventive
              suggestions, not clinical diagnoses or prescriptions. Always consult a qualified healthcare
              professional before making any changes to your health management.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
