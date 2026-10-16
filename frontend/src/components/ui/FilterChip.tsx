interface Props {
  label: string;
  variant?: "active" | "neutral";
}

/** Small read-only pill showing which filter is applied to a dashboard section. */
export function FilterChip({ label, variant = "neutral" }: Props) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs border ${
        variant === "active"
          ? "bg-brand-50 text-brand-700 border-brand-200"
          : "bg-gray-50 text-gray-600 border-gray-200"
      }`}
    >
      {label}
    </span>
  );
}
