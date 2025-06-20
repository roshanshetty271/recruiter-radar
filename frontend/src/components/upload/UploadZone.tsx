"use client";

import React, { useCallback, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, FileText, AlertCircle, CheckCircle2 } from "lucide-react";
import { Button } from "../ui/button";

interface UploadZoneProps {
  onUpload: (files: File[]) => void;
  disabled?: boolean;
  remainingUploads: number;
}

type DropZoneState = "idle" | "dragging" | "dropped" | "processing";

export function UploadZone({
  onUpload,
  disabled = false,
  remainingUploads,
}: UploadZoneProps) {
  const [state, setState] = useState<DropZoneState>("idle");
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isDragActive, setIsDragActive] = useState(false);

  // File validation
  const validateFiles = useCallback(
    (files: File[]) => {
      const errors: string[] = [];

      // Check file count
      if (files.length > remainingUploads) {
        errors.push(`Too many files. You can upload ${remainingUploads} more.`);
      }

      // Check each file
      files.forEach((file, index) => {
        // Check file type
        if (file.type !== "application/pdf") {
          errors.push(`File ${index + 1}: Only PDF files are allowed`);
        }

        // Check file size (10MB limit)
        if (file.size > 10 * 1024 * 1024) {
          errors.push(`File ${index + 1}: File size must be less than 10MB`);
        }

        // Check filename
        if (!file.name.toLowerCase().endsWith(".pdf")) {
          errors.push(`File ${index + 1}: File must have .pdf extension`);
        }
      });

      return errors;
    },
    [remainingUploads]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragActive(false);
      setState("idle");
      setValidationError(null);

      const files = Array.from(e.dataTransfer.files);

      // Validate files
      const validationErrors = validateFiles(files);
      if (validationErrors.length > 0) {
        setValidationError(validationErrors.join("; "));
        return;
      }

      // Process files
      setState("dropped");
      setTimeout(() => {
        setState("processing");
        onUpload(files);

        // Reset state after a short delay
        setTimeout(() => {
          setState("idle");
        }, 500);
      }, 300);
    },
    [onUpload, validateFiles]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragActive(true);
    setState("dragging");
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    // Only set to false if we're leaving the drop zone entirely
    if (!e.currentTarget.contains(e.relatedTarget as Node)) {
      setIsDragActive(false);
      setState("idle");
    }
  }, []);

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files || []);

      // Validate files
      const validationErrors = validateFiles(files);
      if (validationErrors.length > 0) {
        setValidationError(validationErrors.join("; "));
        return;
      }

      // Process files
      setState("dropped");
      setTimeout(() => {
        setState("processing");
        onUpload(files);

        // Reset state after a short delay
        setTimeout(() => {
          setState("idle");
        }, 500);
      }, 300);

      // Reset input
      e.target.value = "";
    },
    [onUpload, validateFiles]
  );

  // Determine zone appearance
  const getZoneClasses = () => {
    if (disabled) {
      return "border-gray-600 bg-gray-800/30 cursor-not-allowed";
    }

    if (validationError) {
      return "border-red-500 bg-red-500/10 border-dashed animate-pulse";
    }

    if (isDragActive || state === "dragging") {
      return "border-purple-400 bg-purple-500/10 border-dashed scale-105";
    }

    if (state === "dropped") {
      return "border-green-400 bg-green-500/10 border-solid";
    }

    if (state === "processing") {
      return "border-blue-400 bg-blue-500/10 border-dashed";
    }

    return "border-gray-500 bg-gray-800/20 hover:border-purple-400 hover:bg-purple-500/5";
  };

  const getIconAndText = () => {
    if (disabled) {
      return {
        icon: <AlertCircle className="w-12 h-12 text-gray-500" />,
        title: "Upload Limit Reached",
        subtitle: "You've reached the maximum uploads for this session",
      };
    }

    if (state === "processing") {
      return {
        icon: (
          <div className="w-12 h-12 border-4 border-blue-400 border-t-transparent rounded-full animate-spin" />
        ),
        title: "Processing...",
        subtitle: "Your files are being uploaded",
      };
    }

    if (state === "dropped") {
      return {
        icon: <CheckCircle2 className="w-12 h-12 text-green-400" />,
        title: "Files Ready!",
        subtitle: "Starting upload process...",
      };
    }

    if (isDragActive) {
      return {
        icon: <Upload className="w-12 h-12 text-purple-400 animate-bounce" />,
        title: "Drop your files here",
        subtitle: "Release to start uploading",
      };
    }

    return {
      icon: <FileText className="w-12 h-12 text-gray-400" />,
      title: "Drag & drop PDF resumes",
      subtitle: `Or click to browse • ${remainingUploads} uploads remaining`,
    };
  };

  const { icon, title, subtitle } = getIconAndText();

  return (
    <div className="space-y-4">
      {/* Drop Zone */}
      <motion.div
        className={`
          relative border-2 rounded-xl p-8 text-center cursor-pointer
          transition-all duration-300 ease-out
          ${getZoneClasses()}
        `}
        whileHover={!disabled ? { scale: 1.02 } : {}}
        whileTap={!disabled ? { scale: 0.98 } : {}}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onClick={() =>
          !disabled && document.getElementById("file-input")?.click()
        }
      >
        {/* Hidden file input */}
        <input
          id="file-input"
          type="file"
          multiple
          accept=".pdf,application/pdf"
          onChange={handleFileSelect}
          className="hidden"
          disabled={disabled}
        />

        {/* Ripple Effect on Hover */}
        {isDragActive && (
          <motion.div
            className="absolute inset-0 rounded-xl bg-purple-400/20"
            initial={{ scale: 0, opacity: 0.8 }}
            animate={{ scale: 1.5, opacity: 0 }}
            transition={{ duration: 0.6, repeat: Infinity }}
          />
        )}

        <div className="relative z-10 space-y-4">
          {/* Icon */}
          <motion.div
            key={state}
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.2 }}
            className="flex justify-center"
          >
            {icon}
          </motion.div>

          {/* Text */}
          <div className="space-y-2">
            <motion.h3
              key={`title-${state}`}
              initial={{ y: 10, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.2, delay: 0.1 }}
              className="text-lg font-semibold text-white"
            >
              {title}
            </motion.h3>
            <motion.p
              key={`subtitle-${state}`}
              initial={{ y: 10, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.2, delay: 0.15 }}
              className="text-sm text-gray-400"
            >
              {subtitle}
            </motion.p>
          </div>

          {/* Browse Button */}
          {!disabled && state === "idle" && !isDragActive && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              onClick={(e) => e.stopPropagation()}
            >
              <Button
                variant="outline"
                className="mt-4 border-purple-500 text-purple-400 hover:bg-purple-500/10"
                onClick={() => document.getElementById("file-input")?.click()}
              >
                Browse Files
              </Button>
            </motion.div>
          )}
        </div>
      </motion.div>

      {/* Validation Error */}
      <AnimatePresence>
        {validationError && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg"
          >
            <div className="flex items-start space-x-2">
              <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-red-400">{validationError}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Upload Tips */}
      {!disabled && (
        <div className="text-xs text-gray-500 space-y-1">
          <p>• Supports PDF files up to 10MB each</p>
          <p>• Multiple files can be uploaded at once</p>
          <p>• AI will extract candidate information automatically</p>
        </div>
      )}
    </div>
  );
}
