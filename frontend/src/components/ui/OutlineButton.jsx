/**
 * OutlineButton — Adheris ghost / secondary button
 *
 * Transparent fill with ink-soft border. Same prop API as before.
 *
 * Props:
 *   children, onClick, type, disabled, className
 */
export default function OutlineButton({
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
      className={`bg-transparent border border-outline-variant rounded-pill font-body text-sm font-semibold text-on-surface px-5 py-2.5 disabled:opacity-60 transition-colors hover:bg-surface-container-low ${className}`}
    >
      {children}
    </button>
  );
}
