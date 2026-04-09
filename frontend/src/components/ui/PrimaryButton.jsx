/**
 * PrimaryButton — gradient pill CTA (Clinical Serenity design system)
 *
 * Props:
 *   children, onClick, type, disabled, className
 */
export default function PrimaryButton({ children, onClick, type = "button", disabled = false, className = "" }) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`bg-gradient-to-br from-primary to-primary-container text-white rounded-pill font-body text-sm font-semibold px-5 py-2.5 disabled:opacity-60 transition-opacity hover:opacity-90 ${className}`}
    >
      {children}
    </button>
  );
}
