/**
 * PrimaryButton — Adheris primary CTA
 *
 * Solid ink fill, coral on hover. Same prop API as before so all
 * consumers continue to work unchanged.
 *
 * Props:
 *   children, onClick, type, disabled, className
 */
export default function PrimaryButton({
  children,
  onClick,
  type = "button",
  disabled = false,
  className = "",
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`bg-ink text-surface rounded-pill font-body text-sm font-semibold px-5 py-2.5 disabled:opacity-60 transition-colors hover:bg-accent ${className}`}
    >
      {children}
    </button>
  );
}
