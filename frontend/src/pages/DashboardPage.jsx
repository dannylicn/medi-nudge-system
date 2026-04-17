import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { getDashboardSummary, updateEscalation } from "../lib/api";

const RISK_CHIP = {
  high: "bg-error-container text-on-error-container",
  normal: "bg-secondary-container text-secondary",
  low: "bg-tertiary-container text-on-tertiary-container",
};

const RISK_BAR = {
  high: "bg-error",
  normal: "bg-secondary",
  low: "bg-tertiary-container",
};

const PRIORITY_STYLE = {
  urgent: "bg-error-container/30 border-l-4 border-error",
  high: "bg-error-container/20 border-l-4 border-error/60",
  normal: "bg-surface-container-low",
  low: "bg-surface-container-low",
};

export default function DashboardPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const { data: d } = await getDashboardSummary();
      setData(d);
    } catch {
      // interceptor handles
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) {
    return <div className="p-8 text-center font-body text-on-surface/30">Loading dashboard...</div>;
  }

  if (!data) {
    return <div className="p-8 text-center font-body text-on-surface/30">Failed to load dashboard</div>;
  }

  const handleDismissEscalation = async (id) => {
    try {
      await updateEscalation(id, { status: "resolved" });
      load();
    } catch { /* */ }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* Hero Metrics Bento Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        {/* Overall Adherence — large teal gradient card */}
        <div className="md:col-span-2 bg-gradient-to-br from-primary to-primary-container p-8 rounded-3xl text-white shadow-xl relative overflow-hidden">
          <div className="relative z-10">
            <p className="text-primary-fixed-dim font-body font-medium mb-1">Overall Adherence</p>
            <h2 className="text-5xl font-display font-extrabold mb-4">{data.overall_adherence}%</h2>
            <div className="flex items-center gap-2 bg-white/10 w-fit px-3 py-1 rounded-full text-xs font-body">
              <span>{data.adherence_trend >= 0 ? "+" : ""}{data.adherence_trend}% from last month</span>
            </div>
          </div>
          <div className="absolute -right-12 -bottom-12 w-48 h-48 bg-white/10 rounded-full blur-3xl" />
        </div>

        {/* High Risk Patients */}
        <div className="bg-surface-container-lowest p-6 rounded-3xl shadow-ambient flex flex-col justify-between">
          <div>
            <div className="w-10 h-10 rounded-full bg-error-container text-error flex items-center justify-center mb-4 text-lg">
              !!
            </div>
            <p className="text-on-surface/50 font-body text-sm font-medium">High Risk Patients</p>
          </div>
          <div>
            <h3 className="text-3xl font-display font-bold text-on-surface">{data.high_risk_count}</h3>
            <p className="text-xs text-error font-semibold mt-1">Requires Immediate Action</p>
          </div>
        </div>

        {/* Pending Refills */}
        <div className="bg-surface-container-lowest p-6 rounded-3xl shadow-ambient flex flex-col justify-between">
          <div>
            <div className="w-10 h-10 rounded-full bg-secondary-container text-secondary flex items-center justify-center mb-4 text-lg">
              Rx
            </div>
            <p className="text-on-surface/50 font-body text-sm font-medium">Pending Refills</p>
          </div>
          <div>
            <h3 className="text-3xl font-display font-bold text-on-surface">{data.pending_refills}</h3>
            <p className="text-xs text-on-surface/40 mt-1">Awaiting patient response</p>
          </div>
        </div>
      </div>

      {/* Content: Table + Sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Patient Adherence Registry */}
        <div className="lg:col-span-2 bg-surface-container-lowest rounded-3xl shadow-ambient overflow-hidden">
          <div className="p-6 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-display font-bold text-on-surface">Patient Adherence Registry</h3>
              <p className="text-xs text-on-surface/40 font-body">Real-time tracking of medication compliance</p>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-surface-container-low text-on-surface/40 text-[10px] uppercase tracking-wider font-body">
                  <th className="px-6 py-4 font-bold">Patient</th>
                  <th className="px-6 py-4 font-bold">Risk Level</th>
                  <th className="px-6 py-4 font-bold">Last Refill</th>
                  <th className="px-6 py-4 font-bold">Adherence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/30">
                {data.at_risk_patients.map((p) => (
                  <tr key={p.id} className="hover:bg-surface-container-low/50 transition-colors">
                    <td className="px-6 py-5">
                      <Link to={`/patients/${p.id}`} className="text-sm font-bold text-on-surface hover:text-primary">
                        {p.full_name}
                      </Link>
                    </td>
                    <td className="px-6 py-5">
                      <span className={`px-3 py-1 rounded-full text-[10px] font-bold uppercase ${RISK_CHIP[p.risk_level] || RISK_CHIP.normal}`}>
                        {p.risk_level === "high" ? "HIGH RISK" : p.risk_level === "low" ? "ON TRACK" : "MODERATE"}
                      </span>
                    </td>
                    <td className="px-6 py-5">
                      <p className="text-xs text-on-surface">
                        {p.last_refill ? new Date(p.last_refill).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "No record"}
                      </p>
                      {p.days_overdue > 0 && (
                        <p className="text-[10px] text-error font-medium">{p.days_overdue} Days Overdue</p>
                      )}
                    </td>
                    <td className="px-6 py-5">
                      <div className="w-24 h-1.5 bg-surface-container-highest rounded-full overflow-hidden">
                        <div
                          className={`h-full ${RISK_BAR[p.risk_level] || RISK_BAR.normal}`}
                          style={{ width: `${Math.min(p.adherence_rate, 100)}%` }}
                        />
                      </div>
                      <p className="text-[10px] text-on-surface/40 mt-1">{p.adherence_rate}% doses taken</p>
                    </td>
                  </tr>
                ))}
                {data.at_risk_patients.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-6 py-10 text-center text-on-surface/30 font-body text-sm">
                      No patient data yet
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Sidebar: Escalations */}
        <div className="space-y-6">
          <div className="bg-surface-container-lowest p-6 rounded-3xl shadow-ambient">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-md font-display font-bold text-on-surface">Pending Escalations</h3>
              {data.pending_escalations.length > 0 && (
                <span className="bg-error text-white text-[10px] px-2 py-0.5 rounded-full font-bold">
                  {data.pending_escalations.length} NEW
                </span>
              )}
            </div>
            <div className="space-y-4">
              {data.pending_escalations.map((e) => (
                <div key={e.id} className={`p-4 rounded-2xl ${PRIORITY_STYLE[e.priority] || PRIORITY_STYLE.normal}`}>
                  <p className="text-xs font-bold text-on-surface capitalize">{e.reason.replace(/_/g, " ")}</p>
                  <p className="text-[11px] text-on-surface/60 mt-1">
                    {e.patient_name} — {e.priority} priority
                  </p>
                  <div className="mt-3 flex gap-2">
                    <Link
                      to={`/patients/${e.patient_id}`}
                      className="text-[10px] bg-primary text-white px-3 py-1 rounded-full font-bold hover:opacity-90"
                    >
                      View Patient
                    </Link>
                    <button
                      onClick={() => handleDismissEscalation(e.id)}
                      className="text-[10px] bg-white text-on-surface px-3 py-1 rounded-full border border-outline-variant hover:bg-surface-container-low"
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              ))}
              {data.pending_escalations.length === 0 && (
                <p className="text-sm text-on-surface/30 font-body text-center py-4">No pending escalations</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
