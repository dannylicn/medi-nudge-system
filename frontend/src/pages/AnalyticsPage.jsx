import { useState, useEffect } from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { getAdherenceAnalytics, getEscalationAnalytics } from "../lib/api";

export default function AnalyticsPage() {
  const [adherence, setAdherence] = useState([]);
  const [escalations, setEscalations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [{ data: adh }, { data: esc }] = await Promise.all([
          getAdherenceAnalytics({ days }),
          getEscalationAnalytics({ days }),
        ]);
        setAdherence(adh);
        setEscalations(esc);
      } catch {
        // interceptor handles
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [days]);

  return (
    <div className="p-6 max-w-5xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-display text-2xl font-bold text-on-surface tracking-tight">Analytics</h1>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="bg-surface-container-highest rounded-xl px-3.5 py-2 font-body text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary-fixed transition-shadow"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {loading ? (
        <div className="py-16 text-center font-body text-on-surface/30">Loading…</div>
      ) : (
        <div className="space-y-5">
          {/* Adherence rate over time */}
          <div className="bg-surface-container-lowest rounded-2xl shadow-ambient p-6">
            <h2 className="font-display text-base font-bold text-on-surface mb-5">Adherence Rate Over Time</h2>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={adherence}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e0e3e5" />
                <XAxis dataKey="date" tick={{ fontSize: 11, fontFamily: "Inter" }} />
                <YAxis
                  tickFormatter={(v) => `${v}%`}
                  domain={[0, 100]}
                  tick={{ fontSize: 11, fontFamily: "Inter" }}
                />
                <Tooltip formatter={(v) => [`${v}%`, "Adherence"]} />
                <Line
                  type="monotone"
                  dataKey="adherence_rate"
                  stroke="#006565"
                  strokeWidth={2.5}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Escalation volume */}
          <div className="bg-surface-container-lowest rounded-2xl shadow-ambient p-6">
            <h2 className="font-display text-base font-bold text-on-surface mb-5">Escalation Volume by Week</h2>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={escalations}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e0e3e5" />
                <XAxis dataKey="week" tick={{ fontSize: 11, fontFamily: "Inter" }} />
                <YAxis tick={{ fontSize: 11, fontFamily: "Inter" }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="urgent" fill="#ba1a1a" name="Urgent" />
                <Bar dataKey="high" fill="#f97316" name="High" />
                <Bar dataKey="medium" fill="#206393" name="Medium" />
                <Bar dataKey="low" fill="#bdc9c8" name="Low" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
