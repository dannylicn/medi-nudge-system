import { useState, useEffect } from "react";
import { getMedications, createMedication } from "../lib/api";

export default function MedicationsPage() {
  const [medications, setMedications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    name: "",
    generic_name: "",
    category: "",
    default_refill_days: 30,
  });

  const fetchMedications = async () => {
    setLoading(true);
    try {
      const { data } = await getMedications();
      setMedications(data);
    } catch {
      // handled by interceptor
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMedications();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await createMedication({
        ...form,
        category: form.category || null,
        default_refill_days: Number(form.default_refill_days),
      });
      setShowForm(false);
      setForm({ name: "", generic_name: "", category: "", default_refill_days: 30 });
      fetchMedications();
    } catch {
      // leave form open
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display text-2xl font-bold text-on-surface tracking-tight">Medication Catalog</h1>
          <p className="font-body text-sm text-on-surface/50">{medications.length} medications</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="bg-gradient-to-br from-primary to-primary-container text-white font-body text-sm font-semibold px-5 py-2.5 rounded-pill transition-opacity hover:opacity-90"
        >
          + Add Medication
        </button>
      </div>

      {/* Medications table */}
      <div className="bg-surface-container-low rounded-2xl overflow-hidden shadow-ambient">
        <table className="w-full font-body text-sm">
          <thead className="bg-surface-container-lowest text-on-surface/40 text-xs uppercase tracking-widest">
            <tr>
              <th className="px-5 py-3.5 text-left">Brand Name</th>
              <th className="px-5 py-3.5 text-left">Generic Name</th>
              <th className="px-5 py-3.5 text-left">Category</th>
              <th className="px-5 py-3.5 text-left">Refill Days</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={4} className="px-5 py-10 text-center text-on-surface/30">Loading…</td>
              </tr>
            ) : medications.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-5 py-10 text-center text-on-surface/30">No medications in catalog</td>
              </tr>
            ) : (
              medications.map((m, i) => (
                <tr
                  key={m.id}
                  className={`transition-colors hover:bg-surface-container-highest/40 ${
                    i % 2 === 0 ? "bg-surface-container-lowest" : "bg-surface-container-low"
                  }`}
                >
                  <td className="px-5 py-3.5 font-medium text-on-surface">{m.name}</td>
                  <td className="px-5 py-3.5 text-on-surface/60">{m.generic_name}</td>
                  <td className="px-5 py-3.5 text-on-surface/60">{m.category || "—"}</td>
                  <td className="px-5 py-3.5 text-on-surface/60">{m.default_refill_days}d</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Add medication modal */}
      {showForm && (
        <div className="fixed inset-0 bg-on-surface/40 flex items-center justify-center z-50">
          <div className="bg-surface-container-lowest/90 backdrop-blur-[20px] rounded-2xl shadow-float p-6 w-full max-w-md">
            <h2 className="font-display text-xl font-bold text-on-surface mb-5">Add Medication</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block font-body text-xs font-medium text-on-surface/70 mb-1.5">Brand Name</label>
                <input
                  type="text"
                  required
                  value={form.name}
                  onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
                  className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 font-body text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary-fixed"
                />
              </div>
              <div>
                <label className="block font-body text-xs font-medium text-on-surface/70 mb-1.5">Generic Name</label>
                <input
                  type="text"
                  required
                  value={form.generic_name}
                  onChange={(e) => setForm((p) => ({ ...p, generic_name: e.target.value }))}
                  className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 font-body text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary-fixed"
                />
              </div>
              <div>
                <label className="block font-body text-xs font-medium text-on-surface/70 mb-1.5">Category</label>
                <input
                  type="text"
                  placeholder="e.g. Antihypertensive"
                  value={form.category}
                  onChange={(e) => setForm((p) => ({ ...p, category: e.target.value }))}
                  className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 font-body text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary-fixed"
                />
              </div>
              <div>
                <label className="block font-body text-xs font-medium text-on-surface/70 mb-1.5">Default Refill Days</label>
                <input
                  type="number"
                  required
                  min={1}
                  value={form.default_refill_days}
                  onChange={(e) => setForm((p) => ({ ...p, default_refill_days: e.target.value }))}
                  className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 font-body text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary-fixed"
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="submit"
                  disabled={saving}
                  className="flex-1 bg-gradient-to-br from-primary to-primary-container text-white rounded-pill py-2.5 font-body text-sm font-semibold disabled:opacity-60"
                >
                  {saving ? "Saving…" : "Add Medication"}
                </button>
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
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
