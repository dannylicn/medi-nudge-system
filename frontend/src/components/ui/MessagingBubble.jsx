/**
 * MessagingBubble — chat bubble (Adheris)
 *
 * sender:
 *   "patient"    — teal-soft (cool / received)
 *   "clinician"  — warm cream (right-aligned)
 *
 * Props (unchanged):
 *   children, sender, timestamp, className
 */
export default function MessagingBubble({
  children,
  sender = "clinician",
  timestamp,
  className = "",
}) {
  const isPatient = sender === "patient";
  return (
    <div className={`flex ${isPatient ? "justify-start" : "justify-end"} ${className}`}>
      <div
        className={`max-w-xs rounded-2xl px-4 py-2.5 font-body text-sm ${
          isPatient
            ? "bg-secondary-container text-secondary rounded-tl-sm"
            : "bg-surface-container-low text-on-surface rounded-tr-sm"
        }`}
      >
        {children}
        {timestamp && <p className="mt-1 text-xs opacity-50 text-right">{timestamp}</p>}
      </div>
    </div>
  );
}
