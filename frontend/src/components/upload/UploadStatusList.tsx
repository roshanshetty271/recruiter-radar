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
} from "lucide-react";
import { UploadStatusResponse } from "../../services/types";
import { Badge } from "../ui/badge";
import { Progress } from "../ui/progress";

interface UploadStatusListProps {
  statuses: UploadStatusResponse[];
}

export function UploadStatusList({ statuses }: UploadStatusListProps) {
  const getStatusIcon = (status: UploadStatusResponse["status"]) => {
    switch (status) {
      case "pending":
        return <Clock className="w-4 h-4 text-yellow-400" />;
      case "processing":
        return <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />;
      case "success":
        return <CheckCircle2 className="w-4 h-4 text-green-400" />;
      case "partial_success":
        return <AlertTriangle className="w-4 h-4 text-yellow-400" />;
      case "pdf_error":
      case "extraction_error":
        return <XCircle className="w-4 h-4 text-red-400" />;
      default:
        return <FileText className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusColor = (status: UploadStatusResponse["status"]) => {
    switch (status) {
      case "pending":
        return "border-yellow-500/30 bg-yellow-500/10";
      case "processing":
        return "border-blue-500/30 bg-blue-500/10";
      case "success":
        return "border-green-500/30 bg-green-500/10";
      case "partial_success":
        return "border-yellow-500/30 bg-yellow-500/10";
      case "pdf_error":
      case "extraction_error":
        return "border-red-500/30 bg-red-500/10";
      default:
        return "border-gray-500/30 bg-gray-500/10";
    }
  };

  const getStatusBadge = (
    status: UploadStatusResponse["status"],
    operationType?: string
  ) => {
    const isUpdate = operationType === "update";

    switch (status) {
      case "pending":
        return (
          <Badge
            variant="secondary"
            className="text-yellow-400 bg-yellow-500/20"
          >
            Pending
          </Badge>
        );
      case "processing":
        return (
          <Badge variant="secondary" className="text-blue-400 bg-blue-500/20">
            Processing
          </Badge>
        );
      case "success":
        return (
          <div className="flex items-center space-x-2">
            <Badge
              variant="secondary"
              className="text-green-400 bg-green-500/20"
            >
              {isUpdate ? "Updated" : "Success"}
            </Badge>
            {isUpdate && (
              <Badge
                variant="outline"
                className="text-purple-400 border-purple-500/30"
              >
                Replaced
              </Badge>
            )}
          </div>
        );
      case "partial_success":
        return (
          <Badge
            variant="secondary"
            className="text-yellow-400 bg-yellow-500/20"
          >
            Partial
          </Badge>
        );
      case "pdf_error":
        return (
          <Badge variant="secondary" className="text-red-400 bg-red-500/20">
            PDF Error
          </Badge>
        );
      case "extraction_error":
        return (
          <Badge variant="secondary" className="text-red-400 bg-red-500/20">
            AI Error
          </Badge>
        );
      default:
        return <Badge variant="secondary">Unknown</Badge>;
    }
  };

  const getProgressValue = (status: UploadStatusResponse["status"]) => {
    switch (status) {
      case "pending":
        return 10;
      case "processing":
        return 50;
      case "success":
        return 100;
      case "partial_success":
        return 80;
      case "pdf_error":
      case "extraction_error":
        return 100; // Complete but failed
      default:
        return 0;
    }
  };

  return (
    <div className="space-y-3">
      <AnimatePresence>
        {statuses.map((status, index) => (
          <motion.div
            key={`${status.filename}-${index}`}
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.95 }}
            transition={{
              duration: 0.3,
              delay: index * 0.1, // Staggered entrance
              ease: "easeOut",
            }}
            className={`
              p-4 rounded-lg border transition-all duration-300
              ${getStatusColor(status.status)}
            `}
          >
            <div className="flex items-start justify-between space-x-4">
              {/* Left side - Icon and details */}
              <div className="flex items-start space-x-3 flex-1 min-w-0">
                {/* Status Icon */}
                <div className="flex-shrink-0 mt-0.5">
                  {getStatusIcon(status.status)}
                </div>

                {/* File details */}
                <div className="flex-1 min-w-0 space-y-2">
                  {/* Filename and extracted name */}
                  <div className="space-y-1">
                    <p className="text-sm font-medium text-white truncate">
                      {status.filename}
                    </p>
                    {status.extracted_name && (
                      <motion.p
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.3 }}
                        className="text-sm text-green-400"
                      >
                        ✨ Extracted: {status.extracted_name}
                      </motion.p>
                    )}
                  </div>

                  {/* Status message */}
                  <p className="text-xs text-gray-400 leading-relaxed">
                    {status.message}
                  </p>

                  {/* Progress bar for processing states */}
                  {(status.status === "pending" ||
                    status.status === "processing") && (
                    <motion.div
                      initial={{ opacity: 0, scaleX: 0 }}
                      animate={{ opacity: 1, scaleX: 1 }}
                      transition={{ delay: 0.2 }}
                      className="space-y-1"
                    >
                      <Progress
                        value={getProgressValue(status.status)}
                        className="h-1.5"
                      />
                      <p className="text-xs text-gray-500">
                        {status.status === "processing"
                          ? "Extracting candidate data..."
                          : "Queued for processing"}
                      </p>
                    </motion.div>
                  )}

                  {/* Processing time */}
                  {status.processing_time_ms > 0 && (
                    <p className="text-xs text-gray-500">
                      Processed in{" "}
                      {(status.processing_time_ms / 1000).toFixed(1)}s
                    </p>
                  )}
                </div>
              </div>

              {/* Right side - Status badge */}
              <div className="flex-shrink-0">
                {getStatusBadge(status.status, status.operation_type)}
              </div>
            </div>

            {/* Success celebration animation */}
            {status.status === "success" && (
              <motion.div
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: [0, 1.2, 1], opacity: [0, 1, 0] }}
                transition={{
                  duration: 1.5,
                  times: [0, 0.3, 1],
                  delay: 0.5,
                }}
                className="absolute inset-0 rounded-lg border-2 border-green-400/50 pointer-events-none"
              />
            )}
          </motion.div>
        ))}
      </AnimatePresence>

      {/* Summary stats */}
      {statuses.length > 1 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: statuses.length * 0.1 + 0.2 }}
          className="pt-3 border-t border-gray-700"
        >
          <div className="flex items-center justify-between text-xs text-gray-400">
            <span>
              {statuses.filter((s) => s.status === "success").length}{" "}
              successful,{" "}
              {
                statuses.filter(
                  (s) => s.status === "processing" || s.status === "pending"
                ).length
              }{" "}
              processing,{" "}
              {statuses.filter((s) => s.status.includes("error")).length} failed
            </span>
            <span>Total: {statuses.length} files</span>
          </div>
        </motion.div>
      )}
    </div>
  );
}
