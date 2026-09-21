import React, { useState } from "react";
import UploadZone from "./components/UploadZone.jsx";
import StatsBar from "./components/StatsBar.jsx";
import LeadsTable from "./components/LeadsTable.jsx";
import { uploadImages, updateLead, retryLead, deleteBatch, exportExcel } from "./services/api.js";

export default function App() {
  const [batchId, setBatchId] = useState(null);
  const [leads, setLeads] = useState([]);
  const [stats, setStats] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [errorMsg, setErrorMsg] = useState("");

  const handleUpload = async (files) => {
    setUploading(true);
    setProgress(0);
    setErrorMsg("");
    try {
      const data = await uploadImages(files, batchId, setProgress);
      setBatchId(data.batch_id);
      setLeads(data.leads);
      setStats(data.stats);
    } catch (err) {
      setErrorMsg(err?.response?.data?.detail || "Upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  };

  const handleUpdate = async (leadId, fields) => {
    try {
      const updated = await updateLead(batchId, leadId, fields);
      setLeads((prev) => prev.map((l) => (l.id === leadId ? updated : l)));
    } catch (err) {
      setErrorMsg("Failed to save edit.");
    }
  };

  const handleRetry = async (leadId) => {
    try {
      const updated = await retryLead(batchId, leadId);
      setLeads((prev) => {
        const next = prev.map((l) => (l.id === leadId ? updated : l));
        return next;
      });
    } catch (err) {
      setErrorMsg("Retry failed.");
    }
  };

  const handleReset = async () => {
    if (batchId) {
      try {
        await deleteBatch(batchId);
      } catch (_) {
        /* ignore */
      }
    }
    setBatchId(null);
    setLeads([]);
    setStats(null);
    setErrorMsg("");
  };

  const handleExport = async () => {
    if (!batchId) return;
    try {
      await exportExcel(batchId);
    } catch (err) {
      setErrorMsg("Export failed.");
    }
  };

  return (
    <div className="min-h-screen">
      <header className="bg-white border-b">
        <div className="max-w-6xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-xl font-semibold">Business Card Lead Extraction</h1>
          <div className="flex gap-2">
            <button
              onClick={handleExport}
              disabled={!leads.length}
              className="bg-green-600 hover:bg-green-700 disabled:bg-gray-300 text-white text-sm px-4 py-2 rounded-lg"
            >
              Download Excel
            </button>
            <button
              onClick={handleReset}
              disabled={!leads.length && !batchId}
              className="bg-gray-200 hover:bg-gray-300 disabled:opacity-50 text-gray-700 text-sm px-4 py-2 rounded-lg"
            >
              Reset Batch
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">
        <UploadZone onUpload={handleUpload} uploading={uploading} progress={progress} />

        {errorMsg && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-2">
            {errorMsg}
          </div>
        )}

        <StatsBar stats={stats} />

        <LeadsTable leads={leads} onUpdate={handleUpdate} onRetry={handleRetry} />
      </main>
    </div>
  );
}
