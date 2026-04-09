import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { getPatient, getPatientMedications, getNudgeCampaigns } from "../lib/api";

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
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [{ data: p }, { data: meds }, { data: camp }] = await Promise.all([
          getPatient(id),
          getPatientMedications(id),
          getNudgeCampaigns({ patient_id: id, page: 1, page_size: 20 }),
        ]);
        setPatient(p);
        setMedications(meds.items || meds);
        setCampaigns(camp.items || camp);
      } catch {
        // handled by interceptor
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id]);

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
        {patient.conditions?.length > 0 && (
          <div className="mt-5 flex flex-wrap gap-2">
            {patient.conditions.map((c) => (
              <span key={c} className="bg-surface-container-highest text-on-surface/60 font-body text-xs px-2.5 py-1 rounded-pill">
                {c}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Medications card */}
      <div className="bg-surface-container-lowest rounded-2xl shadow-ambient p-6 mb-4">
        <h2 className="font-display text-base font-bold text-on-surface mb-4">Medications</h2>
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
                    {m.dosage_instructions} · {m.supply_days_per_dispense}d supply
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
    </div>
  );
}

