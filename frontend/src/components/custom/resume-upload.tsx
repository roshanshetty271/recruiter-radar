"use client";

import React, { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useDropzone } from "react-dropzone";
import {
  Upload,
  FileText,
  CheckCircle,
  XCircle,
  Loader2,
  AlertCircle,
  Sparkles,
  Brain,
  X,
  Trophy,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { apiService } from "@/services/apiService";
import { useToast } from "@/components/ui/use-toast";
import { cn } from "@/lib/utils";
import confetti from "canvas-confetti";

interface BatchUploadResponse {
  summary: string;
  stats: {
    total_files: number;
    successful: number;
    new_candidates: number;
    duplicates_updated: number;
    failed: number;
    processing_time_seconds: number;
  };
  added: { candidate_id: string; name: string; email?: string }[];
  updated: { candidate_id: string; name: string; email?: string }[];
  failed: { file_name: string; error: string; message?: string }[];
}

interface ProcessingFile {
  id: string;
  name: string;
  size: number;
  status:
    | "pending"
    | "parsing"
    | "extracting"
    | "embedding"
    | "completed"
    | "error";
  progress: number;
  extractedName?: string;
  extractedEmail?: string;
  extractedSkills?: string[];
  candidateId?: string;
  error?: string;
  retryCount?: number;
}

const AI_INSIGHTS = [
  "🧠 Extracting candidate skills and experience...",
  "✨ Analyzing professional background...",
  "🎯 Generating searchable embeddings...",
  "🔍 Identifying key competencies...",
  "💼 Processing work history...",
  "🎓 Parsing education details...",
];

export function ResumeUpload({
  onUploadComplete,
}: {
  onUploadComplete?: () => void;
}) {
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingFiles, setProcessingFiles] = useState<ProcessingFile[]>([]);
  const [progress, setProgress] = useState(0);
  const [uploadComplete, setUploadComplete] = useState(false);
  const [uploadResults, setUploadResults] =
    useState<BatchUploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [candidateName, setCandidateName] = useState("");
  const [currentInsight, setCurrentInsight] = useState(0);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  const MAX_FILES = 10;
  const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

  // Cycle through AI insights during processing
  React.useEffect(() => {
    if (!isProcessing) return;

    const interval = setInterval(() => {
      setCurrentInsight((prev) => (prev + 1) % AI_INSIGHTS.length);
    }, 2000);

    return () => clearInterval(interval);
  }, [isProcessing]);

  const validateFiles = (
    files: File[]
  ): { valid: File[]; errors: string[] } => {
    const valid: File[] = [];
    const errors: string[] = [];

    files.slice(0, MAX_FILES).forEach((file) => {
      const ext = file.name.split(".").pop()?.toLowerCase();
      if (!["pdf", "docx", "doc", "txt"].includes(ext || "")) {
        errors.push(`${file.name}: Invalid file type (use PDF, DOCX, or TXT)`);
      } else if (file.size > MAX_FILE_SIZE) {
        errors.push(`${file.name}: File too large (max 10MB)`);
      } else {
        valid.push(file);
      }
    });

    if (files.length > MAX_FILES) {
      errors.push(`Only first ${MAX_FILES} files will be processed`);
    }

    return { valid, errors };
  };

  const handleFileSelect = useCallback(
    async (acceptedFiles: File[]) => {
      const { valid, errors } = validateFiles(acceptedFiles);

      if (errors.length > 0) {
        setError(errors.join("\n"));
        setTimeout(() => setError(null), 5000);
      }

      if (valid.length === 0) return;

      setIsProcessing(true);
      setUploadComplete(false);
      setUploadResults(null);
      setProgress(0);
      setCurrentInsight(0);

      const files: ProcessingFile[] = valid.map((file, index) => ({
        id: `${file.name}-${Date.now()}-${index}`,
        name: file.name,
        size: file.size,
        status: "pending" as const,
        progress: 0,
        retryCount: 0,
      }));

      setProcessingFiles(files);

      try {
        const uploadResponse = await apiService.uploadBatch(valid);
        const taskId = uploadResponse.task_id;

        // Start polling
        const pollInterval = setInterval(async () => {
          try {
            const status = await apiService.getBatchStatus(taskId);
            setProgress(status.progress || 0);

            if (status.status === "completed") {
              clearInterval(pollInterval);
              setUploadResults(status);
              // Map results to files similar to before
              setProcessingFiles((prev) =>
                prev.map((file) => {
                  const failedFile = status.failed.find(
                    (f) => f.file_name === file.name
                  );
                  if (failedFile) {
                    return {
                      ...file,
                      status: "error",
                      progress: 100,
                      error: failedFile.message,
                    };
                  }
                  // Assume added or updated
                  const candidate = [...status.added, ...status.updated].find(
                    (c) =>
                      file.name
                        .toLowerCase()
                        .includes(c.name.toLowerCase().split(" ")[0])
                  );
                  return {
                    ...file,
                    status: "completed",
                    progress: 100,
                    candidateId: candidate?.candidate_id,
                    extractedName: candidate?.name,
                    extractedEmail: candidate?.email,
                  };
                })
              );
              setUploadComplete(true);
              // confetti and toast as before, using status.stats
            } else if (status.status === "failed") {
              clearInterval(pollInterval);
              setError(status.error);
              // Mark all files error
            }
          } catch (err) {
            clearInterval(pollInterval);
            setError("Failed to get status");
          }
        }, 2000);
      } catch (err) {
        // error handling
      } finally {
        setTimeout(() => setIsProcessing(false), 1500);
      }
    },
    [onUploadComplete, toast]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: handleFileSelect,
    accept: {
      "application/pdf": [".pdf"],
      "application/msword": [".doc"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        [".docx"],
      "text/plain": [".txt"],
    },
    maxFiles: MAX_FILES,
    multiple: true,
    noClick: true, // We'll handle clicks manually
  });

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const resetComponent = () => {
    setIsProcessing(false);
    setProcessingFiles([]);
    setProgress(0);
    setUploadComplete(false);
    setUploadResults(null);
    setError(null);
    setCandidateName("");
  };

  const retryFailedFile = async (fileId: string) => {
    const file = processingFiles.find((f) => f.id === fileId);
    if (!file || file.status !== "error") return;

    // Find the original File object - we need to store it
    // For now, we'll show a toast that retry needs re-upload
    toast({
      title: "Retry Feature",
      description:
        "Please re-upload the failed file. Individual retry coming soon!",
    });
  };

  return (
    <div className="w-full max-w-2xl mx-auto space-y-6">
      <AnimatePresence mode="wait">
        {!isProcessing && !uploadComplete ? (
          <motion.div
            key="upload"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="space-y-6"
          >
            <Card className="bg-gray-900/50 border-gray-700">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-white">
                  <Upload className="w-5 h-5" />
                  Upload Resumes
                </CardTitle>
                <CardDescription className="text-gray-400">
                  Upload up to 10 resume files (PDF, DOCX, or TXT) to
                  automatically extract candidate information and add them to
                  your searchable database.
                </CardDescription>
              </CardHeader>

              <CardContent className="space-y-4">
                {/* Optional candidate name input */}
                <div>
                  <Label htmlFor="candidateName" className="text-gray-300">
                    Candidate Name Override (optional)
                  </Label>
                  <Input
                    id="candidateName"
                    value={candidateName}
                    onChange={(e) => setCandidateName(e.target.value)}
                    placeholder="Override extracted name if needed"
                    className="bg-gray-800 border-gray-600 text-white placeholder-gray-400"
                  />
                </div>

                {/* Enhanced drop zone */}
                <div
                  {...getRootProps()}
                  onClick={handleClick}
                  className={cn(
                    "relative rounded-xl border-2 border-dashed p-12 text-center transition-all duration-300 cursor-pointer group",
                    isDragActive
                      ? "border-purple-500 bg-purple-500/10 scale-[1.02] shadow-lg shadow-purple-500/20"
                      : "border-gray-700 hover:border-purple-500/50 hover:bg-gray-800/50"
                  )}
                >
                  <input
                    {...getInputProps()}
                    ref={fileInputRef}
                    className="hidden"
                  />

                  <div className="space-y-6">
                    {/* Animated upload icon */}
                    <motion.div
                      animate={
                        isDragActive
                          ? { scale: 1.1, rotate: 5 }
                          : { scale: 1, rotate: 0 }
                      }
                      transition={{ type: "spring", damping: 10 }}
                      className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-blue-500/20 to-purple-500/20 group-hover:from-blue-500/30 group-hover:to-purple-500/30 transition-all duration-300"
                    >
                      <Upload className="h-10 w-10 text-purple-500" />
                    </motion.div>

                    <div>
                      <p className="text-lg font-medium text-white mb-2">
                        {isDragActive
                          ? "Drop your resumes here!"
                          : "Drop resumes here or click to browse"}
                      </p>
                      <p className="text-sm text-gray-400">
                        Support for PDF, DOC, DOCX, TXT • Max 10 files • 10MB
                        each
                      </p>
                    </div>

                    {/* Explicit browse button */}
                    <Button
                      type="button"
                      variant="outline"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleClick();
                      }}
                      className="border-purple-500/50 text-purple-400 hover:bg-purple-500/10 hover:border-purple-500"
                    >
                      <FileText className="mr-2 h-4 w-4" />
                      Select Files
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Error Display */}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <Alert className="bg-red-900/50 border-red-700">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription className="text-red-200 whitespace-pre-line">
                    <div className="flex justify-between items-start">
                      <span>{error}</span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setError(null)}
                        className="text-red-200 hover:text-white p-1 ml-2"
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                  </AlertDescription>
                </Alert>
              </motion.div>
            )}
          </motion.div>
        ) : isProcessing ? (
          <motion.div
            key="processing"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="rounded-xl border border-gray-800 bg-gray-900/50 backdrop-blur-sm p-8"
          >
            <div className="space-y-6">
              {/* Animated header */}
              <div className="text-center">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                  className="inline-block mb-4"
                >
                  <Sparkles className="h-8 w-8 text-purple-500" />
                </motion.div>
                <h3 className="text-xl font-semibold text-white">
                  Processing {processingFiles.length} Resume
                  {processingFiles.length > 1 ? "s" : ""}
                </h3>
                <p className="text-sm text-gray-400 mt-2">
                  AI is working its magic on your files...
                </p>
              </div>

              {/* Enhanced progress bar with gradient */}
              <div className="relative h-3 bg-gray-800 rounded-full overflow-hidden">
                <motion.div
                  className="absolute top-0 left-0 h-full bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 rounded-full"
                  initial={{ width: "0%" }}
                  animate={{
                    width: `${Math.max(
                      10,
                      Math.min(
                        95,
                        Object.values(processingFiles).reduce(
                          (acc, file) => acc + file.progress,
                          0
                        ) / processingFiles.length
                      )
                    )}%`,
                  }}
                  transition={{ duration: 0.5 }}
                />
                {/* Animated shimmer effect */}
                <motion.div
                  className="absolute top-0 left-0 h-full w-20 bg-gradient-to-r from-transparent via-white/20 to-transparent rounded-full"
                  animate={{ x: [-80, 400] }}
                  transition={{
                    duration: 1.5,
                    repeat: Infinity,
                    ease: "easeInOut",
                  }}
                />
              </div>

              {/* Enhanced file processing cards with candidate previews */}
              <div className="space-y-3 max-h-[400px] overflow-y-auto">
                {processingFiles.map((file, index) => (
                  <motion.div
                    key={file.id}
                    initial={{ x: -20, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    transition={{ delay: index * 0.1 }}
                    className={cn(
                      "rounded-lg transition-all border",
                      file.status === "completed"
                        ? "bg-green-500/10 border-green-500/30 shadow-lg shadow-green-500/10"
                        : file.status === "error"
                        ? "bg-red-500/10 border-red-500/30"
                        : "bg-gray-800/50 border-gray-700"
                    )}
                  >
                    <div className="p-4">
                      {/* Main file info row */}
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3 flex-1">
                          <div className="relative">
                            <FileText className="h-5 w-5 text-gray-400" />
                            {file.status === "parsing" && (
                              <motion.div
                                className="absolute inset-0 flex items-center justify-center"
                                animate={{ rotate: 360 }}
                                transition={{
                                  duration: 1,
                                  repeat: Infinity,
                                  ease: "linear",
                                }}
                              >
                                <Loader2 className="h-5 w-5 text-blue-500" />
                              </motion.div>
                            )}
                            {file.status === "extracting" && (
                              <motion.div
                                className="absolute inset-0 flex items-center justify-center"
                                animate={{ scale: [1, 1.2, 1] }}
                                transition={{ duration: 1, repeat: Infinity }}
                              >
                                <Brain className="h-5 w-5 text-purple-500" />
                              </motion.div>
                            )}
                            {file.status === "embedding" && (
                              <motion.div
                                className="absolute inset-0 flex items-center justify-center"
                                animate={{ rotate: 360 }}
                                transition={{
                                  duration: 2,
                                  repeat: Infinity,
                                  ease: "linear",
                                }}
                              >
                                <Sparkles className="h-5 w-5 text-indigo-500" />
                              </motion.div>
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-white truncate">
                              {file.name}
                            </p>
                            <p className="text-xs text-gray-400">
                              {(file.size / 1024).toFixed(1)} KB • {file.status}
                              {file.retryCount &&
                                file.retryCount > 0 &&
                                ` • Retry ${file.retryCount}`}
                            </p>
                          </div>
                        </div>

                        {/* Status indicators and actions */}
                        <div className="flex items-center gap-2">
                          {file.status === "completed" && (
                            <motion.div
                              initial={{ scale: 0 }}
                              animate={{ scale: 1 }}
                              transition={{ type: "spring", damping: 10 }}
                            >
                              <CheckCircle className="h-5 w-5 text-green-500" />
                            </motion.div>
                          )}
                          {file.status === "error" && (
                            <>
                              <XCircle className="h-5 w-5 text-red-500" />
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => retryFailedFile(file.id)}
                                className="ml-2 h-6 px-2 text-xs border-red-500/50 text-red-400 hover:bg-red-500/10"
                              >
                                Retry
                              </Button>
                            </>
                          )}
                          {["parsing", "extracting", "embedding"].includes(
                            file.status
                          ) && (
                            <motion.div
                              animate={{ opacity: [0.5, 1, 0.5] }}
                              transition={{ repeat: Infinity, duration: 1.5 }}
                              className="text-xs text-purple-400 font-medium min-w-[2rem] text-right"
                            >
                              {Math.round(file.progress)}%
                            </motion.div>
                          )}
                        </div>
                      </div>

                      {/* Candidate preview (show extracted info if available) */}
                      {(file.extractedName ||
                        file.extractedEmail ||
                        file.extractedSkills ||
                        file.error) && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          transition={{ duration: 0.3 }}
                          className="mt-3 pt-3 border-t border-gray-700/50"
                        >
                          {file.status === "error" && file.error ? (
                            <div className="flex items-start gap-2">
                              <AlertCircle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                              <p className="text-xs text-red-300">
                                {file.error}
                              </p>
                            </div>
                          ) : (
                            <div className="space-y-1">
                              {file.extractedName && (
                                <motion.div
                                  initial={{ x: -10, opacity: 0 }}
                                  animate={{ x: 0, opacity: 1 }}
                                  className="flex items-center gap-2"
                                >
                                  <span className="text-xs text-gray-500">
                                    👤
                                  </span>
                                  <span className="text-xs text-green-400">
                                    {file.extractedName}
                                  </span>
                                </motion.div>
                              )}
                              {file.extractedEmail && (
                                <motion.div
                                  initial={{ x: -10, opacity: 0 }}
                                  animate={{ x: 0, opacity: 1 }}
                                  transition={{ delay: 0.1 }}
                                  className="flex items-center gap-2"
                                >
                                  <span className="text-xs text-gray-500">
                                    📧
                                  </span>
                                  <span className="text-xs text-blue-400">
                                    {file.extractedEmail}
                                  </span>
                                </motion.div>
                              )}
                              {file.extractedSkills &&
                                file.extractedSkills.length > 0 && (
                                  <motion.div
                                    initial={{ x: -10, opacity: 0 }}
                                    animate={{ x: 0, opacity: 1 }}
                                    transition={{ delay: 0.2 }}
                                    className="flex items-center gap-2"
                                  >
                                    <span className="text-xs text-gray-500">
                                      🎯
                                    </span>
                                    <span className="text-xs text-purple-400">
                                      {file.extractedSkills
                                        .slice(0, 3)
                                        .join(", ")}
                                      {file.extractedSkills.length > 3 && "..."}
                                    </span>
                                  </motion.div>
                                )}
                            </div>
                          )}
                        </motion.div>
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>

              {/* Cycling AI insights */}
              <motion.div
                key={currentInsight}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.5 }}
                className="flex items-center justify-center gap-2 text-sm text-gray-400"
              >
                <Brain className="h-4 w-4" />
                <span>{AI_INSIGHTS[currentInsight]}</span>
              </motion.div>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="complete"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            {/* Success Header */}
            <div className="text-center rounded-xl border border-gray-800 bg-gray-900/50 p-8">
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: "spring", damping: 10 }}
                className="mb-6"
              >
                <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-green-500/20 to-emerald-500/20 mb-4">
                  {uploadResults?.stats.failed &&
                  uploadResults.stats.failed > 0 ? (
                    <AlertCircle className="h-12 w-12 text-yellow-500" />
                  ) : (
                    <CheckCircle className="h-12 w-12 text-green-500" />
                  )}
                </div>
              </motion.div>

              <h3 className="text-2xl font-semibold text-white mb-2">
                {uploadResults?.stats.failed && uploadResults.stats.failed > 0
                  ? "⚠️ Partially Complete!"
                  : "🎉 All Resumes Processed!"}
              </h3>
              <p className="text-gray-400 mb-6">
                {uploadResults?.summary ||
                  `${
                    processingFiles.filter((f) => f.status === "completed")
                      .length
                  } candidates added to your talent pool`}
              </p>

              {/* Detailed Stats Grid */}
              {uploadResults && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                  className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6"
                >
                  <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4">
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: 0.3, type: "spring" }}
                      className="text-2xl font-bold text-green-400"
                    >
                      {uploadResults.stats.new_candidates}
                    </motion.div>
                    <div className="text-xs text-gray-400">New Candidates</div>
                  </div>

                  <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: 0.4, type: "spring" }}
                      className="text-2xl font-bold text-blue-400"
                    >
                      {uploadResults.stats.duplicates_updated}
                    </motion.div>
                    <div className="text-xs text-gray-400">Updated</div>
                  </div>

                  <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: 0.5, type: "spring" }}
                      className="text-2xl font-bold text-red-400"
                    >
                      {uploadResults.stats.failed}
                    </motion.div>
                    <div className="text-xs text-gray-400">Failed</div>
                  </div>

                  <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-4">
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: 0.6, type: "spring" }}
                      className="text-2xl font-bold text-purple-400"
                    >
                      {uploadResults.stats.processing_time_seconds.toFixed(1)}s
                    </motion.div>
                    <div className="text-xs text-gray-400">Total Time</div>
                  </div>
                </motion.div>
              )}

              <div className="flex gap-3 justify-center">
                <Button
                  onClick={() => (window.location.href = "/")}
                  className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                >
                  <Trophy className="mr-2 h-4 w-4" />
                  Search New Candidates
                </Button>
                <Button
                  variant="outline"
                  onClick={resetComponent}
                  className="border-gray-600 text-gray-300 hover:bg-gray-800"
                >
                  Upload More Resumes
                </Button>
              </div>
            </div>

            {/* Detailed Results Breakdown */}
            {uploadResults &&
              (uploadResults.added.length > 0 ||
                uploadResults.updated.length > 0 ||
                uploadResults.failed.length > 0) && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                  className="rounded-xl border border-gray-800 bg-gray-900/50 p-6"
                >
                  <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <FileText className="h-5 w-5" />
                    Detailed Results
                  </h4>

                  <div className="space-y-4">
                    {/* New Candidates */}
                    {uploadResults.added.length > 0 && (
                      <div>
                        <h5 className="text-sm font-medium text-green-400 mb-2">
                          ✅ New Candidates Added ({uploadResults.added.length})
                        </h5>
                        <div className="space-y-2">
                          {uploadResults.added.map((candidate, index) => (
                            <motion.div
                              key={candidate.candidate_id}
                              initial={{ x: -20, opacity: 0 }}
                              animate={{ x: 0, opacity: 1 }}
                              transition={{ delay: 0.5 + index * 0.1 }}
                              className="flex items-center gap-3 p-3 bg-green-500/5 border border-green-500/20 rounded-lg"
                            >
                              <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
                              <div className="flex-1">
                                <p className="text-sm font-medium text-white">
                                  {candidate.name}
                                </p>
                                {candidate.email && (
                                  <p className="text-xs text-gray-400">
                                    {candidate.email}
                                  </p>
                                )}
                              </div>
                              <span className="text-xs text-green-400 bg-green-500/10 px-2 py-1 rounded">
                                New
                              </span>
                            </motion.div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Updated Candidates */}
                    {uploadResults.updated.length > 0 && (
                      <div>
                        <h5 className="text-sm font-medium text-blue-400 mb-2">
                          🔄 Candidates Updated ({uploadResults.updated.length})
                        </h5>
                        <div className="space-y-2">
                          {uploadResults.updated.map((candidate, index) => (
                            <motion.div
                              key={candidate.candidate_id}
                              initial={{ x: -20, opacity: 0 }}
                              animate={{ x: 0, opacity: 1 }}
                              transition={{ delay: 0.6 + index * 0.1 }}
                              className="flex items-center gap-3 p-3 bg-blue-500/5 border border-blue-500/20 rounded-lg"
                            >
                              <CheckCircle className="h-4 w-4 text-blue-500 flex-shrink-0" />
                              <div className="flex-1">
                                <p className="text-sm font-medium text-white">
                                  {candidate.name}
                                </p>
                                {candidate.email && (
                                  <p className="text-xs text-gray-400">
                                    {candidate.email}
                                  </p>
                                )}
                              </div>
                              <span className="text-xs text-blue-400 bg-blue-500/10 px-2 py-1 rounded">
                                Updated
                              </span>
                            </motion.div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Failed Files */}
                    {uploadResults.failed.length > 0 && (
                      <div>
                        <h5 className="text-sm font-medium text-red-400 mb-2">
                          ❌ Failed Uploads ({uploadResults.failed.length})
                        </h5>
                        <div className="space-y-2">
                          {uploadResults.failed.map((failedFile, index) => (
                            <motion.div
                              key={failedFile.file_name}
                              initial={{ x: -20, opacity: 0 }}
                              animate={{ x: 0, opacity: 1 }}
                              transition={{ delay: 0.7 + index * 0.1 }}
                              className="flex items-start gap-3 p-3 bg-red-500/5 border border-red-500/20 rounded-lg"
                            >
                              <XCircle className="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" />
                              <div className="flex-1">
                                <p className="text-sm font-medium text-white">
                                  {failedFile.file_name}
                                </p>
                                <p className="text-xs text-red-300">
                                  {failedFile.error || failedFile.message}
                                </p>
                              </div>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() =>
                                  retryFailedFile(failedFile.file_name)
                                }
                                className="h-6 px-2 text-xs border-red-500/50 text-red-400 hover:bg-red-500/10"
                              >
                                Retry
                              </Button>
                            </motion.div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
