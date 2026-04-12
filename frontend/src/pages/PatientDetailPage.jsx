import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import {
  getPatient, getPatientMedications, getNudgeCampaigns,
  updatePatient, getMedications, assignMedication,
  createDispensingRecord, getDispensingRecords, getConditions,
} from "../lib/api";

const CAMPAIGN_STATUS_CHIP = {
  resolved: "bg-tertiary-container text-on-tertiary-container",
  escalated: "bg-error-container text-on-error-container",
  no_reply: "bg-surface-container-highest text-on-surface/60",
  sent: "bg-secondary-container text-secondary",
  confirmed: "bg-tertiary-container text-on-tertiary-container",
};

const RISK_CHIP = {
  high: "bg-error-container text-on-error-container",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-tertiary-container text-on-tertiary-container",
};

export default function PatientDetailPage() {
  const { id } = useParams();
  const [patient, setPatient] = useState(null);
  const [medications, setMedications] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const [dispensingRecords, setDispensingRecords] = useState([]);
  const [conditionsList, setConditionsList] = useState([]); // from API
  const [loading, setLoading] = useState(true);

  // Conditions editing
  const [editingConditions, setEditingConditions] = useState(false);
  const [selectedConditions, setSelectedConditions] = useState([]);
  const [savingConditions, setSavingConditions] = useState(false);

  // Assign medication
  const [showAssignMed, setShowAssignMed] = useState(false);
  const [catalogMeds, setCatalogMeds] = useState([]);
  const [assignForm, setAssignForm] = useState({ medication_id: "", dosage: "", refill_interval_days: "", frequency: "once_daily", reminder_times: "" });
  const [assigningSaving, setAssigningSaving] = useState(false);

  // Dispensing
  const [showDispensing, setShowDispensing] = useState(false);
  const [dispensingForm, setDispensingForm] = useState({
    medication_id: "", dispensed_at: new Date().toISOString().slice(0, 16), days_supply: 30, quantity: "",
  });
  const [dispensingSaving, setDispensingSaving] = useState(false);

  const reload = async () => {
    try {
      const [patientRes, medsRes, campRes, dispRes, condsRes] = await Promise.allSettled([
        getPatient(id),
        getPatientMedications(id),
        getNudgeCampaigns({ patient_id: id, page: 1, page_size: 20 }),
        getDispensingRecords(id),
        getConditions(),
      ]);
      if (patientRes.status === "fulfilled") setPatient(patientRes.value.data);
      if (medsRes.status === "fulfilled") {
        const d = medsRes.value.data;
        setMedications(d.items || d);
      }
      if (campRes.status === "fulfilled") {
        const d = campRes.value.data;
        setCampaigns(d.items || d);
      }
      if (dispRes.status === "fulfilled") {
        const d = dispRes.value.data;
        setDispensingRecords(d.items || d);
      }
      if (condsRes.status === "fulfilled") {
        setConditionsList(condsRes.value.data);
      }
    } catch {
      // handled by interceptor
    }
  };

  useEffect(() => {
    const load = async () => {
      await reload();
      setLoading(false);
    };
    load();
  }, [id]);

  // --- Conditions handlers ---
  const startEditConditions = () => {
    setSelectedConditions([...(patient?.conditions || [])]);
    setEditingConditions(true);
  };
  const toggleCondition = (c) => {
    setSelectedConditions((prev) =>
      prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]
    );
  };
  const saveConditions = async () => {
    setSavingConditions(true);
    try {
      await updatePatient(id, { conditions: selectedConditions });
      setEditingConditions(false);
      await reload();
    } catch {
      // keep form open
    } finally {
      setSavingConditions(false);
    }
  };

  // --- Assign medication handler ---
  // Build set of suggested medication IDs from patient's conditions
  const suggestedMedIds = new Set();
  (patient?.conditions || []).forEach((cName) => {
    const cond = conditionsList.find((c) => c.name === cName);
    if (cond) cond.medications.forEach((m) => suggestedMedIds.add(m.id));
  });

  const openAssignMed = async () => {
    try {
      const { data } = await getMedications();
      // Sort: suggested first, then alphabetical
      const sorted = [...data].sort((a, b) => {
        const aS = suggestedMedIds.has(a.id) ? 0 : 1;
        const bS = suggestedMedIds.has(b.id) ? 0 : 1;
        if (aS !== bS) return aS - bS;
        return a.name.localeCompare(b.name);
      });
      setCatalogMeds(sorted);
    } catch { /* */ }
    setAssignForm({ medication_id: "", dosage: "", refill_interval_days: "", frequency: "once_daily", reminder_times: "" });
    setShowAssignMed(true);
  };
  const handleAssignMed = async (e) => {
    e.preventDefault();
    setAssigningSaving(true);
    try {
      await assignMedication(id, {
        medication_id: Number(assignForm.medication_id),
        dosage: assignForm.dosage || null,
        refill_interval_days: assignForm.refill_interval_days ? Number(assignForm.refill_interval_days) : null,
        frequency: assignForm.frequency,
        reminder_times: assignForm.reminder_times
          ? assignForm.reminder_times.split(",").map((t) => t.trim()).filter(Boolean)
          : null,
      });
      setShowAssignMed(false);
      await reload();
    } catch { /* */ } finally {
      setAssigningSaving(false);
    }
  };

  // --- Dispensing handler ---
  const openDispensing = async () => {
    try {
      const { data } = await getMedications();
      setCatalogMeds(data);
    } catch { /* */ }
    setDispensingForm({
      medication_id: "", dispensed_at: new Date().toISOString().slice(0, 16), days_supply: 30, quantity: "",
    });
    setShowDispensing(true);
  };
  const handleDispensing = async (e) => {
    e.preventDefault();
    setDispensingSaving(true);
    try {
      await createDispensingRecord({
        patient_id: Number(id),
        medication_id: Number(dispensingForm.medication_id),
        dispensed_at: new Date(dispensingForm.dispensed_at).toISOString(),
        days_supply: Number(dispensingForm.days_supply),
        quantity: dispensingForm.quantity ? Number(dispensingForm.quantity) : null,
        source: "manual",
      });
      setShowDispensing(false);
      await reload();
    } catch { /* */ } finally {
      setDispensingSaving(false);
    }
  };

  if (loading) return <div className="p-6 font-body text-on-surface/30">Loading…</div>;
  if (!patient) return <div className="p-6 font-body text-error">Patient not found</div>;

  return (
    <div className="p-6 max-w-4xl">
      {/* Back */}
      <Link to="/patients" className="font-body text-sm text-primary hover:underline mb-5 inline-block">
        ← Back to patients
      </Link>

      {/* Header card */}
      <div className="bg-surface-container-lowest rounded-2xl shadow-ambient p-6 mb-4">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="font-display text-2xl font-bold text-on-surface tracking-tight">{patient.full_name}</h1>
            <p className="font-body text-sm text-on-surface/50 mt-0.5">{patient.phone_number}</p>
          </div>
          <span className={`px-3 py-1 rounded-pill text-xs font-semibold ${RISK_CHIP[patient.risk_level] || "bg-surface-container-highest text-on-surface/60"}`}>
            {patient.risk_level} risk
          </span>
        </div>
        <div className="mt-6 grid grid-cols-4 gap-6 font-body text-sm">
          <div>
            <p className="text-xs text-primary-fixed-dim font-medium uppercase tracking-wide mb-1">Age</p>
            <p className="font-display font-semibold text-on-surface">{patient.age ?? "—"}</p>
          </div>
          <div>
            <p className="text-xs text-primary-fixed-dim font-medium uppercase tracking-wide mb-1">Language</p>
            <p className="font-display font-semibold text-on-surface uppercase">{patient.language_preference}</p>
          </div>
          <div>
            <p className="text-xs text-primary-fixed-dim font-medium uppercase tracking-wide mb-1">Onboarding</p>
            <p className="font-display font-semibold text-on-surface">{patient.onboarding_state}</p>
          </div>
          <div>
            <p className="text-xs text-primary-fixed-dim font-medium uppercase tracking-wide mb-1">Consent</p>
            <p className="font-display font-semibold text-on-surface">{patient.consent_obtained_at ? "✓" : "Pending"}</p>
          </div>
        </div>
        {/* Conditions */}
        <div className="mt-5">
          <div className="flex items-center gap-2 mb-2">
            <p className="text-xs text-primary-fixed-dim font-medium uppercase tracking-wide">Conditions</p>
            {!editingConditions && (
              <button
                onClick={startEditConditions}
                className="font-body text-xs text-primary hover:underline"
              >
                Edit
              </button>
            )}
          </div>
          {editingConditions ? (
            <div>
              <div className="grid grid-cols-2 gap-1.5 max-h-52 overflow-y-auto rounded-xl bg-surface-container-highest p-3 mb-3">
                {conditionsList.map((c) => (
                  <label key={c.id} className="flex items-center gap-2 cursor-pointer py-1 px-1.5 rounded-lg hover:bg-surface-container-low">
                    <input
                      type="checkbox"
                      checked={selectedConditions.includes(c.name)}
                      onChange={() => toggleCondition(c.name)}
                      className="accent-primary w-3.5 h-3.5"
                    />
                    <span className="font-body text-xs text-on-surface">{c.name}</span>
                  </label>
                ))}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={saveConditions}
                  disabled={savingConditions}
                  className="bg-primary text-white rounded-xl px-4 py-2 font-body text-sm font-semibold disabled:opacity-60"
                >
                  {savingConditions ? "…" : "Save"}
                </button>
                <button
                  onClick={() => setEditingConditions(false)}
                  className="bg-surface-container-highest rounded-xl px-4 py-2 font-body text-sm text-on-surface/70"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : patient.conditions?.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {patient.conditions.map((c) => (
                <span key={c} className="bg-surface-container-highest text-on-surface/60 font-body text-xs px-2.5 py-1 rounded-pill">
                  {c}
                </span>
              ))}
            </div>
          ) : (
            <p className="font-body text-sm text-on-surface/30">No conditions recorded</p>
          )}
        </div>
      </div>

      {/* Medications card */}
      <div className="bg-surface-container-lowest rounded-2xl shadow-ambient p-6 mb-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-display text-base font-bold text-on-surface">Medications</h2>
          <div className="flex gap-2">
            <button
              onClick={openDispensing}
              className="font-body text-xs text-primary border border-primary/30 rounded-pill px-3 py-1.5 hover:bg-primary/5"
            >
              Record Dispensing
            </button>
            <button
              onClick={openAssignMed}
              className="font-body text-xs bg-primary text-white rounded-pill px-3 py-1.5 hover:opacity-90"
            >
              + Assign Medication
            </button>
          </div>
        </div>
        {medications.length === 0 ? (
          <p className="font-body text-sm text-on-surface/30">No medications on record</p>
        ) : (
          <div className="space-y-6">
            {medications.map((m) => (
              <div key={m.id} className="bg-surface-container-low rounded-xl p-4 flex items-center justify-between">
                <div>
                  <p className="font-body text-sm font-semibold text-on-surface">
                    {m.medication?.brand_name || m.medication?.generic_name}
                  </p>
                  <p className="font-body text-xs text-on-surface/50 mt-0.5">
                    {m.dosage || "—"} · {m.frequency?.replace(/_/g, " ")} · refill {m.refill_interval_days ?? "—"}d
                  </p>
                </div>
                <div className="text-right font-body text-xs text-on-surface/50">
                  <p>Dispensed: {m.last_dispensed_at ? new Date(m.last_dispensed_at).toLocaleDateString() : "—"}</p>
                  <p className={`mt-1 font-semibold ${m.is_active ? "text-tertiary-container" : "text-on-surface/30"}`}>
                    {m.is_active ? "Active" : "Inactive"}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Dispensing Records */}
      <div className="bg-surface-container-lowest rounded-2xl shadow-ambient p-6 mb-4">
        <h2 className="font-display text-base font-bold text-on-surface mb-4">Dispensing Records</h2>
        {dispensingRecords.length === 0 ? (
          <p className="font-body text-sm text-on-surface/30">No dispensing records</p>
        ) : (
          <div className="space-y-3">
            {dispensingRecords.map((r) => (
              <div key={r.id} className="bg-surface-container-low rounded-xl p-4 flex items-center justify-between">
                <div>
                  <p className="font-body text-sm font-semibold text-on-surface">
                    Medication #{r.medication_id}
                  </p>
                  <p className="font-body text-xs text-on-surface/50 mt-0.5">
                    {r.days_supply}d supply{r.quantity ? ` · ${r.quantity} units` : ""} · {r.source}
                  </p>
                </div>
                <p className="font-body text-xs text-on-surface/50">
                  {new Date(r.dispensed_at).toLocaleDateString()}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Nudge campaign timeline */}
      <div className="bg-surface-container-lowest rounded-2xl shadow-ambient p-6">
        <h2 className="font-display text-base font-bold text-on-surface mb-4">Nudge Campaign Timeline</h2>
        {campaigns.length === 0 ? (
          <p className="font-body text-sm text-on-surface/30">No campaigns yet</p>
        ) : (
          <div className="space-y-4">
            {campaigns.map((c) => (
              <div key={c.id} className="flex items-start gap-4">
                <div className="mt-1.5 w-2 h-2 rounded-full bg-primary flex-shrink-0" />
                <div className="flex-1 bg-surface-container-low rounded-xl px-4 py-3">
                  <div className="flex items-center justify-between">
                    <span className="font-body text-sm text-on-surface font-medium">
                      {c.medication?.generic_name ?? `Campaign #${c.id}`}
                    </span>
                    <span className={`font-body text-xs px-2.5 py-0.5 rounded-pill font-semibold ${CAMPAIGN_STATUS_CHIP[c.status] || "bg-surface-container-highest text-on-surface/60"}`}>
                      {c.status}
                    </span>
                  </div>
                  <p className="font-body text-xs text-on-surface/40 mt-1">
                    Attempt {c.attempt_number} · {new Date(c.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Assign Medication Modal */}
      {showAssignMed && (
        <div className="fixed inset-0 bg-on-surface/40 flex items-center justify-center z-50">
          <div className="bg-surface-container-lowest/90 backdrop-blur-[20px] rounded-2xl shadow-float p-6 w-full max-w-md">
            <h2 className="font-display text-xl font-bold text-on-surface mb-5">Assign Medication</h2>
            <form onSubmit={handleAssignMed} className="space-y-4">
              <div>
                <label className="block font-body text-xs font-medium text-on-surface/70 mb-1.5">Medication</label>
                <select
                  required
                  value={assignForm.medication_id}
                  onChange={(e) => setAssignForm((p) => ({ ...p, medication_id: e.target.value }))}
                  className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 font-body text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary-fixed"
                >
                  <option value="">Select…</option>
                  {catalogMeds.map((m) => (
                    <option key={m.id} value={m.id}>
                      {suggestedMedIds.has(m.id) ? "★ " : ""}{m.name} ({m.generic_name})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block font-body text-xs font-medium text-on-surface/70 mb-1.5">Dosage Instructions</label>
                <input
                  type="text"
                  placeholder="e.g. 10mg once daily"
                  value={assignForm.dosage}
                  onChange={(e) => setAssignForm((p) => ({ ...p, dosage: e.target.value }))}
                  className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 font-body text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary-fixed"
                />
              </div>
              <div>
                <label className="block font-body text-xs font-medium text-on-surface/70 mb-1.5">Refill Interval (days)</label>
                <input
                  type="number"
                  min={1}
                  placeholder="30"
                  value={assignForm.refill_interval_days}
                  onChange={(e) => setAssignForm((p) => ({ ...p, refill_interval_days: e.target.value }))}
                  className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 font-body text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary-fixed"
                />
              </div>
              <div>
                <label className="block font-body text-xs font-medium text-on-surface/70 mb-1.5">Frequency</label>
                <select
                  value={assignForm.frequency}
                  onChange={(e) => setAssignForm((p) => ({ ...p, frequency: e.target.value }))}
                  className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 font-body text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary-fixed"
                >
                  <option value="once_daily">Once daily</option>
                  <option value="twice_daily">Twice daily</option>
                  <option value="three_times_daily">Three times daily</option>
                  <option value="every_other_day">Every other day</option>
                  <option value="weekly">Weekly</option>
                  <option value="as_needed">As needed</option>
                </select>
              </div>
              <div>
                <label className="block font-body text-xs font-medium text-on-surface/70 mb-1.5">
                  Reminder Times (SGT) — comma-separated
                </label>
                <input
                  type="text"
                  placeholder={assignForm.frequency === "twice_daily" ? "08:00, 20:00" : "08:00"}
                  value={assignForm.reminder_times}
                  onChange={(e) => setAssignForm((p) => ({ ...p, reminder_times: e.target.value }))}
                  className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 font-body text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary-fixed"
                />
                <p className="font-body text-xs text-on-surface/40 mt-1">Leave blank to use frequency defaults</p>
              </div>
              <div className="flex gap-3 pt-2">
                <button type="submit" disabled={assigningSaving} className="flex-1 bg-gradient-to-br from-primary to-primary-container text-white rounded-pill py-2.5 font-body text-sm font-semibold disabled:opacity-60">
                  {assigningSaving ? "Assigning…" : "Assign"}
                </button>
                <button type="button" onClick={() => setShowAssignMed(false)} className="flex-1 bg-surface-container-highest rounded-pill py-2.5 font-body text-sm text-on-surface/70 hover:bg-outline-variant/30">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Record Dispensing Modal */}
      {showDispensing && (
        <div className="fixed inset-0 bg-on-surface/40 flex items-center justify-center z-50">
          <div className="bg-surface-container-lowest/90 backdrop-blur-[20px] rounded-2xl shadow-float p-6 w-full max-w-md">
            <h2 className="font-display text-xl font-bold text-on-surface mb-5">Record Dispensing</h2>
            <form onSubmit={handleDispensing} className="space-y-4">
              <div>
                <label className="block font-body text-xs font-medium text-on-surface/70 mb-1.5">Medication</label>
                <select
                  required
                  value={dispensingForm.medication_id}
                  onChange={(e) => setDispensingForm((p) => ({ ...p, medication_id: e.target.value }))}
                  className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 font-body text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary-fixed"
                >
                  <option value="">Select…</option>
                  {catalogMeds.map((m) => (
                    <option key={m.id} value={m.id}>{m.name} ({m.generic_name})</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block font-body text-xs font-medium text-on-surface/70 mb-1.5">Dispensed At</label>
                <input
                  type="datetime-local"
                  required
                  value={dispensingForm.dispensed_at}
                  onChange={(e) => setDispensingForm((p) => ({ ...p, dispensed_at: e.target.value }))}
                  className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 font-body text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary-fixed"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-body text-xs font-medium text-on-surface/70 mb-1.5">Days Supply</label>
                  <input
                    type="number"
                    required
                    min={1}
                    value={dispensingForm.days_supply}
                    onChange={(e) => setDispensingForm((p) => ({ ...p, days_supply: e.target.value }))}
                    className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 font-body text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary-fixed"
                  />
                </div>
                <div>
                  <label className="block font-body text-xs font-medium text-on-surface/70 mb-1.5">Quantity</label>
                  <input
                    type="number"
                    min={1}
                    placeholder="Optional"
                    value={dispensingForm.quantity}
                    onChange={(e) => setDispensingForm((p) => ({ ...p, quantity: e.target.value }))}
                    className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 font-body text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary-fixed"
                  />
                </div>
              </div>
              <div className="flex gap-3 pt-2">
                <button type="submit" disabled={dispensingSaving} className="flex-1 bg-gradient-to-br from-primary to-primary-container text-white rounded-pill py-2.5 font-body text-sm font-semibold disabled:opacity-60">
                  {dispensingSaving ? "Saving…" : "Record Dispensing"}
                </button>
                <button type="button" onClick={() => setShowDispensing(false)} className="flex-1 bg-surface-container-highest rounded-pill py-2.5 font-body text-sm text-on-surface/70 hover:bg-outline-variant/30">
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

