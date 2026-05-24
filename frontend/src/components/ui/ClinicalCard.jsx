/**
 * ClinicalCard — Adheris content surface
 *
 * White card with soft ambient shadow and 1px outline border for definition.
 * Same prop API as before.
 *
 * Props: children, className
 */
export default function ClinicalCard({ children, className = "" }) {
  return (
    <div
      className={`bg-surface-container-lowest border border-outline-variant rounded-2xl shadow-soft p-6 ${className}`}
    >
      {children}
    </div>
  );
}
