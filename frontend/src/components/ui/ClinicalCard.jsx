/**
 * ClinicalCard — tonal layering wrapper (Clinical Serenity design system)
 *
 * Renders a surface-container-lowest card with ambient shadow.
 * Use nested surface-container-low divs inside for sub-sections.
 *
 * Props:
 *   children, className
 */
export default function ClinicalCard({ children, className = "" }) {
  return (
    <div className={`bg-surface-container-lowest rounded-2xl shadow-ambient p-6 ${className}`}>
      {children}
    </div>
  );
}
