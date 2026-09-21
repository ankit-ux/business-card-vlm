import React from "react";

const FIELDS = [
  { key: "first_name", label: "First Name" },
  { key: "last_name", label: "Last Name" },
  { key: "position", label: "Position" },
  { key: "company", label: "Company" },
  { key: "location", label: "Location" },
  { key: "phone", label: "Phone" },
  { key: "email", label: "Email" },
];

export default function LeadsTable({ leads, onUpdate, onRetry }) {
  if (!leads || leads.length === 0) {
    return <p className="text-gray-500 text-sm">No leads yet. Upload some business cards above.</p>;
  }

  const handleBlur = (leadId, field, value, original) => {
    if (value !== original) {
      onUpdate(leadId, { [field]: value });
    }
  };

  return (
    <div className="overflow-x-auto bg-white rounded-lg border">
      <table className="min-w-full text-sm">
        <thead className="bg-gray-100 text-gray-600 text-left">
          <tr>
            <th className="px-3 py-2 whitespace-nowrap">Status</th>
            {FIELDS.map((f) => (
              <th key={f.key} className="px-3 py-2 whitespace-nowrap">
                {f.label}
              </th>
            ))}
            <th className="px-3 py-2 whitespace-nowrap">Source</th>
            <th className="px-3 py-2 whitespace-nowrap">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {leads.map((lead) => (
            <tr
              key={lead.id}
              className={
                lead.status === "failed"
                  ? "bg-red-50"
                  : lead.is_duplicate
                  ? "bg-yellow-50"
                  : "bg-white"
              }
            >
              <td className="px-3 py-2 whitespace-nowrap">
                {lead.status === "failed" ? (
                  <span className="text-red-600 text-xs font-medium" title={lead.error || ""}>
                    Failed
                  </span>
                ) : lead.is_duplicate ? (
                  <span className="text-yellow-700 text-xs font-medium">Duplicate</span>
                ) : (
                  <span className="text-green-600 text-xs font-medium">OK</span>
                )}
              </td>
              {FIELDS.map((f) => (
                <td key={f.key} className="px-3 py-2 min-w-[130px]">
                  <input
                    className="w-full bg-transparent focus:bg-blue-50 focus:outline-none rounded px-1 py-0.5"
                    defaultValue={lead[f.key] || ""}
                    onBlur={(e) => handleBlur(lead.id, f.key, e.target.value, lead[f.key])}
                  />
                </td>
              ))}
              <td className="px-3 py-2 max-w-[140px] truncate text-gray-500" title={lead.filename}>
                {lead.filename}
              </td>
              <td className="px-3 py-2 whitespace-nowrap">
                {lead.status === "failed" && (
                  <button
                    onClick={() => onRetry(lead.id)}
                    className="text-blue-600 hover:text-blue-800 text-xs font-medium"
                  >
                    Retry
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
