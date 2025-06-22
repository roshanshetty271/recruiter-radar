"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Clock,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  FileText,
  Loader2,
  User,
} from "lucide-react";
import { UploadStatusResponse } from "../../services/types";
import { Badge } from "../ui/badge";
import { Progress } from "../ui/progress";

interface UploadStatusListProps {
  uploadResults: UploadStatusResponse[];
  isUploading: boolean;
}

export default function UploadStatusList({
  uploadResults,
  isUploading,
}: UploadStatusListProps) {
  const getStatusIcon = (status: UploadStatusResponse["status"]) => {
    switch (status) {
      case "success":
        return <CheckCircle2 className="w-5 h-5 text-green-500" />;
      case "partial_success":
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
      case "pdf_error":
      case "extraction_error":
        return <XCircle className="w-5 h-5 text-red-500" />;
      case "processing":
        return (
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
          >
            <Loader2 className="w-5 h-5 text-blue-500" />
          </motion.div>
        );
      case "pending":
      default:
        return <Clock className="w-5 h-5 text-gray-500" />;
    }
  };

  const getStatusColor = (status: UploadStatusResponse["status"]) => {
    switch (status) {
      case "success":
        return "bg-green-500/10 border-green-500/20 text-green-700 dark:text-green-300";
      case "partial_success":
        return "bg-yellow-500/10 border-yellow-500/20 text-yellow-700 dark:text-yellow-300";
      case "pdf_error":
      case "extraction_error":
        return "bg-red-500/10 border-red-500/20 text-red-700 dark:text-red-300";
      case "processing":
        return "bg-blue-500/10 border-blue-500/20 text-blue-700 dark:text-blue-300";
      case "pending":
      default:
        return "bg-gray-500/10 border-gray-500/20 text-gray-700 dark:text-gray-300";
    }
  };

  const getStatusText = (status: UploadStatusResponse["status"]) => {
    switch (status) {
      case "success":
        return "Success";
      case "partial_success":
        return "Partial";
      case "pdf_error":
        return "PDF Error";
      case "extraction_error":
        return "Extract Error";
      case "processing":
        return "Processing";
      case "pending":
      default:
        return "Pending";
    }
  };

  const formatProcessingTime = (timeMs: number) => {
    if (timeMs < 1000) return `${timeMs}ms`;
    return `${(timeMs / 1000).toFixed(1)}s`;
  };

  return (
    <div className="space-y-3">
      <AnimatePresence>
        {uploadResults.map((result, index) => (
          <motion.div
            key={result.filename}
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.95 }}
            transition={{
              duration: 0.3,
              delay: index * 0.1,
              ease: "easeOut",
            }}
            className="border rounded-lg p-4 bg-card/50 backdrop-blur-sm"
          >
            <div className="flex items-start gap-3">
              {/* Status Icon */}
              <div className="flex-shrink-0 mt-0.5">
                {getStatusIcon(result.status)}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    {/* Filename */}
                    <div className="flex items-center gap-2 mb-1">
                      <FileText className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                      <h4
                        className="font-medium text-sm truncate"
                        title={result.filename}
                      >
                        {result.filename}
                      </h4>
                    </div>

                    {/* Extracted Name */}
                    {result.extracted_name && (
                      <div className="flex items-center gap-2 mb-2">
                        <User className="w-3 h-3 text-muted-foreground flex-shrink-0" />
                        <span className="text-sm text-muted-foreground">
                          {result.extracted_name}
                        </span>
                      </div>
                    )}

                    {/* Message */}
                    {result.message && (
                      <p className="text-sm text-muted-foreground mb-2">
                        {result.message}
                      </p>
                    )}

                    {/* Processing Time */}
                    {result.processing_time_ms > 0 && (
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span>
                          Processed in{" "}
                          {formatProcessingTime(result.processing_time_ms)}
                        </span>
                        {result.operation_type && (
                          <span className="capitalize">
                            {result.operation_type}
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Status Badge */}
                  <Badge
                    variant="outline"
                    className={`${getStatusColor(result.status)} flex-shrink-0`}
                  >
                    {getStatusText(result.status)}
                  </Badge>
                </div>
              </div>
            </div>

            {/* Progress Bar for Processing */}
            {result.status === "processing" && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="mt-3 pt-3 border-t"
              >
                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  <span>Extracting candidate information...</span>
                </div>
                <div className="w-full bg-muted rounded-full h-1">
                  <motion.div
                    className="bg-primary h-1 rounded-full"
                    initial={{ width: "0%" }}
                    animate={{ width: "100%" }}
                    transition={{
                      duration: 2,
                      repeat: Infinity,
                      ease: "easeInOut",
                    }}
                  />
                </div>
              </motion.div>
            )}
          </motion.div>
        ))}
      </AnimatePresence>

      {/* Processing Indicator */}
      {isUploading && uploadResults.length === 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-center gap-3 p-6 border rounded-lg bg-card/30"
        >
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
          >
            <Loader2 className="w-5 h-5 text-primary" />
          </motion.div>
          <span className="text-sm text-muted-foreground">
            Preparing uploads...
          </span>
        </motion.div>
      )}

      {/* Empty State */}
      {!isUploading && uploadResults.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-6 text-muted-foreground"
        >
          <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No uploads yet</p>
        </motion.div>
      )}
    </div>
  );
}
