import React from "react";

function StatCard({ label, value, color }) {
  return (
    <div className="bg-white rounded-lg border p-4 flex-1 min-w-[120px]">
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`text-2xl font-semibold ${color}`}>{value}</p>
    </div>
  );
}

export default function StatsBar({ stats }) {
  if (!stats) return null;
  return (
    <div className="flex gap-3 flex-wrap">
      <StatCard label="Total Cards" value={stats.total} color="text-gray-900" />
      <StatCard label="Extracted" value={stats.success} color="text-green-600" />
      <StatCard label="Failed" value={stats.failed} color="text-red-600" />
      <StatCard label="Duplicates" value={stats.duplicates} color="text-yellow-600" />
    </div>
  );
}
