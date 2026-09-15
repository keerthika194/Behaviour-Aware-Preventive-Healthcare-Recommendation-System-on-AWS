import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { getRecommendations, RecommendationResponse } from '../services/api';
import { RiskIndicator } from '../components/common/RiskIndicator';
import { Header } from '../components/layout/Header';
import { RiskBadge } from '../components/common/RiskBadge';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import {
  Activity,
  ShieldAlert,
  Lightbulb,
  CheckCircle2,
  Radio,
  ArrowRight,
  Cpu,
  Wifi,
  BarChart3,
} from 'lucide-react';

export function DashboardPage() {
  const { user } = useAuth();
  const [recommendation, setRecommendation] = useState<RecommendationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  // Frontend-only acknowledge state — no backend changes needed
  const [acknowledgedSet, setAcknowledgedSet] = useState<Set<number>>(new Set());

  const loadRecommendations = async () => {
    // Use the authenticated Cognito sub — never fall back to a hardcoded demo ID
    const userId = user?.userSub;
    if (!userId) {
      setError('User session not found. Please sign in again.');
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setError('');
      const data = await getRecommendations(userId);
      if (Array.isArray(data) && data.length > 0) {
        setRecommendation(data[0]);
      } else {
        setRecommendation(null);
      }
    } catch (err: any) {
      console.warn('Dashboard recommendation error:', err.message);
      setError(err.message || 'Failed to fetch recommendations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecommendations();
  }, [user]);

  // ── Derived values from API response ──────────────────────────────────
  // hasData is true only when the API returned a real record for this user.
  // When false, we must NOT show the old demo patient's fake fallback values.
  const hasData = recommendation !== null;

  const activity = recommendation?.activity ?? null;
  const activityConfidence = recommendation?.activity_confidence != null
    ? Number(recommendation.activity_confidence)
    : null;
  const riskScore = recommendation?.risk_score != null
    ? Number(recommendation.risk_score)
    : null;
  const riskBand = recommendation?.risk_band ?? null;
  const riskScorePct = riskScore != null ? (riskScore * 100).toFixed(2) + '%' : null;
  const lastUpdate = recommendation?.timestamp
    ? new Date(recommendation.timestamp).toLocaleString()
    : recommendation?.created_at
    ? new Date(recommendation.created_at).toLocaleString()
    : new Date().toLocaleString();

  // Gather all recommendations as a list — prefer the array field, fall back to single text
  const recList: string[] = (() => {
    if (!hasData) return [];
    if (recommendation?.recommendations && recommendation.recommendations.length > 0) {
      return recommendation.recommendations;
    }
    const single =
      recommendation?.recommendation_text || recommendation?.recommendation;
    if (single) return [single];
    return [];
  })();

  const riskInterpretation: Record<string, string> = {
    Low: 'Your current profile and recent behaviour indicate a relatively low preventive risk.',
    Medium:
      'Your recent behaviour and health indicators suggest a moderate preventive risk. Increased activity and monitoring are advisable.',
    High:
      'Your profile and behaviour data indicate an elevated preventive risk. Lifestyle adjustments and consultation with a healthcare professional are recommended.',
  };
  const riskText = riskBand ? (riskInterpretation[riskBand] ?? '') : '';

  const toggleAcknowledge = (idx: number) => {
    setAcknowledgedSet((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const allAcknowledged = recList.length > 0 && acknowledgedSet.size >= recList.length;

  return (
    <div className="space-y-6">
      <Header
        title="Preventive Healthcare Dashboard"
        description="Behaviour-aware preventive health monitoring and personalised recommendations."
        onRefresh={loadRecommendations}
        isRefreshing={loading}
      />

      {/* ── Data Pipeline Status Strip ───────────────────────────────── */}
      <div className="rounded-xl border border-slate-200 bg-white px-5 py-3.5 shadow-sm">
        <div className="flex flex-wrap items-center gap-y-2">
          <span className="mr-3 text-[10px] font-bold uppercase tracking-widest text-slate-400">
            Data Pipeline
          </span>

          <div className="flex flex-wrap items-center gap-1">
            {/* Step 1 */}
            <div className="flex shrink-0 items-center gap-1.5 rounded-lg bg-slate-50 border border-slate-200 px-3 py-1.5">
              <Radio className="h-3.5 w-3.5 text-teal-600" />
              <span className="text-[11px] font-semibold text-slate-700">Smartwatch Simulator</span>
              <span className="ml-0.5 h-1.5 w-1.5 rounded-full bg-teal-500 animate-pulse" />
            </div>

            <ArrowRight className="h-3.5 w-3.5 shrink-0 text-slate-300" />

            {/* Step 2 */}
            <div className="flex shrink-0 items-center gap-1.5 rounded-lg bg-slate-50 border border-slate-200 px-3 py-1.5">
              <Wifi className="h-3.5 w-3.5 text-blue-600" />
              <span className="text-[11px] font-semibold text-slate-700">AWS IoT Core</span>
            </div>

            <ArrowRight className="h-3.5 w-3.5 shrink-0 text-slate-300" />

            {/* Step 3 */}
            <div className="flex shrink-0 items-center gap-1.5 rounded-lg bg-slate-50 border border-slate-200 px-3 py-1.5">
              <Cpu className="h-3.5 w-3.5 text-purple-600" />
              <span className="text-[11px] font-semibold text-slate-700">ML Pipeline</span>
              <span className="ml-1 rounded bg-purple-100 px-1 py-0.5 text-[9px] font-bold text-purple-700">
                XGBoost + RF
              </span>
            </div>

            <ArrowRight className="h-3.5 w-3.5 shrink-0 text-slate-300" />

            {/* Step 4 */}
            <div className="flex shrink-0 items-center gap-1.5 rounded-lg bg-slate-50 border border-slate-200 px-3 py-1.5">
              <BarChart3 className="h-3.5 w-3.5 text-amber-600" />
              <span className="text-[11px] font-semibold text-slate-700">Dashboard</span>
            </div>
          </div>

          <div className="ml-auto pl-4 text-[10px] text-slate-400 whitespace-nowrap">
            Last update: {lastUpdate}
          </div>
        </div>
      </div>

      {loading && <LoadingState message="Loading your latest health insights..." />}
      {!loading && error && <ErrorState message={error} onRetry={loadRecommendations} />}

      {!loading && (
        <>
          {/* ── Hero Cards Row ──────────────────────────────────────────── */}
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">

            {/* A. Today's Behaviour */}
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                  Today's Behaviour
                </span>
                <div className="rounded-lg border border-teal-200 bg-teal-50 p-2">
                  <Activity className="h-4 w-4 text-teal-600" />
                </div>
              </div>

              <div className="mt-4">
                {hasData ? (
                  <>
                    <div className="text-3xl font-bold tracking-tight text-slate-900">{activity}</div>
                    <div className="mt-2 flex items-center gap-2">
                      <div className="h-1.5 w-1.5 rounded-full bg-teal-500" />
                      <span className="text-xs font-semibold text-slate-600">
                        {activityConfidence != null ? (activityConfidence * 100).toFixed(1) + '% confidence' : ''}
                      </span>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="text-2xl font-bold tracking-tight text-slate-400">No data yet</div>
                    <div className="mt-2 text-xs text-slate-400">
                      No activity has been processed for this account.
                    </div>
                  </>
                )}
              </div>

              <div className="mt-5 space-y-2 text-[11px] text-slate-500">
                <div className="flex items-center justify-between">
                  <span>Model</span>
                  <span className="font-semibold text-slate-700">Random Forest</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Sensor features</span>
                  <span className="font-semibold text-slate-700">30 (Accel + Gyro)</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Window</span>
                  <span className="font-semibold text-slate-700">10 s @ 20 Hz</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Data source</span>
                  <span className="rounded bg-slate-100 px-1.5 py-0.5 font-semibold text-slate-600">
                    Simulated telemetry
                  </span>
                </div>
              </div>
            </div>

            {/* B. Preventive Risk */}
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                  Preventive Risk
                </span>
                <div className="rounded-lg border border-rose-200 bg-rose-50 p-2">
                  <ShieldAlert className="h-4 w-4 text-rose-500" />
                </div>
              </div>

              <div className="mt-4">
                {hasData ? (
                  <div className="flex items-baseline gap-3">
                    <span className="text-4xl font-bold tracking-tight text-slate-900">
                      {riskScorePct}
                    </span>
                    {riskBand ? <RiskBadge level={riskBand} size="md" /> : null}
                  </div>
                ) : (
                  <div className="text-2xl font-bold tracking-tight text-slate-400">Awaiting data</div>
                )}
              </div>

              <div className="mt-4">
                {hasData && riskScore != null
                  ? <RiskIndicator score={riskScore} showScale={false} />
                  : <div className="h-2 rounded-full bg-slate-100" />}
              </div>

              <div className="mt-4 rounded-lg bg-slate-50 border border-slate-100 px-3 py-2.5 text-[11px] leading-relaxed text-slate-600">
                {hasData ? riskText : 'No risk assessment available yet for this account.'}
              </div>
            </div>

            {/* C. Smartwatch Data Status */}
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                  Smartwatch Data
                </span>
                <div className="rounded-lg border border-blue-200 bg-blue-50 p-2">
                  <Radio className="h-4 w-4 text-blue-600" />
                </div>
              </div>

              <div className="mt-4 space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-slate-500">Status</span>
                  {hasData ? (
                    <span className="flex items-center gap-1.5 font-semibold text-teal-700">
                      <span className="h-1.5 w-1.5 rounded-full bg-teal-500 animate-pulse" />
                      Connected
                    </span>
                  ) : (
                    <span className="flex items-center gap-1.5 font-semibold text-slate-400">
                      <span className="h-1.5 w-1.5 rounded-full bg-slate-300" />
                      No telemetry received
                    </span>
                  )}
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-slate-500">Source</span>
                  <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-bold text-slate-600">
                    WISDM v2 Dataset
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-slate-500">Activity data</span>
                  <span className={`font-semibold ${hasData ? 'text-slate-800' : 'text-slate-400'}`}>
                    {hasData ? 'Received' : 'Not yet received'}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-slate-500">Transport</span>
                  <span className="font-semibold text-slate-800">AWS IoT Core</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-slate-500">Processing</span>
                  <span className="font-semibold text-slate-800">Lambda → DynamoDB</span>
                </div>
              </div>

              <div className="mt-4 rounded-lg bg-slate-50 border border-slate-100 px-3 py-2.5 text-[10px] leading-relaxed text-slate-400">
                {hasData
                  ? 'Simulated smartwatch telemetry. A real WISDM-trained sensor stream is replayed through AWS IoT Core to drive the ML prediction pipeline.'
                  : 'No telemetry has been processed for this account yet. Run the IoT simulator with your user credentials to generate data.'}
              </div>
            </div>
          </div>

          {/* ── Recommendations + Sidebar ───────────────────────────────── */}
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-5">

            {/* C. Recommendations with Acknowledge */}
            <div className="lg:col-span-3 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-1 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-amber-200 bg-amber-50">
                    <Lightbulb className="h-4 w-4 text-amber-600" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">
                      Your Preventive Recommendations
                    </h3>
                    <p className="text-[10px] text-slate-500">
                      Personalised behavioural interventions — based on activity and risk profile
                    </p>
                  </div>
                </div>
                {riskBand ? <RiskBadge level={riskBand} size="sm" /> : null}
              </div>

              {allAcknowledged && (
                <div className="mt-3 flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-700">
                  <CheckCircle2 className="h-4 w-4" />
                  All recommendations acknowledged. Great job staying engaged with your health!
                </div>
              )}

              <div className="mt-4 space-y-2.5">
                {recList.map((rec, idx) => {
                  const isAck = acknowledgedSet.has(idx);
                  return (
                    <div
                      key={idx}
                      className={`flex items-start justify-between gap-4 rounded-lg border px-4 py-3 transition-colors ${
                        isAck
                          ? 'border-emerald-200 bg-emerald-50/50'
                          : 'border-slate-100 bg-slate-50/50 hover:border-slate-200 hover:bg-white'
                      }`}
                    >
                      <div className="flex min-w-0 items-start gap-2.5">
                        {isAck ? (
                          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
                        ) : (
                          <div className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400" />
                        )}
                        <p
                          className={`text-xs leading-relaxed ${
                            isAck ? 'text-slate-400 line-through' : 'font-medium text-slate-700'
                          }`}
                        >
                          {rec}
                        </p>
                      </div>
                      <button
                        onClick={() => toggleAcknowledge(idx)}
                        className={`shrink-0 rounded-md px-2.5 py-1 text-[10px] font-semibold transition-colors ${
                          isAck
                            ? 'border border-emerald-300 bg-white text-emerald-700 hover:bg-emerald-50'
                            : 'border border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                        }`}
                      >
                        {isAck ? 'Acknowledged ✓' : 'Got it'}
                      </button>
                    </div>
                  );
                })}
              </div>

              <div className="mt-4 rounded-lg border border-amber-100 bg-amber-50/50 px-4 py-2.5 text-[10px] leading-relaxed text-amber-700">
                <strong>Disclaimer:</strong> These are behaviour-based preventive recommendations
                generated from your activity profile and risk estimation model. They are not medical
                diagnoses. Always consult a qualified healthcare professional for medical advice,
                diagnosis, or treatment.
              </div>
            </div>

            {/* Right sidebar: Risk Indicator + Latest Session */}
            <div className="lg:col-span-2 space-y-5">
              {/* Risk Indicator */}
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <h3 className="mb-4 text-[10px] font-bold uppercase tracking-widest text-slate-400">
                  Risk Indicator
                </h3>
                {riskScore != null ? (
                  <RiskIndicator score={riskScore} showScale={true} />
                ) : (
                  <div className="text-xs text-slate-400">No risk score available</div>
                )}
              </div>

              {/* Recent Activity History */}
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                    Recent Activity
                  </h3>
                  <span className="rounded bg-slate-100 px-2 py-0.5 text-[9px] font-bold text-slate-500 uppercase">
                    Latest Record
                  </span>
                </div>
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-100 text-slate-400">
                      <th className="pb-2 font-semibold">Time</th>
                      <th className="pb-2 font-semibold">Activity</th>
                      <th className="pb-2 font-semibold">Risk</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td className="py-3 text-slate-500 whitespace-nowrap">
                        {recommendation?.timestamp
                          ? new Date(recommendation.timestamp).toLocaleTimeString([], {
                              hour: '2-digit',
                              minute: '2-digit',
                            })
                          : 'Latest'}
                      </td>
                      <td className="py-3 font-bold text-slate-900">{activity}</td>
                      <td className="py-3">
                        {riskBand ? <RiskBadge level={riskBand} size="sm" /> : null}
                      </td>
                    </tr>
                  </tbody>
                </table>
                <p className="mt-3 text-[10px] text-slate-400">
                  Showing the most recent session from the recommendation pipeline.
                  Visit the Activity page for full sensor telemetry details.
                </p>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}