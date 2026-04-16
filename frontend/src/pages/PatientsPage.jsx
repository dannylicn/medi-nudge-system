import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { getPatients, createPatient, getConditions, triggerNudgeCampaigns, triggerDailyReminders } from "../lib/api";

const RISK_CHIP = {
  high: "bg-error-container text-on-error-container",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-tertiary-container text-on-tertiary-container",
};

export default function PatientsPage() {
  const [patients, setPatients] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [showEnrol, setShowEnrol] = useState(false);
  const [newPatient, setNewPatient] = useState({
    full_name: "",
    phone_number: "",
    nric: "",
    language_preference: "en",
    conditions: [],
    caregiver_name: "",
    caregiver_phone_number: "",
  });
  const [enrolling, setEnrolling] = useState(false);
  const [conditionsList, setConditionsList] = useState([]);
  const [triggeringNudge, setTriggeringNudge] = useState(false);
  const [triggeringReminder, setTriggeringReminder] = useState(false);
  const [triggerResult, setTriggerResult] = useState(null);
  const PAGE_SIZE = 20;

  useEffect(() => {
    getConditions().then(({ data }) => setConditionsList(data)).catch(() => {});
  }, []);

  const fetchPatients = async () => {
    setLoading(true);
    try {
      const { data } = await getPatients({
        page,
        page_size: PAGE_SIZE,
        search: search || undefined,
        risk_level: riskFilter || undefined,
      });
      setPatients(data.items);
      setTotal(data.total);
    } catch {
      // handled by interceptor
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPatients();
  }, [page, riskFilter]);

  useEffect(() => {
    const t = setTimeout(fetchPatients, 350);
    return () => clearTimeout(t);
  }, [search]);

  const handleEnrol = async (e) => {
    e.preventDefault();
    setEnrolling(true);
    try {
      await createPatient(newPatient);
      setShowEnrol(false);
      setNewPatient({ full_name: "", phone_number: "", nric: "", language_preference: "en", conditions: [], caregiver_name: "", caregiver_phone_number: "" });
      fetchPatients();
    } catch {
      // leave form open
    } finally {
      setEnrolling(false);
    }
  };

  const handleTriggerNudge = async () => {
    setTriggeringNudge(true);
    setTriggerResult(null);
    try {
      const { data } = await triggerNudgeCampaigns();
      setTriggerResult(`Nudge: ${data.campaigns_created} campaigns created, ${data.checked} checked`);
    } catch {
      setTriggerResult("Failed to trigger nudge campaigns");
    } finally {
      setTriggeringNudge(false);
      setTimeout(() => setTriggerResult(null), 5000);
    }
  };

  const handleTriggerReminder = async () => {
    setTriggeringReminder(true);
    setTriggerResult(null);
    try {
      const { data } = await triggerDailyReminders();
      setTriggerResult(`Reminders: ${data.reminders_sent} sent, ${data.patients_checked} patients checked`);
    } catch {
      setTriggerResult("Failed to trigger daily reminders");
    } finally {
      setTriggeringReminder(false);
      setTimeout(() => setTriggerResult(null), 5000);
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display text-2xl font-bold text-on-surface tracking-tight">Patients</h1>
          <p className="font-body text-sm text-on-surface/50">{total} total</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleTriggerNudge}
            disabled={triggeringNudge}
            className="font-body text-xs text-primary border border-primary/30 rounded-pill px-3 py-1.5 hover:bg-primary/5 disabled:opacity-60 transition-colors"
          >
            {triggeringNudge ? "Triggering…" : "Trigger Nudge"}
          </button>
          <button
            onClick={handleTriggerReminder}
            disabled={triggeringReminder}
            className="font-body text-xs text-primary border border-primary/30 rounded-pill px-3 py-1.5 hover:bg-primary/5 disabled:opacity-60 transition-colors"
          >
            {triggeringReminder ? "Triggering…" : "Trigger Reminder"}
          </button>
          <button
            onClick={() => setShowEnrol(true)}
            className="bg-gradient-to-br from-primary to-primary-container text-white font-body text-sm font-semibold px-5 py-2.5 rounded-pill transition-opacity hover:opacity-90"
          >
            + Enrol Patient
          </button>
        </div>
      </div>

      {triggerResult && (
        <div className="mb-4 px-4 py-2.5 bg-tertiary-container/20 border border-tertiary-container/30 rounded-xl font-body text-sm text-on-surface/70">
          {triggerResult}
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 mb-5">
        <input
          type="text"
          placeholder="Search by name or phone…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="bg-surface-container-highest rounded-xl px-3.5 py-2 font-body text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary-fixed w-64 transition-shadow"
        />
        <select
          value={riskFilter}
          onChange={(e) => { setRiskFilter(e.target.value); setPage(1); }}
          className="bg-surface-container-highest rounded-xl px-3.5 py-2 font-body text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary-fixed transition-shadow"
        >
          <option value="">All risk levels</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>

      {/* Patient cards — no border table; cards on surface-container-low */}
      <div className="bg-surface-container-low rounded-2xl overflow-hidden shadow-ambient">
        <table className="w-full font-body text-sm">
          <thead className="bg-surface-container-lowest text-on-surface/40 text-xs uppercase tracking-widest">
            <tr>
              <th className="px-5 py-3.5 text-left">Name</th>
              <th className="px-5 py-3.5 text-left">Phone</th>
              <th className="px-5 py-3.5 text-left">Language</th>
              <th className="px-5 py-3.5 text-left">Risk</th>
              <th className="px-5 py-3.5 text-left">Onboarding</th>
              <th className="px-5 py-3.5 text-left">Active</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="px-5 py-10 text-center text-on-surface/30">
                  Loading…
                </td>
              </tr>
            ) : patients.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-5 py-10 text-center text-on-surface/30">
                  No patients found
                </td>
              </tr>
            ) : (
              patients.map((p, i) => (
                <tr
                  key={p.id}
                  className={`transition-colors hover:bg-surface-container-highest/40 ${
                    i % 2 === 0 ? "bg-surface-container-lowest" : "bg-surface-container-low"
                  }`}
                >
                  <td className="px-5 py-3.5">
                    <Link
                      to={`/patients/${p.id}`}
                      className="text-primary font-medium hover:underline"
                    >
                      {p.full_name}
                    </Link>
                  </td>
                  <td className="px-5 py-3.5 text-on-surface/60">{p.phone_number}</td>
                  <td className="px-5 py-3.5 text-on-surface/60 uppercase">{p.language_preference}</td>
                  <td className="px-5 py-3.5">
                    <span className={`px-2.5 py-0.5 rounded-pill text-xs font-semibold ${RISK_CHIP[p.risk_level] || "bg-surface-container-highest text-on-surface/60"}`}>
                      {p.risk_level}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 text-on-surface/50 text-xs">{p.onboarding_state}</td>
                  <td className="px-5 py-3.5">
                    <span className={`inline-block w-2 h-2 rounded-full ${p.is_active ? "bg-tertiary-container" : "bg-surface-container-highest"}`} />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-5 py-3.5 bg-surface-container-lowest flex items-center justify-between font-body text-sm text-on-surface/50">
            <span>
              Page {page} of {totalPages}
            </span>
            <div className="flex gap-2">
              <button
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
                className="px-3 py-1 rounded-xl bg-surface-container-highest disabled:opacity-40 hover:bg-outline-variant/30 transition-colors"
              >
                ← Prev
              </button>
              <button
                disabled={page === totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1 rounded-xl bg-surface-container-highest disabled:opacity-40 hover:bg-outline-variant/30 transition-colors"
              >
                Next →
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Enrol modal */}
      {showEnrol && (
        <div className="fixed inset-0 bg-on-surface/40 flex items-center justify-center z-50">
          <div className="bg-surface-container-lowest/90 backdrop-blur-[20px] rounded-2xl shadow-float p-6 w-full max-w-md">
            <h2 className="font-display text-xl font-bold text-on-surface mb-5">Enrol New Patient</h2>
            <form onSubmit={handleEnrol} className="space-y-4">
              <div>
                <label className="block font-body text-xs font-medium text-on-surface/70 mb-1.5">Full Name</label>
                <input
                  type="text"
                  required
                  value={newPatient.full_name}
                  onChange={(e) => setNewPatient((prev) => ({ ...prev, full_name: e.target.value }))}
                  className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 font-body text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary-fixed"
                />
              </div>
              <div>
                <label className="block font-body text-xs font-medium text-on-surface/70 mb-1.5">NRIC / FIN</label>
                <input
                  type="text"
                  required
                  placeholder="S1234567A"
                  value={newPatient.nric}
                  onChange={(e) => setNewPatient((prev) => ({ ...prev, nric: e.target.value.toUpperCase() }))}
                  className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 font-body text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary-fixed"
                />
              </div>
              <div>
                <label className="block font-body text-xs font-medium text-on-surface/70 mb-1.5">Phone (E.164)</label>
                <input
                  type="text"
                  required
                  placeholder="+6598765432"
                  value={newPatient.phone_number}
                  onChange={(e) => setNewPatient((prev) => ({ ...prev, phone_number: e.target.value }))}
                  className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 font-body text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary-fixed"
                />
              </div>
              <div>
                <label className="block font-body text-xs font-medium text-on-surface/70 mb-1.5">Language</label>
                <select
                  value={newPatient.language_preference}
                  onChange={(e) => setNewPatient((prev) => ({ ...prev, language_preference: e.target.value }))}
                  className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 font-body text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary-fixed"
                >
                  <option value="en">English</option>
                  <option value="zh">Chinese</option>
                  <option value="ms">Malay</option>
                  <option value="ta">Tamil</option>
                </select>
              </div>
              <div>
                <label className="block font-body text-xs font-medium text-on-surface/70 mb-1.5">Caregiver Name <span className="text-on-surface/40 font-normal">(optional)</span></label>
                <input
                  type="text"
                  placeholder="e.g. Jane Doe"
                  value={newPatient.caregiver_name}
                  onChange={(e) => setNewPatient((prev) => ({ ...prev, caregiver_name: e.target.value }))}
                  className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 font-body text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary-fixed"
                />
              </div>
              <div>
                <label className="block font-body text-xs font-medium text-on-surface/70 mb-1.5">Caregiver Phone <span className="text-on-surface/40 font-normal">(optional — WhatsApp invite will be sent)</span></label>
                <input
                  type="text"
                  placeholder="+6591234567"
                  value={newPatient.caregiver_phone_number}
                  onChange={(e) => setNewPatient((prev) => ({ ...prev, caregiver_phone_number: e.target.value }))}
                  className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 font-body text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary-fixed"
                />
              </div>
              <div>
                <label className="block font-body text-xs font-medium text-on-surface/70 mb-1.5">Conditions</label>
                <div className="grid grid-cols-2 gap-1 max-h-40 overflow-y-auto rounded-xl bg-surface-container-highest p-2.5">
                  {conditionsList.map((c) => (
                    <label key={c.id} className="flex items-center gap-2 cursor-pointer py-0.5 px-1 rounded-lg hover:bg-surface-container-low">
                      <input
                        type="checkbox"
                        checked={newPatient.conditions.includes(c.name)}
                        onChange={() => setNewPatient((prev) => ({
                          ...prev,
                          conditions: prev.conditions.includes(c.name)
                            ? prev.conditions.filter((x) => x !== c.name)
                            : [...prev.conditions, c.name],
                        }))}
                        className="accent-primary w-3.5 h-3.5"
                      />
                      <span className="font-body text-xs text-on-surface">{c.name}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="submit"
                  disabled={enrolling}
                  className="flex-1 bg-gradient-to-br from-primary to-primary-container text-white rounded-pill py-2.5 font-body text-sm font-semibold disabled:opacity-60"
                >
                  {enrolling ? "Enrolling…" : "Enrol"}
                </button>
                <button
                  type="button"
                  onClick={() => setShowEnrol(false)}
                  className="flex-1 bg-surface-container-highest rounded-pill py-2.5 font-body text-sm text-on-surface/70 hover:bg-outline-variant/30"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
