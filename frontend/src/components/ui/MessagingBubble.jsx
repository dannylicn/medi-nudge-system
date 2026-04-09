/**
 * MessagingBubble — WhatsApp-style chat bubble (Clinical Serenity design system)
 *
 * sender:
 *   "patient"    — secondary-container (#90c9ff) with secondary text
 *   "clinician"  — surface-container-highest (#e0e3e5) with on-surface text
 *
 * Props:
 *   children, sender, timestamp, className
 */
export default function MessagingBubble({ children, sender = "clinician", timestamp, className = "" }) {
  const isPatient = sender === "patient";
  return (
    <div className={`flex ${isPatient ? "justify-start" : "justify-end"} ${className}`}>
      <div
        className={`max-w-xs rounded-xl px-4 py-2.5 font-body text-sm ${
          isPatient
            ? "bg-secondary-container text-secondary rounded-tl-sm"
            : "bg-surface-container-highest text-on-surface rounded-tr-sm"
        }`}
      >
        {children}
        {timestamp && (
          <p className="mt-1 text-xs opacity-50 text-right">{timestamp}</p>
        )}
      </div>
    </div>
  );
}
