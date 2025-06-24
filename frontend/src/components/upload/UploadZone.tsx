"use client";

import React, { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload,
  FileText,
  AlertCircle,
  CheckCircle2,
  Loader2,
} from "lucide-react";
import { Button } from "../ui/button";
import { Progress } from "@/components/ui/progress";
import { useSession } from "@/contexts/SessionContext";
import { apiService } from "@/services/apiService";
import { UploadStatusResponse } from "@/services/types";

interface UploadZoneProps {
  sessionId: string;
  onUploadStart: () => void;
  onUploadProgress: (result: UploadStatusResponse) => void;
  onUploadComplete: (allResults: UploadStatusResponse[]) => void;
  disabled?: boolean;
  maxFiles?: number;
}

export default function UploadZone({
  sessionId,
  onUploadStart,
  onUploadProgress,
  onUploadComplete,
  disabled = false,
  maxFiles = 10,
}: UploadZoneProps) {
  const { incrementUpload } = useSession();
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{
    [filename: string]: number;
  }>({});
  const [uploadQueue, setUploadQueue] = useState<File[]>([]);

  const validateFile = (file: File): string | null => {
    // Check file type
    if (file.type !== "application/pdf") {
      return "Only PDF files are allowed";
    }

    // Check file size (10MB limit)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      return "File size must be less than 10MB";
    }

    // Check filename
    if (file.name.length > 100) {
      return "Filename is too long";
    }

    return null;
  };

  const uploadSingleFile = async (
    file: File
  ): Promise<UploadStatusResponse> => {
    try {
      // Simulate progress updates
      setUploadProgress((prev) => ({ ...prev, [file.name]: 0 }));

      // Start upload
      const result = await apiService.uploadResume(file, sessionId);

      // Complete progress
      setUploadProgress((prev) => ({ ...prev, [file.name]: 100 }));

      // Increment session upload count if successful
      if (result.status === "success") {
        incrementUpload();
      }

      return result;
    } catch (error) {
      console.error("Upload failed:", error);
      return {
        filename: file.name,
        status: "pdf_error",
        message: error instanceof Error ? error.message : "Upload failed",
        processing_time_ms: 0,
      };
    }
  };

  const handleUpload = async (files: File[]) => {
    if (files.length === 0) return;

    setIsUploading(true);
    setUploadQueue(files);
    onUploadStart();

    const results: UploadStatusResponse[] = [];

    // Process files sequentially to avoid overwhelming the server
    for (const file of files) {
      try {
        // Validate file
        const validationError = validateFile(file);
        if (validationError) {
          const errorResult: UploadStatusResponse = {
            filename: file.name,
            status: "pdf_error",
            message: validationError,
            processing_time_ms: 0,
          };
          results.push(errorResult);
          onUploadProgress(errorResult);
          continue;
        }

        // Upload file
        const result = await uploadSingleFile(file);
        results.push(result);
        onUploadProgress(result);

        // Small delay between uploads
        if (files.indexOf(file) < files.length - 1) {
          await new Promise((resolve) => setTimeout(resolve, 500));
        }
      } catch (error) {
        const errorResult: UploadStatusResponse = {
          filename: file.name,
          status: "pdf_error",
          message: "Unexpected error during upload",
          processing_time_ms: 0,
        };
        results.push(errorResult);
        onUploadProgress(errorResult);
      }
    }

    setIsUploading(false);
    setUploadQueue([]);
    setUploadProgress({});
    onUploadComplete(results);
  };

  const onDrop = useCallback(
    (acceptedFiles: File[], rejectedFiles: any[]) => {
      // Handle rejected files
      if (rejectedFiles.length > 0) {
        console.warn("Some files were rejected:", rejectedFiles);
      }

      // Limit number of files
      const filesToUpload = acceptedFiles.slice(0, maxFiles);
      if (acceptedFiles.length > maxFiles) {
        console.warn(`Only uploading first ${maxFiles} files`);
      }

      if (filesToUpload.length > 0) {
        handleUpload(filesToUpload);
      }
    },
    [maxFiles]
  );

  const {
    getRootProps,
    getInputProps,
    isDragActive,
    isDragAccept,
    isDragReject,
  } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
    },
    maxFiles,
    disabled: disabled || isUploading,
    multiple: true,
  });

  // Determine zone state
  const getZoneState = () => {
    if (disabled) return "disabled";
    if (isUploading) return "uploading";
    if (isDragReject) return "reject";
    if (isDragAccept) return "accept";
    if (isDragActive) return "active";
    return "idle";
  };

  const zoneState = getZoneState();

  // Zone styling based on state
  const getZoneStyles = () => {
    const baseStyles =
      "border-2 border-dashed rounded-xl p-8 text-center transition-all duration-200 cursor-pointer";

    switch (zoneState) {
      case "disabled":
        return `${baseStyles} border-muted bg-muted/20 cursor-not-allowed opacity-50`;
      case "uploading":
        return `${baseStyles} border-primary bg-primary/5 cursor-wait`;
      case "reject":
        return `${baseStyles} border-red-500 bg-red-500/5 animate-pulse`;
      case "accept":
        return `${baseStyles} border-green-500 bg-green-500/5 scale-[1.02]`;
      case "active":
        return `${baseStyles} border-primary bg-primary/5 scale-[1.01]`;
      default:
        return `${baseStyles} border-muted-foreground/25 hover:border-primary hover:bg-primary/5`;
    }
  };

  return (
    <div className="space-y-4">
      <motion.div
        className={getZoneStyles()}
        whileHover={!disabled && !isUploading ? { scale: 1.01 } : {}}
        whileTap={!disabled && !isUploading ? { scale: 0.99 } : {}}
      >
        <div {...getRootProps()}>
          <input {...getInputProps()} />

          <div className="space-y-4">
            {/* Icon */}
            <div className="flex justify-center">
              {isUploading ? (
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  className="p-3 bg-primary/10 rounded-full"
                >
                  <Loader2 className="w-8 h-8 text-primary" />
                </motion.div>
              ) : zoneState === "reject" ? (
                <div className="p-3 bg-red-500/10 rounded-full">
                  <AlertCircle className="w-8 h-8 text-red-500" />
                </div>
              ) : (
                <motion.div
                  animate={isDragActive ? { scale: [1, 1.1, 1] } : {}}
                  transition={{
                    duration: 0.5,
                    repeat: isDragActive ? Infinity : 0,
                  }}
                  className="p-3 bg-primary/10 rounded-full"
                >
                  <Upload className="w-8 h-8 text-primary" />
                </motion.div>
              )}
            </div>

            {/* Text */}
            <div className="space-y-2">
              {isUploading ? (
                <>
                  <h3 className="text-lg font-medium">Processing uploads...</h3>
                  <p className="text-sm text-muted-foreground">
                    {uploadQueue.length} file
                    {uploadQueue.length !== 1 ? "s" : ""} in queue
                  </p>
                </>
              ) : zoneState === "reject" ? (
                <>
                  <h3 className="text-lg font-medium text-red-600 dark:text-red-400">
                    Invalid files
                  </h3>
                  <p className="text-sm text-red-600 dark:text-red-400">
                    Only PDF files under 10MB are allowed
                  </p>
                </>
              ) : isDragActive ? (
                <>
                  <h3 className="text-lg font-medium text-primary">
                    Drop files here
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Release to start uploading
                  </p>
                </>
              ) : (
                <>
                  <h3 className="text-lg font-medium">
                    Drag & drop PDF resumes here
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    or click to browse files
                  </p>
                  <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
                    <FileText className="w-3 h-3" />
                    <span>
                      PDF only • Max 10MB each • Up to {maxFiles} files
                    </span>
                  </div>
                </>
              )}
            </div>

            {/* Browse Button */}
            {!isUploading && !disabled && !isDragActive && (
              <Button
                variant="outline"
                size="sm"
                className="mt-4"
                onClick={(e) => e.stopPropagation()}
              >
                Browse Files
              </Button>
            )}
          </div>
        </div>
      </motion.div>

      {isUploading && Object.keys(uploadProgress).length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-3"
        >
          <h4 className="text-sm font-medium">Upload Progress</h4>
          {Object.entries(uploadProgress).map(([filename, progress]) => (
            <div key={filename} className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="truncate flex-1 mr-2">{filename}</span>
                <span className="text-muted-foreground">{progress}%</span>
              </div>
              <Progress value={progress} className="h-1" />
            </div>
          ))}
        </motion.div>
      )}
    </div>
  );
}
