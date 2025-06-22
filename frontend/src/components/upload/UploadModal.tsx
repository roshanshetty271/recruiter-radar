"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Upload, FileText, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import UploadZone from "./UploadZone";
import UploadStatusList from "./UploadStatusList";
import { useSession } from "../../contexts/SessionContext";
import { UploadStatusResponse } from "../../services/types";

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadComplete?: (results: UploadStatusResponse[]) => void;
}

export default function UploadModal({
  isOpen,
  onClose,
  onUploadComplete,
}: UploadModalProps) {
  const { session, remainingUploads, canUpload } = useSession();
  const [uploadResults, setUploadResults] = useState<UploadStatusResponse[]>(
    []
  );
  const [isUploading, setIsUploading] = useState(false);

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setUploadResults([]);
      setIsUploading(false);
    }
  }, [isOpen]);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen && !isUploading) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      // Prevent background scroll
      document.body.style.overflow = "hidden";
    }

    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "unset";
    };
  }, [isOpen, isUploading, onClose]);

  const handleUploadStart = () => {
    setIsUploading(true);
  };

  const handleUploadProgress = (result: UploadStatusResponse) => {
    setUploadResults((prev) => {
      const existing = prev.find((r) => r.filename === result.filename);
      if (existing) {
        return prev.map((r) => (r.filename === result.filename ? result : r));
      }
      return [...prev, result];
    });
  };

  const handleUploadComplete = (allResults: UploadStatusResponse[]) => {
    setIsUploading(false);
    setUploadResults(allResults);
    onUploadComplete?.(allResults);
  };

  const handleClose = () => {
    if (!isUploading) {
      onClose();
    }
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget && !isUploading) {
      onClose();
    }
  };

  const successCount = uploadResults.filter(
    (r) => r.status === "success"
  ).length;
  const errorCount = uploadResults.filter(
    (r) => r.status === "pdf_error" || r.status === "extraction_error"
  ).length;

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          onClick={handleBackdropClick}
        >
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
          />

          {/* Modal */}
          <motion.div
            initial={{ scale: 0.95, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.95, opacity: 0, y: 20 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="relative w-full max-w-2xl max-h-[90vh] bg-background border rounded-xl shadow-2xl overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b bg-background/95 backdrop-blur-sm">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <Upload className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold">Upload Resumes</h2>
                  <p className="text-sm text-muted-foreground">
                    {canUpload
                      ? `${remainingUploads} upload${
                          remainingUploads !== 1 ? "s" : ""
                        } remaining`
                      : "Upload limit reached"}
                  </p>
                </div>
              </div>

              <Button
                variant="ghost"
                size="icon"
                onClick={handleClose}
                disabled={isUploading}
                className="rounded-full"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>

            {/* Content */}
            <div className="p-6 space-y-6 overflow-y-auto max-h-[calc(90vh-140px)]">
              {/* Upload limit warning */}
              {!canUpload && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-center gap-3 p-4 bg-orange-500/10 border border-orange-500/20 rounded-lg"
                >
                  <AlertCircle className="w-5 h-5 text-orange-500 flex-shrink-0" />
                  <div>
                    <p className="font-medium text-orange-700 dark:text-orange-300">
                      Upload Limit Reached
                    </p>
                    <p className="text-sm text-orange-600 dark:text-orange-400">
                      You've reached the maximum of 10 uploads for this session.
                      Start a new session to upload more resumes.
                    </p>
                  </div>
                </motion.div>
              )}

              {/* Upload Zone */}
              {canUpload && (
                <UploadZone
                  sessionId={session.id}
                  onUploadStart={handleUploadStart}
                  onUploadProgress={handleUploadProgress}
                  onUploadComplete={handleUploadComplete}
                  disabled={!canUpload || isUploading}
                  maxFiles={remainingUploads}
                />
              )}

              {/* Upload Status */}
              {uploadResults.length > 0 && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="font-medium flex items-center gap-2">
                      <FileText className="w-4 h-4" />
                      Upload Results
                    </h3>
                    {uploadResults.length > 0 && (
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        {successCount > 0 && (
                          <span className="text-green-600 dark:text-green-400">
                            ✓ {successCount} successful
                          </span>
                        )}
                        {errorCount > 0 && (
                          <span className="text-red-600 dark:text-red-400">
                            ✗ {errorCount} failed
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  <UploadStatusList
                    uploadResults={uploadResults}
                    isUploading={isUploading}
                  />
                </div>
              )}

              {/* Tips */}
              {canUpload && uploadResults.length === 0 && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.3 }}
                  className="space-y-3"
                >
                  <h3 className="font-medium text-sm">
                    Tips for best results:
                  </h3>
                  <ul className="space-y-2 text-sm text-muted-foreground">
                    <li className="flex items-start gap-2">
                      <span className="text-primary mt-1">•</span>
                      Upload PDF files only (max 10MB each)
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-primary mt-1">•</span>
                      Ensure resumes contain clear text (not image-only)
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-primary mt-1">•</span>
                      Include contact information and skills for best matching
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-primary mt-1">•</span>
                      Processing typically takes 5-10 seconds per resume
                    </li>
                  </ul>
                </motion.div>
              )}
            </div>

            {/* Footer */}
            {uploadResults.length > 0 && !isUploading && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-between p-6 border-t bg-muted/30"
              >
                <div className="text-sm text-muted-foreground">
                  {successCount > 0 && (
                    <span>
                      {successCount} resume{successCount !== 1 ? "s" : ""}{" "}
                      processed successfully
                    </span>
                  )}
                </div>

                <Button onClick={handleClose}>Done</Button>
              </motion.div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
