import React from 'react';
import { Header } from '../components/layout/Header';
import { EmptyState } from '../components/common/EmptyState';
import { Bell } from 'lucide-react';

export const NotificationsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <Header
        title="Notifications & System Advisories"
        description="System alerts and real-time activity threshold notifications."
      />

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <EmptyState
          title="No new notifications"
          description="All physical activity and preventive risk notifications have been acknowledged."
        />
      </div>
    </div>
  );
};
