import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import {
  getPatient, getPatientMedications, getNudgeCampaigns,
  updatePatient, getMedications, assignMedication,
  createDispensingRecord, getDispensingRecords, getConditions,
  regenerateInviteLink, generateCaregiverInviteLink, getDoseHistory,
  triggerPatientNudge, triggerPatientReminder,
} from "../lib/api";

const RISK_CHIP = {
  high: "bg-error-container text-on-error-container",
  normal: "bg-secondary-container text-secondary",
  low: "bg-tertiary-container text-on-tertiary-container",
};

const CAMPAIGN_STATUS_CHIP = {
  resolved: "bg-tertiary-container text-on-tertiary-container",
  escalated: "bg-error-container text-on-error-container",
  sent: "bg-secondary-container text-secondary",
  responded: "bg-surface-container-highest text-on-surface/60",
  pending: "bg-surface-container-highest text-on-surface/60",
  failed: "bg-error-container text-on-error-container",
};

export default function PatientDetailPage() {
  const { id } = useParams();
  const [patient, setPatient] = useState(null);
  const [medications, setMedications] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const [dispensingRecords, setDispensingRecords] = useState([]);
  const [doseHistory, setDoseHistory] = useState([]);
  const [conditionsList, setConditionsList] = useState([]);
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

  // Caregiver editing
  const [editingCaregiver, setEditingCaregiver] = useState(false);
  const [caregiverForm, setCaregiverForm] = useState({ caregiver_name: "", caregiver_phone_number: "" });
  const [savingCaregiver, setSavingCaregiver] = useState(false);
  const [caregiverInviteLink, setCaregiverInviteLink] = useState(null);
  const [caregiverLinkLoading, setCaregiverLinkLoading] = useState(false);
  const [caregiverLinkCopied, setCaregiverLinkCopied] = useState(false);

  // QR code invite
  const [qrCode, setQrCode] = useState(null);
  const [inviteLink, setInviteLink] = useState(null);
  const [qrLoading, setQrLoading] = useState(false);

  // Trigger buttons
  const [triggeringNudge, setTriggeringNudge] = useState(false);
  const [triggeringReminder, setTriggeringReminder] = useState(false);
  const [triggerResult, setTriggerResult] = useState(null);

  const reload = async () => {
    try {
      const [patientRes, medsRes, campRes, dispRes, condsRes, doseRes] = await Promise.allSettled([
        getPatient(id),
        getPatientMedications(id),
        getNudgeCampaigns({ patient_id: id, page: 1, page_size: 20 }),
        getDispensingRecords(id),
        getConditions(),
        getDoseHistory(id, { days: 30 }),
      ]);
      if (patientRes.status === "fulfilled") setPatient(patientRes.value.data);
      if (medsRes.status === "fulfilled") { const d = medsRes.value.data; setMedications(d.items || d); }
      if (campRes.status === "fulfilled") { const d = campRes.value.data; setCampaigns(d.items || d); }
      if (dispRes.status === "fulfilled") { const d = dispRes.value.data; setDispensingRecords(d.items || d); }
      if (condsRes.status === "fulfilled") setConditionsList(condsRes.value.data);
      if (doseRes.status === "fulfilled") setDoseHistory(doseRes.value.data);
    } catch { /* interceptor */ }
  };

  useEffect(() => { const load = async () => { await reload(); setLoading(false); }; load(); }, [id]);

  // --- Handlers (unchanged logic) ---
  const startEditConditions = () => { setSelectedConditions([...(patient?.conditions || [])]); setEditingConditions(true); };
  const toggleCondition = (c) => setSelectedConditions((prev) => prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]);
  const saveConditions = async () => { setSavingConditions(true); try { await updatePatient(id, { conditions: selectedConditions }); setEditingConditions(false); await reload(); } catch { /* no-op */ } finally { setSavingConditions(false); } };

  const startEditCaregiver = () => { setCaregiverForm({ caregiver_name: patient?.caregiver_name || "", caregiver_phone_number: patient?.caregiver_phone_number || "" }); setEditingCaregiver(true); };
  const saveCaregiver = async () => { setSavingCaregiver(true); try { await updatePatient(id, caregiverForm); setEditingCaregiver(false); await reload(); } catch { /* no-op */ } finally { setSavingCaregiver(false); } };
  const handleGenerateCaregiverLink = async () => { setCaregiverLinkLoading(true); try { const res = await generateCaregiverInviteLink(id); setCaregiverInviteLink(res.data.invite_link); } catch { /* no-op */ } finally { setCaregiverLinkLoading(false); } };
  const handleCopyCaregiverLink = () => { if (!caregiverInviteLink) return; navigator.clipboard.writeText(caregiverInviteLink); setCaregiverLinkCopied(true); setTimeout(() => setCaregiverLinkCopied(false), 2000); };
  const handleRegenerateQR = async () => { setQrLoading(true); try { const res = await regenerateInviteLink(id); setQrCode(res.data.onboarding_qr_code); setInviteLink(res.data.invite_link); } catch { /* no-op */ } finally { setQrLoading(false); } };

  const handleTriggerNudge = async () => {
    setTriggeringNudge(true); setTriggerResult(null);
    try { const { data } = await triggerPatientNudge(id); setTriggerResult(`Nudge: ${data.campaigns_fired} fired, ${data.campaigns_failed} failed`); await reload(); }
    catch { setTriggerResult("Failed to trigger nudge"); }
    finally { setTriggeringNudge(false); setTimeout(() => setTriggerResult(null), 5000); }
  };
  const handleTriggerReminder = async () => {
    setTriggeringReminder(true); setTriggerResult(null);
    try { const { data } = await triggerPatientReminder(id); setTriggerResult(`Reminder: ${data.reminders_sent} sent`); await reload(); }
    catch { setTriggerResult("Failed to trigger reminder"); }
    finally { setTriggeringReminder(false); setTimeout(() => setTriggerResult(null), 5000); }
  };

  const suggestedMedIds = new Set();
  (patient?.conditions || []).forEach((cName) => { const cond = conditionsList.find((c) => c.name === cName); if (cond) cond.medications.forEach((m) => suggestedMedIds.add(m.id)); });

  const openAssignMed = async () => { try { const { data } = await getMedications(); setCatalogMeds([...data].sort((a, b) => { const aS = suggestedMedIds.has(a.id) ? 0 : 1; const bS = suggestedMedIds.has(b.id) ? 0 : 1; return aS !== bS ? aS - bS : a.name.localeCompare(b.name); })); } catch { /* no-op */ } setAssignForm({ medication_id: "", dosage: "", refill_interval_days: "", frequency: "once_daily", reminder_times: "" }); setShowAssignMed(true); };
  const handleAssignMed = async (e) => { e.preventDefault(); setAssigningSaving(true); try { await assignMedication(id, { medication_id: Number(assignForm.medication_id), dosage: assignForm.dosage || null, refill_interval_days: assignForm.refill_interval_days ? Number(assignForm.refill_interval_days) : null, frequency: assignForm.frequency, reminder_times: assignForm.reminder_times ? assignForm.reminder_times.split(",").map((t) => t.trim()).filter(Boolean) : null }); setShowAssignMed(false); await reload(); } catch { /* no-op */ } finally { setAssigningSaving(false); } };

  const openDispensing = async () => { try { const { data } = await getMedications(); setCatalogMeds(data); } catch { /* no-op */ } setDispensingForm({ medication_id: "", dispensed_at: new Date().toISOString().slice(0, 16), days_supply: 30, quantity: "" }); setShowDispensing(true); };
  const handleDispensing = async (e) => { e.preventDefault(); setDispensingSaving(true); try { await createDispensingRecord({ patient_id: Number(id), medication_id: Number(dispensingForm.medication_id), dispensed_at: new Date(dispensingForm.dispensed_at).toISOString(), days_supply: Number(dispensingForm.days_supply), quantity: dispensingForm.quantity ? Number(dispensingForm.quantity) : null, source: "manual" }); setShowDispensing(false); await reload(); } catch { /* no-op */ } finally { setDispensingSaving(false); } };

  if (loading) return <div className="p-8 font-body text-on-surface/30">Loading...</div>;
  if (!patient) return <div className="p-8 font-body text-error">Patient not found</div>;

  // Computed values
  const takenCount = doseHistory.filter((d) => d.status === "taken").length;
  const totalDoses = doseHistory.length;
  const adherenceRate = totalDoses > 0 ? Math.round(takenCount / totalDoses * 100) : 100;
  const missedCount = doseHistory.filter((d) => d.status === "missed").length;
  const medNames = medications.map((m) => m.medication?.name || m.medication?.generic_name).filter(Boolean).join(", ");

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Back */}
      <Link to="/patients" className="font-body text-sm text-primary hover:underline inline-block">
        &larr; Back to patients
      </Link>

      {/* Patient Profile Header (Stitch design) */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-6 border-b border-outline-variant/15">
        <div className="flex items-start gap-6">
          <div className="w-24 h-24 rounded-2xl bg-primary-container flex items-center justify-center text-white text-3xl font-display font-bold shadow-lg shadow-on-surface/5">
            {patient.full_name.split(" ").map((n) => n[0]).join("").slice(0, 2)}
          </div>
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h2 className="font-display text-2xl font-bold tracking-tight text-on-surface">{patient.full_name}</h2>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${patient.is_active ? "bg-tertiary-container/10 text-tertiary-container" : "bg-error-container text-on-error-container"}`}>
                {patient.is_active ? "Active" : "Inactive"}
              </span>
            </div>
            <p className="text-sm text-outline font-medium mb-4">
              {patient.phone_number} {patient.age ? `| ${patient.age} Years Old` : ""} | {patient.language_preference.toUpperCase()} | {patient.onboarding_state}
            </p>
            <div className="flex flex-wrap gap-3">
              {patient.conditions?.length > 0 && (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-surface-container-low rounded-lg text-xs font-medium text-on-surface/70">
                  {patient.conditions.join(", ")}
                </div>
              )}
              {medNames && (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-surface-container-low rounded-lg text-xs font-medium text-on-surface/70">
                  {medNames}
                </div>
              )}
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold ${
                patient.nudge_delivery_mode === "voice" || patient.nudge_delivery_mode === "both" ? "bg-secondary-container/20 text-secondary" : "bg-surface-container-low text-on-surface/50"
              }`}>
                {patient.nudge_delivery_mode === "text" ? "Text nudges" : patient.nudge_delivery_mode === "voice" ? "Voice nudges" : patient.nudge_delivery_mode === "both" ? "Text + Voice" : "Text nudges"}
              </div>
            </div>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button onClick={handleTriggerNudge} disabled={triggeringNudge} className="px-4 py-2 rounded-full border border-primary/30 text-primary text-xs font-medium hover:bg-primary/5 disabled:opacity-60">
            {triggeringNudge ? "Triggering..." : "Trigger Nudge"}
          </button>
          <button onClick={handleTriggerReminder} disabled={triggeringReminder} className="px-4 py-2 rounded-full border border-primary/30 text-primary text-xs font-medium hover:bg-primary/5 disabled:opacity-60">
            {triggeringReminder ? "Triggering..." : "Trigger Reminder"}
          </button>
          <button onClick={openDispensing} className="px-4 py-2 rounded-full border border-outline text-on-surface text-xs font-medium hover:bg-surface-container transition-colors">
            Record Dispensing
          </button>
          <button onClick={openAssignMed} className="px-4 py-2 rounded-full bg-gradient-to-br from-primary to-primary-container text-white text-xs font-bold shadow-md shadow-primary/20">
            + Assign Medication
          </button>
        </div>
      </div>

      {triggerResult && (
        <div className="px-4 py-2.5 bg-tertiary-container/20 border border-tertiary-container/30 rounded-xl font-body text-sm text-on-surface/70">{triggerResult}</div>
      )}

      {/* Telegram QR / Caregiver Invite */}
      {(!patient.telegram_chat_id || patient.caregiver_name) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {!patient.telegram_chat_id && (
            <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm">
              <h3 className="font-display text-sm font-bold text-on-surface mb-4">Telegram Onboarding QR</h3>
              {qrCode ? (
                <div className="flex flex-col items-start gap-3">
                  <img src={`data:image/png;base64,${qrCode}`} alt="QR" className="w-40 h-40 rounded-xl border border-outline-variant" />
                  <div className="flex gap-2 flex-wrap">
                    <button onClick={() => { const a = document.createElement("a"); a.href = `data:image/png;base64,${qrCode}`; a.download = `invite-qr-patient-${id}.png`; a.click(); }} className="text-xs bg-primary text-white px-3 py-1.5 rounded-full font-bold hover:opacity-90">Download QR</button>
                    <button onClick={() => navigator.clipboard.writeText(inviteLink)} className="text-xs bg-surface-container text-on-surface border border-outline-variant px-3 py-1.5 rounded-full hover:bg-surface-container-high">Copy Link</button>
                    <button onClick={handleRegenerateQR} disabled={qrLoading} className="text-xs text-primary hover:underline px-2 py-1.5">{qrLoading ? "..." : "Regenerate"}</button>
                  </div>
                </div>
              ) : (
                <button onClick={handleRegenerateQR} disabled={qrLoading} className="text-sm bg-primary text-white px-4 py-2 rounded-full hover:opacity-90 disabled:opacity-50">
                  {qrLoading ? "Generating..." : "Generate Invite QR"}
                </button>
              )}
            </div>
          )}
          {patient.caregiver_name && (
            <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-display text-sm font-bold text-on-surface">Caregiver</h3>
                <button onClick={startEditCaregiver} className="text-xs text-primary hover:underline">Edit</button>
              </div>
              {editingCaregiver ? (
                <div className="space-y-2">
                  <input type="text" placeholder="Name" value={caregiverForm.caregiver_name} onChange={(e) => setCaregiverForm((f) => ({ ...f, caregiver_name: e.target.value }))} className="w-full bg-surface-container-highest rounded-xl px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary-fixed" />
                  <input type="text" placeholder="Phone (E.164)" value={caregiverForm.caregiver_phone_number} onChange={(e) => setCaregiverForm((f) => ({ ...f, caregiver_phone_number: e.target.value }))} className="w-full bg-surface-container-highest rounded-xl px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary-fixed" />
                  <div className="flex gap-2"><button onClick={saveCaregiver} disabled={savingCaregiver} className="bg-primary text-white rounded-full px-4 py-1.5 text-xs font-bold">{savingCaregiver ? "..." : "Save"}</button><button onClick={() => setEditingCaregiver(false)} className="text-xs text-on-surface/50">Cancel</button></div>
                </div>
              ) : (
                <div>
                  <p className="text-sm font-medium text-on-surface">{patient.caregiver_name} <span className="text-on-surface/50 text-xs">{patient.caregiver_phone_number}</span></p>
                  <p className="text-xs mt-1">{patient.caregiver_telegram_id ? <span className="text-tertiary-container">Telegram linked</span> : <span className="text-on-surface/40">Telegram not linked</span>}</p>
                  {!patient.caregiver_telegram_id && (
                    <div className="mt-3 space-y-1.5">
                      <button onClick={handleGenerateCaregiverLink} disabled={caregiverLinkLoading} className="text-xs text-primary border border-primary/30 rounded-full px-3 py-1.5 hover:bg-primary/5">{caregiverLinkLoading ? "..." : "Generate Invite Link"}</button>
                      {caregiverInviteLink && (
                        <div className="flex items-center gap-2 bg-surface-container-highest rounded-xl px-3 py-2">
                          <span className="text-xs text-on-surface/70 truncate flex-1">{caregiverInviteLink}</span>
                          <button onClick={handleCopyCaregiverLink} className="text-xs text-primary font-semibold">{caregiverLinkCopied ? "Copied!" : "Copy"}</button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Bento Grid: Adherence Score + Conditions/Risk */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        {/* Adherence Risk Score Card */}
        <div className="md:col-span-4 bg-surface-container-lowest rounded-xl p-6 shadow-sm flex flex-col items-center justify-center text-center relative overflow-hidden">
          <h3 className="text-sm font-body text-outline mb-6">Dose Adherence (30 Days)</h3>
          <div className="relative mb-6">
            <svg className="w-40 h-40 transform -rotate-90">
              <circle className="text-surface-container-high" cx="80" cy="80" fill="transparent" r="70" stroke="currentColor" strokeWidth="8" />
              <circle
                className={adherenceRate >= 80 ? "text-tertiary-container" : adherenceRate >= 50 ? "text-secondary" : "text-error"}
                cx="80" cy="80" fill="transparent" r="70" stroke="currentColor"
                strokeWidth="12" strokeLinecap="round"
                strokeDasharray="440" strokeDashoffset={440 - (440 * adherenceRate / 100)}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className={`font-display text-5xl font-extrabold ${adherenceRate >= 80 ? "text-tertiary-container" : adherenceRate >= 50 ? "text-secondary" : "text-error"}`}>{adherenceRate}</span>
              <span className="text-[10px] text-outline uppercase tracking-widest font-bold">
                {adherenceRate >= 80 ? "On Track" : adherenceRate >= 50 ? "Moderate" : "High Risk"}
              </span>
            </div>
          </div>
          <p className="text-xs text-on-surface/50">{takenCount} taken / {missedCount} missed of {totalDoses} doses</p>
        </div>

        {/* Conditions + Caregiver info */}
        <div className="md:col-span-8 space-y-6">
          {/* Conditions card */}
          <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-display text-sm font-bold text-on-surface">Conditions</h3>
              {!editingConditions && <button onClick={startEditConditions} className="text-xs text-primary hover:underline">Edit</button>}
            </div>
            {editingConditions ? (
              <div>
                <div className="grid grid-cols-3 gap-1.5 max-h-40 overflow-y-auto rounded-xl bg-surface-container-highest p-3 mb-3">
                  {conditionsList.map((c) => (
                    <label key={c.id} className="flex items-center gap-2 cursor-pointer py-1 px-1.5 rounded-lg hover:bg-surface-container-low">
                      <input type="checkbox" checked={selectedConditions.includes(c.name)} onChange={() => toggleCondition(c.name)} className="accent-primary w-3.5 h-3.5" />
                      <span className="text-xs text-on-surface">{c.name}</span>
                    </label>
                  ))}
                </div>
                <div className="flex gap-2">
                  <button onClick={saveConditions} disabled={savingConditions} className="bg-primary text-white rounded-full px-4 py-1.5 text-xs font-bold">{savingConditions ? "..." : "Save"}</button>
                  <button onClick={() => setEditingConditions(false)} className="text-xs text-on-surface/50">Cancel</button>
                </div>
              </div>
            ) : patient.conditions?.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {patient.conditions.map((c) => <span key={c} className="bg-surface-container-highest text-on-surface/60 text-xs px-2.5 py-1 rounded-full">{c}</span>)}
              </div>
            ) : (
              <p className="text-sm text-on-surface/30">No conditions recorded</p>
            )}
          </div>

          {/* Voice + risk level */}
          <div className="grid grid-cols-2 gap-6">
            <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm">
              <h3 className="font-display text-sm font-bold text-on-surface mb-2">Risk Level</h3>
              <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${RISK_CHIP[patient.risk_level] || RISK_CHIP.normal}`}>{patient.risk_level}</span>
            </div>
            <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm">
              <h3 className="font-display text-sm font-bold text-on-surface mb-2">Voice Nudge</h3>
              <p className="text-xs text-on-surface/60">{patient.nudge_delivery_mode || "text"} {patient.selected_voice_id ? `(${patient.selected_voice_id.slice(0, 8)}...)` : "(default)"}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Content: Refill Timeline + Behavior Signals */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Pharmacy Refill Timeline */}
        <div className="lg:col-span-7 bg-surface-container-lowest rounded-xl p-8 shadow-sm">
          <div className="flex items-center justify-between mb-8">
            <h3 className="font-display text-lg font-bold text-on-surface">Pharmacy Refill Timeline</h3>
            <div className="flex gap-3">
              <span className="flex items-center gap-1.5 text-[10px] font-bold text-outline uppercase tracking-wider"><span className="w-2 h-2 rounded-full bg-tertiary-container" /> On Time</span>
              <span className="flex items-center gap-1.5 text-[10px] font-bold text-outline uppercase tracking-wider"><span className="w-2 h-2 rounded-full bg-error" /> Late</span>
            </div>
          </div>
          {dispensingRecords.length === 0 ? (
            <p className="text-sm text-on-surface/30 text-center py-8">No dispensing records</p>
          ) : (
            <div className="relative space-y-10 before:content-[''] before:absolute before:left-[11px] before:top-2 before:bottom-2 before:w-0.5 before:bg-surface-container-highest">
              {dispensingRecords.slice(0, 8).map((r) => {
                const med = medications.find((m) => m.medication_id === r.medication_id);
                const medName = med?.medication?.name || `Medication #${r.medication_id}`;
                return (
                  <div key={r.id} className="relative pl-10">
                    <div className={`absolute left-0 top-1 w-6 h-6 rounded-full ring-4 ring-white flex items-center justify-center text-white text-[10px] font-bold ${r.source === "manual" ? "bg-tertiary-container" : "bg-secondary"}`}>
                      {r.source === "manual" ? "M" : "A"}
                    </div>
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div>
                        <h4 className="text-sm font-bold text-on-surface">{medName}</h4>
                        <p className="text-xs text-outline mt-0.5">{r.days_supply}d supply{r.quantity ? ` | ${r.quantity} units` : ""} | {r.source}</p>
                      </div>
                      <div className="text-right">
                        <span className="text-[10px] text-outline">{new Date(r.dispensed_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right sidebar: Dose History + Campaigns */}
        <div className="lg:col-span-5 space-y-6">
          {/* Dose History */}
          <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm">
            <h3 className="font-display text-md font-bold text-on-surface mb-4">Dose History (30 Days)</h3>
            {doseHistory.length === 0 ? (
              <p className="text-sm text-on-surface/30 text-center py-4">No dose records yet</p>
            ) : (
              <div className="space-y-3 max-h-64 overflow-y-auto">
                {doseHistory.slice(0, 20).map((d) => (
                  <div key={d.id} className="flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full flex-shrink-0 ${d.status === "taken" ? "bg-tertiary-container" : "bg-error"}`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-on-surface truncate">{d.medication_name}</p>
                      <p className="text-[10px] text-outline">{new Date(d.logged_at).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</p>
                    </div>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${d.status === "taken" ? "bg-tertiary-container/10 text-tertiary-container" : "bg-error-container text-on-error-container"}`}>{d.status}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Nudge Campaigns */}
          <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm">
            <h3 className="font-display text-md font-bold text-on-surface mb-4">Nudge Campaigns</h3>
            {campaigns.length === 0 ? (
              <p className="text-sm text-on-surface/30 text-center py-4">No campaigns yet</p>
            ) : (
              <div className="space-y-3 max-h-64 overflow-y-auto">
                {campaigns.map((c) => (
                  <div key={c.id} className="p-3 bg-surface-container-low rounded-xl">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-bold text-on-surface">Campaign #{c.id}</span>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${CAMPAIGN_STATUS_CHIP[c.status] || "bg-surface-container-highest text-on-surface/60"}`}>{c.status}</span>
                    </div>
                    <p className="text-[10px] text-outline">Attempt {c.attempt_number} | {c.days_overdue}d overdue | {new Date(c.created_at).toLocaleDateString()}</p>
                    {c.response_type && <p className="text-[10px] text-primary font-medium mt-1">Response: {c.response_type}</p>}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Medications card */}
      <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-display text-lg font-bold text-on-surface">Active Medications</h3>
          <div className="flex gap-2">
            <button onClick={openDispensing} className="text-xs text-primary border border-primary/30 rounded-full px-3 py-1.5 hover:bg-primary/5">Record Dispensing</button>
            <button onClick={openAssignMed} className="text-xs bg-primary text-white rounded-full px-3 py-1.5 hover:opacity-90">+ Assign</button>
          </div>
        </div>
        {medications.length === 0 ? (
          <p className="text-sm text-on-surface/30">No medications on record</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {medications.map((m) => (
              <div key={m.id} className="bg-surface-container-low rounded-xl p-4">
                <p className="text-sm font-bold text-on-surface">{m.medication?.name || m.medication?.generic_name}</p>
                <p className="text-xs text-on-surface/50 mt-1">{m.dosage || "No dosage"} | {m.frequency?.replace(/_/g, " ")} | refill {m.refill_interval_days ?? "30"}d</p>
                <p className={`text-[10px] mt-2 font-bold ${m.is_active ? "text-tertiary-container" : "text-on-surface/30"}`}>{m.is_active ? "Active" : "Inactive"}</p>
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
                <label className="block text-xs font-medium text-on-surface/70 mb-1.5">Medication</label>
                <select required value={assignForm.medication_id} onChange={(e) => setAssignForm((p) => ({ ...p, medication_id: e.target.value }))} className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary-fixed">
                  <option value="">Select...</option>
                  {catalogMeds.map((m) => <option key={m.id} value={m.id}>{suggestedMedIds.has(m.id) ? "* " : ""}{m.name} ({m.generic_name})</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-on-surface/70 mb-1.5">Dosage</label>
                <input type="text" placeholder="e.g. 10mg" value={assignForm.dosage} onChange={(e) => setAssignForm((p) => ({ ...p, dosage: e.target.value }))} className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary-fixed" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-on-surface/70 mb-1.5">Refill (days)</label>
                  <input type="number" min={1} placeholder="30" value={assignForm.refill_interval_days} onChange={(e) => setAssignForm((p) => ({ ...p, refill_interval_days: e.target.value }))} className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary-fixed" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-on-surface/70 mb-1.5">Frequency</label>
                  <select value={assignForm.frequency} onChange={(e) => setAssignForm((p) => ({ ...p, frequency: e.target.value }))} className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary-fixed">
                    <option value="once_daily">Once daily</option>
                    <option value="twice_daily">Twice daily</option>
                    <option value="three_times_daily">3x daily</option>
                    <option value="every_other_day">Every other day</option>
                    <option value="weekly">Weekly</option>
                    <option value="as_needed">As needed</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-on-surface/70 mb-1.5">Reminder Times (SGT, comma-separated)</label>
                <input type="text" placeholder="08:00, 20:00" value={assignForm.reminder_times} onChange={(e) => setAssignForm((p) => ({ ...p, reminder_times: e.target.value }))} className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary-fixed" />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="submit" disabled={assigningSaving} className="flex-1 bg-gradient-to-br from-primary to-primary-container text-white rounded-full py-2.5 text-sm font-bold disabled:opacity-60">{assigningSaving ? "Assigning..." : "Assign"}</button>
                <button type="button" onClick={() => setShowAssignMed(false)} className="flex-1 bg-surface-container-highest rounded-full py-2.5 text-sm text-on-surface/70">Cancel</button>
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
                <label className="block text-xs font-medium text-on-surface/70 mb-1.5">Medication</label>
                <select required value={dispensingForm.medication_id} onChange={(e) => setDispensingForm((p) => ({ ...p, medication_id: e.target.value }))} className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary-fixed">
                  <option value="">Select...</option>
                  {catalogMeds.map((m) => <option key={m.id} value={m.id}>{m.name} ({m.generic_name})</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-on-surface/70 mb-1.5">Dispensed At</label>
                <input type="datetime-local" required value={dispensingForm.dispensed_at} onChange={(e) => setDispensingForm((p) => ({ ...p, dispensed_at: e.target.value }))} className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary-fixed" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-on-surface/70 mb-1.5">Days Supply</label>
                  <input type="number" required min={1} value={dispensingForm.days_supply} onChange={(e) => setDispensingForm((p) => ({ ...p, days_supply: e.target.value }))} className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary-fixed" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-on-surface/70 mb-1.5">Quantity</label>
                  <input type="number" min={1} placeholder="Optional" value={dispensingForm.quantity} onChange={(e) => setDispensingForm((p) => ({ ...p, quantity: e.target.value }))} className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary-fixed" />
                </div>
              </div>
              <div className="flex gap-3 pt-2">
                <button type="submit" disabled={dispensingSaving} className="flex-1 bg-gradient-to-br from-primary to-primary-container text-white rounded-full py-2.5 text-sm font-bold disabled:opacity-60">{dispensingSaving ? "Saving..." : "Record"}</button>
                <button type="button" onClick={() => setShowDispensing(false)} className="flex-1 bg-surface-container-highest rounded-full py-2.5 text-sm text-on-surface/70">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
