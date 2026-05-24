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
import { getAdherenceAnalytics, getEscalationAnalytics, getDoseAdherence, getCriticalAdherence, getMissedDoseHeatmap } from "../lib/api";

export default function AnalyticsPage() {
  const [adherence, setAdherence] = useState([]);
  const [escalations, setEscalations] = useState([]);
  const [doseAdherence, setDoseAdherence] = useState([]);
  const [doseByMed, setDoseByMed] = useState([]);
  const [criticalAdherence, setCriticalAdherence] = useState([]);
  const [heatmap, setHeatmap] = useState([]);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [{ data: adh }, { data: esc }, { data: dose }, { data: doseMed }, { data: critAdh }, { data: hm }] = await Promise.all([
          getAdherenceAnalytics({ days }),
          getEscalationAnalytics({ days }),
          getDoseAdherence({ days }),
          getDoseAdherence({ days, group_by: "medication" }),
          getCriticalAdherence({ days }),
          getMissedDoseHeatmap({ days }),
        ]);
        setAdherence(adh);
        setEscalations(esc);
        setDoseAdherence(dose);
        setDoseByMed(doseMed);
        setCriticalAdherence(critAdh);
        setHeatmap(hm);
      } catch {
        // interceptor handles
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [days]);

  return (
    <div className="p-6 max-w-5xl w-full mx-auto">
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
        <div className="py-16 text-center font-body text-on-surface/30">Loading...</div>
      ) : (
        <div className="space-y-5">
          {/* Refill Adherence Rate — hidden for mid-review, uncomment for final pitch
          <div className="bg-surface-container-lowest rounded-2xl shadow-ambient p-6">
            <h2 className="font-display text-base font-bold text-on-surface mb-5">Refill Adherence Rate</h2>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={adherence}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e0e3e5" />
                <XAxis dataKey="week" tick={{ fontSize: 11, fontFamily: "Inter" }} />
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
          */}

          {/* Dose adherence rate over time */}
          <div className="bg-surface-container-lowest rounded-2xl shadow-ambient p-6">
            <h2 className="font-display text-base font-bold text-on-surface mb-5">Dose Adherence Rate</h2>
            {doseAdherence.length === 0 ? (
              <p className="font-body text-sm text-on-surface/30 py-8 text-center">No dose data yet</p>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={doseAdherence}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e0e3e5" />
                  <XAxis dataKey="week" tick={{ fontSize: 11, fontFamily: "Inter" }} />
                  <YAxis
                    tickFormatter={(v) => `${v}%`}
                    domain={[0, 100]}
                    tick={{ fontSize: 11, fontFamily: "Inter" }}
                  />
                  <Tooltip formatter={(v) => [`${v}%`, "Adherence"]} />
                  <Line type="monotone" dataKey="adherence_rate" stroke="#006565" strokeWidth={2.5} dot={false} name="Adherence %" />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Per-medication adherence table */}
          <div className="bg-surface-container-lowest rounded-2xl shadow-ambient p-6">
            <h2 className="font-display text-base font-bold text-on-surface mb-4">Adherence by Medication</h2>
            {doseByMed.length === 0 ? (
              <p className="font-body text-sm text-on-surface/30 py-8 text-center">No dose data yet</p>
            ) : (
              <div className="overflow-hidden rounded-xl">
                <table className="w-full font-body text-sm">
                  <thead className="bg-surface-container-highest text-on-surface/40 text-xs uppercase tracking-widest">
                    <tr>
                      <th className="px-4 py-3 text-left">Medication</th>
                      <th className="px-4 py-3 text-right">Total</th>
                      <th className="px-4 py-3 text-right">Taken</th>
                      <th className="px-4 py-3 text-right">Missed</th>
                      <th className="px-4 py-3 text-right">Adherence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {doseByMed.map((m, i) => (
                      <tr key={m.medication_id} className={i % 2 === 0 ? "bg-surface-container-lowest" : "bg-surface-container-low"}>
                        <td className="px-4 py-2.5 font-medium text-on-surface">{m.medication_name}</td>
                        <td className="px-4 py-2.5 text-right text-on-surface/60">{m.total}</td>
                        <td className="px-4 py-2.5 text-right text-tertiary-container font-semibold">{m.taken}</td>
                        <td className="px-4 py-2.5 text-right text-error font-semibold">{m.missed}</td>
                        <td className="px-4 py-2.5 text-right">
                          <span className={`px-2 py-0.5 rounded-pill text-xs font-semibold ${
                            m.adherence_rate >= 80 ? "bg-tertiary-container text-on-tertiary-container" :
                            m.adherence_rate >= 50 ? "bg-yellow-100 text-yellow-800" :
                            "bg-error-container text-on-error-container"
                          }`}>
                            {m.adherence_rate}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Critical vs Non-Critical Adherence */}
          {criticalAdherence.length > 0 && (
            <div className="bg-surface-container-lowest rounded-2xl shadow-ambient p-6">
              <h2 className="font-display text-base font-bold text-on-surface mb-5">Critical vs Non-Critical Medication Adherence</h2>
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={criticalAdherence}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e0e3e5" />
                  <XAxis dataKey="week" tick={{ fontSize: 11, fontFamily: "Inter" }} />
                  <YAxis tickFormatter={(v) => `${v}%`} domain={[0, 100]} tick={{ fontSize: 11, fontFamily: "Inter" }} />
                  <Tooltip formatter={(v) => [`${v}%`]} />
                  <Legend />
                  <Line type="monotone" dataKey="critical_adherence" stroke="#ba1a1a" strokeWidth={2.5} dot={false} name="Critical Medications" />
                  <Line type="monotone" dataKey="non_critical_adherence" stroke="#006565" strokeWidth={2.5} dot={false} name="Non-Critical Medications" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Missed Dose Heatmap */}
          {heatmap.length > 0 && (() => {
            const maxCount = Math.max(...heatmap.map(h => h.missed_count), 1);
            const days_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
            const slots = ["Morning", "Afternoon", "Evening", "Night"];
            const getCount = (day, slot) => heatmap.find(h => h.day === day && h.time_slot === slot)?.missed_count || 0;
            return (
              <div className="bg-surface-container-lowest rounded-2xl shadow-ambient p-6">
                <h2 className="font-display text-base font-bold text-on-surface mb-2">Missed Doses by Day & Time</h2>
                <p className="text-xs text-on-surface/50 mb-5">Darker red = more missed doses. Helps identify when patients are most likely to forget.</p>
                <div className="overflow-hidden rounded-xl">
                  <table className="w-full font-body text-sm">
                    <thead>
                      <tr>
                        <th className="px-3 py-2 text-left text-[10px] text-on-surface/40 uppercase tracking-widest"></th>
                        {days_order.map(d => <th key={d} className="px-3 py-2 text-center text-[10px] text-on-surface/40 uppercase tracking-widest">{d}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {slots.map(slot => (
                        <tr key={slot}>
                          <td className="px-3 py-2 text-xs font-medium text-on-surface/60">{slot}</td>
                          {days_order.map(day => {
                            const count = getCount(day, slot);
                            const intensity = count > 0 ? 0.15 + (count / maxCount) * 0.7 : 0;
                            return (
                              <td key={day} className="px-3 py-2 text-center">
                                <div
                                  className="w-full py-2 rounded-lg text-xs font-bold"
                                  style={{ backgroundColor: count > 0 ? `rgba(186, 26, 26, ${intensity})` : "rgba(0,0,0,0.03)", color: intensity > 0.4 ? "white" : "rgba(0,0,0,0.6)" }}
                                >
                                  {count}
                                </div>
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            );
          })()}

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
