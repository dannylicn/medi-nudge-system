/**
 * FormInput — Adheris input field
 *
 * States:
 *   default — surface bg, subtle outline border
 *   focus   — coral 3px halo
 *   error   — coral-soft fill with coral ring
 *
 * Props (unchanged from before):
 *   id, label, type, value, onChange, placeholder, required, autoComplete,
 *   error (boolean), errorMessage (string), className
 */
export default function FormInput({
  id,
  label,
  type = "text",
  value,
  onChange,
  placeholder,
  required = false,
  autoComplete,
  error = false,
  errorMessage,
  className = "",
}) {
  return (
    <div className={className}>
      {label && (
        <label
          htmlFor={id}
          className="block font-body text-[11px] font-semibold tracking-eyebrow uppercase text-muted mb-1.5"
        >
          {label}
        </label>
      )}
      <input
        id={id}
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        autoComplete={autoComplete}
        className={`w-full rounded-xl border px-3.5 py-2.5 font-body text-sm text-on-surface outline-none transition-shadow ${
          error
            ? "bg-error-container border-accent/30 focus:ring-[3px] focus:ring-accent/25"
            : "bg-surface border-outline-variant focus:border-accent focus:ring-[3px] focus:ring-accent/15"
        }`}
      />
      {error && errorMessage && (
        <p className="mt-1 font-body text-xs text-accent">{errorMessage}</p>
      )}
    </div>
  );
}
