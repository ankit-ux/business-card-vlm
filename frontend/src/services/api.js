import axios from "axios";

const api = axios.create({ baseURL: "/api" });

export async function uploadImages(files, batchId, onProgress) {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  if (batchId) formData.append("batch_id", batchId);

  const res = await api.post("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (evt) => {
      if (onProgress && evt.total) {
        onProgress(Math.round((evt.loaded * 100) / evt.total));
      }
    },
  });
  return res.data;
}

export async function getLeads(batchId) {
  const res = await api.get(`/leads/${batchId}`);
  return res.data;
}

export async function updateLead(batchId, leadId, fields) {
  const res = await api.patch(`/leads/${batchId}/${leadId}`, fields);
  return res.data;
}

export async function retryLead(batchId, leadId) {
  const res = await api.post(`/leads/${batchId}/retry/${leadId}`);
  return res.data;
}

export async function deleteBatch(batchId) {
  const res = await api.delete(`/leads/${batchId}`);
  return res.data;
}

export async function exportExcel(batchId) {
  const res = await api.get(`/leads/${batchId}/export`, { responseType: "blob" });
  const url = window.URL.createObjectURL(new Blob([res.data]));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", `leads_${batchId.slice(0, 8)}.xlsx`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export default api;
