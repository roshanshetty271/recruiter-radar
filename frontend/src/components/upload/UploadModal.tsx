"use client";

import React, { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Upload } from "lucide-react";
import { Button } from "../ui/button";
import { UploadZone } from "./UploadZone";
import { UploadStatusList } from "./UploadStatusList";
import { useSession } from "../../contexts/SessionContext";
import { UploadStatusResponse } from "../../services/types";

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  uploadStatuses: UploadStatusResponse[];
  onUpload: (files: File[]) => void;
}

export function UploadModal({
  isOpen,
  onClose,
  uploadStatuses,
  onUpload,
}: UploadModalProps) {
  const { remainingUploads } = useSession();

  // Close on escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      // Prevent body scroll when modal is open
      document.body.style.overflow = "hidden";
    }

    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "auto";
    };
  }, [isOpen, onClose]);

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Modal Content */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="relative bg-gray-900/95 backdrop-blur-xl border border-gray-700 rounded-2xl shadow-2xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-700">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-purple-600/20 rounded-lg flex items-center justify-center">
                  <Upload className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-white">
                    Upload Resumes
                  </h2>
                  <p className="text-sm text-gray-400">
                    {remainingUploads > 0
                      ? `${remainingUploads} upload${
                          remainingUploads === 1 ? "" : "s"
                        } remaining`
                      : "Upload limit reached"}
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                className="text-gray-400 hover:text-white hover:bg-gray-800"
              >
                <X className="w-5 h-5" />
              </Button>
            </div>

            {/* Content */}
            <div className="p-6 space-y-6 max-h-[calc(90vh-140px)] overflow-y-auto">
              {/* Upload Zone */}
              <UploadZone
                onUpload={onUpload}
                disabled={remainingUploads === 0}
                remainingUploads={remainingUploads}
              />

              {/* Status List */}
              {uploadStatuses.length > 0 && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-medium text-white">
                      Upload Status
                    </h3>
                    <span className="text-sm text-gray-400">
                      {uploadStatuses.length} file
                      {uploadStatuses.length === 1 ? "" : "s"}
                    </span>
                  </div>
                  <UploadStatusList statuses={uploadStatuses} />
                </div>
              )}

              {/* Empty State */}
              {uploadStatuses.length === 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 }}
                  className="text-center py-8"
                >
                  <div className="w-16 h-16 bg-gray-800 rounded-full mx-auto mb-4 flex items-center justify-center">
                    <Upload className="w-8 h-8 text-gray-500" />
                  </div>
                  <p className="text-gray-400 mb-2">No files uploaded yet</p>
                  <p className="text-sm text-gray-500">
                    Drag and drop PDF resumes above to get started
                  </p>
                </motion.div>
              )}
            </div>

            {/* Footer */}
            <div className="border-t border-gray-700 p-4 bg-gray-900/50">
              <div className="flex items-center justify-between text-sm text-gray-400">
                <span>Supports PDF files up to 10MB</span>
                <span>Session expires in 48 hours</span>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
