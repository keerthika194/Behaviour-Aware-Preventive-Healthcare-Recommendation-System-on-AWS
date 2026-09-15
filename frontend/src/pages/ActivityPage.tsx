import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Header } from '../components/layout/Header';
import { StatCard } from '../components/common/StatCard';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { getRecommendations, RecommendationResponse } from '../services/api';
import { Activity, Radio, Cpu, AlertCircle } from 'lucide-react';

export const ActivityPage: React.FC = () => {
  const { user } = useAuth();
  const [data, setData] = useState<RecommendationResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchActivityData = async () => {
    const userId = user?.userSub;
    if (!userId) {
      setError('User session not found. Please sign in again.');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const result = await getRecommendations(userId);
      if (Array.isArray(result) && result.length > 0) {
        setData(result[0]);
      } else {
        setData(null);
      }
    } catch (err: any) {
      setError(err.message || 'Unable to load activity telemetry data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActivityData();
  }, [user]);

  const hasData = data !== null;
  const activityName = data?.activity ?? null;
  const confidencePct = data?.activity_confidence != null
    ? (Number(data.activity_confidence) * 100).toFixed(2) + '%'
    : null;
  const timestamp = data?.timestamp
    ? new Date(data.timestamp).toLocaleString()
    : null;

  return (
    <div className="space-y-6">
      <Header
        title="Smartwatch Activity Recognition"
        description="Real-time physical activity classification derived from 30 smartwatch sensor features."
        onRefresh={fetchActivityData}
        isRefreshing={loading}
      />

      {loading && <LoadingState message="Fetching activity stream..." />}
      {!loading && error && <ErrorState message={error} onRetry={fetchActivityData} />}

      {!loading && !error && (
        <>
          {/* Top Activity Stat Cards */}
          <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
            <StatCard
              title="Detected Activity"
              value={hasData && activityName ? activityName : 'No activity yet'}
              subtitle={hasData ? 'Random Forest Model Prediction' : 'Awaiting sensor stream'}
              icon={<Activity className="h-5 w-5 text-teal-600" />}
            />

            <StatCard
              title="Activity Confidence"
              value={hasData && confidencePct ? confidencePct : 'N/A'}
              subtitle={hasData ? 'Maximum Class Probability' : 'No probability score'}
              icon={<Radio className="h-5 w-5 text-blue-600" />}
            />

            <StatCard
              title="Sensor Telemetry Windows"
              value="30 Features"
              subtitle="10s Windows @ 20 Hz Accel & Gyro"
              icon={<Cpu className="h-5 w-5 text-slate-600" />}
            />
          </div>

          {/* Activity Classification History */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Activity Telemetry History</h3>
                <p className="text-xs text-slate-500">
                  Recorded physical activity windows from simulated smartwatch IoT stream
                </p>
              </div>
              <span className="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
                WISDM v2 — Sensor Stream
              </span>
            </div>

            {hasData ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50 text-slate-500">
                      <th className="py-3 px-4 font-semibold">Detected Activity</th>
                      <th className="py-3 px-4 font-semibold">Confidence Score</th>
                      <th className="py-3 px-4 font-semibold">Sensor Axis Features</th>
                      <th className="py-3 px-4 font-semibold">Window Interval</th>
                      <th className="py-3 px-4 font-semibold">Recorded Timestamp</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    <tr className="hover:bg-slate-50/50">
                      <td className="py-3.5 px-4 font-bold text-slate-900">{activityName}</td>
                      <td className="py-3.5 px-4 text-slate-600 font-medium">{confidencePct}</td>
                      <td className="py-3.5 px-4 text-slate-500">30 features (Accel + Gyro)</td>
                      <td className="py-3.5 px-4 text-slate-500">10 seconds (200 samples)</td>
                      <td className="py-3.5 px-4 text-slate-500">{timestamp}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-10 text-center">
                <AlertCircle className="h-10 w-10 text-slate-300 mb-3" />
                <p className="text-sm font-bold text-slate-700">No activity data recorded yet</p>
                <p className="text-xs text-slate-400 max-w-md mt-1">
                  Run the IoT smartwatch simulator and ML processing pipeline to populate activity telemetry for your account.
                </p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
