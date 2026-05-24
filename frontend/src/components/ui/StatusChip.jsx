/**
 * StatusChip — Adheris status pill
 *
 * variants:
 *   "on-track"      — green-soft (positive)
 *   "non-adherence" — coral-soft (urgent / missed)
 *   "pending"       — gold-soft (warning / awaiting)
 *   "info"          — teal-soft (informational)
 *   default         — warm cream (neutral)
 *
 * Same prop API as before.
 */
const VARIANT_CLASSES = {
  "on-track":      "bg-green-container text-green",
  "non-adherence": "bg-error-container text-accent",
  pending:         "bg-gold-container text-gold",
  info:            "bg-secondary-container text-secondary",
  default:         "bg-surface-container-low text-on-surface/70",
};

export default function StatusChip({ children, variant = "default", className = "" }) {
  const cls = VARIANT_CLASSES[variant] ?? VARIANT_CLASSES.default;
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-pill font-body text-[10.5px] font-semibold uppercase tracking-[0.08em] ${cls} ${className}`}
    >
      {children}
    </span>
  );
}
