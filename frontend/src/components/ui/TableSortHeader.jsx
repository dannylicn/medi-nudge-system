/**
 * TableSortHeader — clickable `<th>` that toggles asc/desc sort.
 *
 * Used inside `<thead><tr>…</tr></thead>` of the dashboard patient
 * registry and the medications catalog table.
 *
 * Props:
 *   label   — column header text
 *   sortKey — unique key for this column
 *   active  — current sort key (compare with sortKey)
 *   dir     — "asc" | "desc"
 *   onSort  — (sortKey) => void  — toggles direction if same key, else asc
 *   align   — "left" | "center" | "right"  (default "left")
 *   className — extra Tailwind classes for the <th>
 */
export default function TableSortHeader({
  label,
  sortKey,
  active,
  dir,
  onSort,
  align = "left",
  className = "",
}) {
  const isActive = active === sortKey;
  const alignCls =
    align === "right" ? "text-right justify-end" :
    align === "center" ? "text-center justify-center" :
    "text-left";

  return (
    <th
      onClick={() => onSort(sortKey)}
      aria-sort={isActive ? (dir === "asc" ? "ascending" : "descending") : "none"}
      className={`px-4 py-3 font-bold cursor-pointer select-none ${alignCls} ${isActive ? "text-on-surface" : ""} ${className}`}
    >
      <span className={`inline-flex items-center gap-1.5 ${align !== "left" ? alignCls : ""}`}>
        {label}
        <SortArrow active={isActive} dir={dir} />
      </span>
    </th>
  );
}

function SortArrow({ active, dir }) {
  const upFill   = active && dir === "asc"  ? "#E85A3C" : "rgba(14,26,43,.22)";
  const downFill = active && dir === "desc" ? "#E85A3C" : "rgba(14,26,43,.22)";
  return (
    <svg width="9" height="12" viewBox="0 0 9 12" className="flex-shrink-0" aria-hidden="true">
      <path d="M4.5 0 L9 4 L0 4 Z" fill={upFill} />
      <path d="M4.5 12 L9 8 L0 8 Z" fill={downFill} />
    </svg>
  );
}
