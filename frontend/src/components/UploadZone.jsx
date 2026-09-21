import React, { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";

export default function UploadZone({ onUpload, uploading, progress }) {
  const [selectedFiles, setSelectedFiles] = useState([]);

  const onDrop = useCallback((acceptedFiles) => {
    setSelectedFiles((prev) => [...prev, ...acceptedFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "image/jpeg": [], "image/png": [], "image/webp": [] },
    multiple: true,
  });

  const removeFile = (idx) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleUploadClick = () => {
    if (selectedFiles.length === 0) return;
    onUpload(selectedFiles);
    setSelectedFiles([]);
  };

  return (
    <div className="w-full">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition
          ${isDragActive ? "border-blue-500 bg-blue-50" : "border-gray-300 bg-white"}`}
      >
        <input {...getInputProps()} />
        <p className="text-gray-600">
          {isDragActive
            ? "Drop the business card images here..."
            : "Drag & drop business card images here, or click to select (multiple allowed)"}
        </p>
        <p className="text-xs text-gray-400 mt-1">JPG, PNG, WEBP supported</p>
      </div>

      {selectedFiles.length > 0 && (
        <div className="mt-4 bg-white rounded-lg border p-4">
          <p className="text-sm font-medium mb-2">{selectedFiles.length} file(s) selected</p>
          <ul className="max-h-40 overflow-y-auto text-sm divide-y">
            {selectedFiles.map((f, idx) => (
              <li key={idx} className="flex justify-between items-center py-1">
                <span className="truncate mr-2">{f.name}</span>
                <button
                  onClick={() => removeFile(idx)}
                  className="text-red-500 hover:text-red-700 text-xs"
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
          <button
            onClick={handleUploadClick}
            disabled={uploading}
            className="mt-3 w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg py-2 text-sm font-medium"
          >
            {uploading ? `Processing... ${progress}%` : "Upload & Extract Leads"}
          </button>
          {uploading && (
            <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
