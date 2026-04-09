/**
 * OutlineButton — borderless pill with surface fill (Clinical Serenity)
 *
 * Props:
 *   children, onClick, type, disabled, className
 */
export default function OutlineButton({ children, onClick, type = "button", disabled = false, className = "" }) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`bg-surface-container-highest rounded-pill font-body text-sm text-on-surface/70 px-5 py-2.5 disabled:opacity-60 transition-colors hover:bg-outline-variant/30 ${className}`}
    >
      {children}
    </button>
  );
}
