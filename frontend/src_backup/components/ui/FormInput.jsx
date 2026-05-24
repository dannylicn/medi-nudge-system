/**
 * FormInput — Clinical Serenity input field
 *
 * States:
 *   default  — surface-container-highest fill, no border
 *   focus    — 2px primary-fixed ring
 *   error    — error-container fill, error/40 ring
 *
 * Props:
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
        <label htmlFor={id} className="block font-body text-xs font-medium text-on-surface/70 mb-1.5">
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
        className={`w-full rounded-xl px-3.5 py-2.5 font-body text-sm text-on-surface outline-none focus:ring-2 transition-shadow ${
          error
            ? "bg-error-container focus:ring-error/40"
            : "bg-surface-container-highest focus:ring-primary-fixed"
        }`}
      />
      {error && errorMessage && (
        <p className="mt-1 font-body text-xs text-error">{errorMessage}</p>
      )}
    </div>
  );
}
