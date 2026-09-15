import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { getRecommendations, RecommendationResponse } from '../services/api';
import { RiskIndicator } from '../components/common/RiskIndicator';
import { Header } from '../components/layout/Header';
import { RiskBadge } from '../components/common/RiskBadge';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { ShieldAlert, Info, AlertCircle, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

export function RiskPage() {
  const { user } = useAuth();
  const [recommendation, setRecommendation] = useState<RecommendationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadRiskData = async () => {
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
      console.warn('Risk data error:', err.message);
      setError(err.message || 'Failed to fetch risk data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRiskData();
  }, [user]);

  const hasData = recommendation !== null;
  const riskScore = recommendation?.risk_score != null ? Number(recommendation.risk_score) : null;
  const riskBand = recommendation?.risk_band ?? null;

  const bandDescription: Record<string, string> = {
    High:
      'Your current preventive risk level is high. Maintaining healthy habits and discussing persistent health concerns with a qualified healthcare professional is recommended.',
    Medium:
      'Your current preventive risk level is moderate. Continue regular physical activity, healthy eating habits, and consistent health monitoring.',
    Low:
      'Your current preventive risk level is low. Continue maintaining healthy daily habits and regular physical activity.',
  };
  const descriptionText = riskBand ? (bandDescription[riskBand] ?? bandDescription['Low']) : '';

  return (
    <div className="space-y-6">
      <Header
        title="Preventive Risk Assessment"
        description="View your current preventive health risk assessment derived from the XGBoost predictive model."
        onRefresh={loadRiskData}
        isRefreshing={loading}
      />

      {loading && <LoadingState message="Loading risk assessment..." />}
      {!loading && error && <ErrorState message={error} onRetry={loadRiskData} />}

      {!loading && !error && (
        <div className="space-y-5">
          {/* Current Risk Score Card */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-5 flex items-center justify-between border-b border-slate-100 pb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-rose-50 text-rose-600 border border-rose-200">
                  <ShieldAlert className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Current Risk Score</h3>
                  <span className="text-[11px] text-slate-500">XGBoost Predictive Model Output</span>
                </div>
              </div>
              {riskBand && <RiskBadge level={riskBand} size="lg" />}
            </div>

            {/* Large score display */}
            {hasData && riskScore != null ? (
              <>
                <div className="mb-6 flex items-center justify-center py-4">
                  <div className="text-center">
                    <span className="block text-5xl font-bold tracking-tight text-slate-900">
                      {(riskScore * 100).toFixed(2)}%
                    </span>
                    <span className="mt-1 block text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Model-Estimated Preventive Risk
                    </span>
                  </div>
                </div>
                <RiskIndicator score={riskScore} showScale={true} />
              </>
            ) : (
              <div className="flex flex-col items-center justify-center py-10 text-center">
                <AlertCircle className="h-10 w-10 text-slate-300 mb-3" />
                <p className="text-sm font-bold text-slate-700">No risk assessment available yet</p>
                <p className="text-xs text-slate-400 max-w-md mt-1 mb-4">
                  Please complete your health profile on the Profile page, run the IoT simulator, and execute the ML processing pipeline.
                </p>
                <Link
                  to="/profile"
                  className="flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-teal-700 transition-colors"
                >
                  <span>Complete Health Profile</span>
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </div>
            )}
          </div>

          {/* Risk Band Threshold Reference */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="mb-4 text-sm font-bold text-slate-900 border-b border-slate-100 pb-3">
              Risk Band Thresholds
            </h3>
            <div className="grid grid-cols-3 gap-4">
              <div className="rounded-lg border border-emerald-200 bg-emerald-50/60 p-4">
                <span className="block text-xs font-bold text-emerald-800 uppercase tracking-wider">Low Risk</span>
                <span className="mt-1 block text-lg font-bold text-emerald-700">0% – 35%</span>
                <p className="mt-1 text-[11px] text-emerald-700/80">Maintain current habits. No immediate intervention required.</p>
              </div>
              <div className="rounded-lg border border-amber-200 bg-amber-50/60 p-4">
                <span className="block text-xs font-bold text-amber-800 uppercase tracking-wider">Medium Risk</span>
                <span className="mt-1 block text-lg font-bold text-amber-700">35% – 65%</span>
                <p className="mt-1 text-[11px] text-amber-700/80">Moderate concern. Increase activity and monitor regularly.</p>
              </div>
              <div className="rounded-lg border border-rose-200 bg-rose-50/60 p-4">
                <span className="block text-xs font-bold text-rose-800 uppercase tracking-wider">High Risk</span>
                <span className="mt-1 block text-lg font-bold text-rose-700">65% – 100%</span>
                <p className="mt-1 text-[11px] text-rose-700/80">Elevated concern. Consult a qualified healthcare professional.</p>
              </div>
            </div>
          </div>

          {/* What This Means */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="mb-3 text-sm font-bold text-slate-900 border-b border-slate-100 pb-3">
              What This Means
            </h3>
            <p className="text-sm font-medium leading-relaxed text-slate-700">
              {hasData && descriptionText ? descriptionText : 'Complete your profile and run the ML processing pipeline to view your personalized risk interpretation.'}
            </p>

            {/* Medical disclaimer */}
            <div className="mt-5 flex items-start gap-2.5 rounded-lg border border-slate-200 bg-slate-50 p-3.5">
              <Info className="h-4 w-4 shrink-0 mt-0.5 text-slate-400" />
              <p className="text-[11px] leading-relaxed text-slate-500">
                <strong className="font-semibold text-slate-700">Medical Disclaimer:</strong> This risk score is
                generated by an XGBoost machine learning model trained on the BRFSS 2015 dataset for academic
                demonstration purposes only. It is not a clinical diagnosis. Always consult a qualified healthcare
                professional for medical advice, diagnosis, or treatment.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}