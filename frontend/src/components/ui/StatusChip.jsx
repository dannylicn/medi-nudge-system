/**
 * StatusChip — borderless status pill (Clinical Serenity design system)
 *
 * variant:
 *   "on-track"       — tertiary-container (green)
 *   "non-adherence"  — error-container (soft red)
 *   "pending"        — yellow-100
 *   "info"           — secondary-container (blue)
 *   default          — surface-container-highest (neutral)
 *
 * Props:
 *   children, variant, className
 */
const VARIANT_CLASSES = {
  "on-track": "bg-tertiary-container text-on-tertiary-container",
  "non-adherence": "bg-error-container text-on-error-container",
  pending: "bg-yellow-100 text-yellow-800",
  info: "bg-secondary-container text-secondary",
  default: "bg-surface-container-highest text-on-surface/60",
};

export default function StatusChip({ children, variant = "default", className = "" }) {
  const cls = VARIANT_CLASSES[variant] ?? VARIANT_CLASSES.default;
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-pill font-body text-xs font-semibold ${cls} ${className}`}>
      {children}
    </span>
  );
}
