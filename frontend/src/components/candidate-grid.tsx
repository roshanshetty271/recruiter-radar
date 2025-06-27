"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  MapPin,
  Star,
  MessageCircle,
  Bookmark,
  CheckCircle,
  ExternalLink,
  ContrastIcon as Versus,
  Brain,
  Target,
  Zap,
  Sparkles,
  TrendingUp,
  ChevronDown,
  ChevronUp,
  Download,
} from "lucide-react";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Progress } from "./ui/progress";
import { Separator } from "./ui/separator";
import { useToast } from "../hooks/use-toast";
import type { FrontendCandidate } from "../lib/types";

interface Candidate {
  id: string;
  name: string;
  title: string;
  location: string;
  distance?: string;
  matchScore: number;
  experience: number | undefined;
  skills: string[];
  isOnline: boolean;
  isVerified: boolean;
  avatar: string;
  visaStatus?: string;
  githubUrl?: string;
  linkedinUrl?: string;
  isDemo?: boolean;
}

// CSV Export utility function
const exportToCsv = (candidates: Candidate[], searchQuery: string) => {
  // Prepare CSV headers
  const headers = [
    "Name",
    "Title",
    "Skills",
    "Location",
    "Experience (Years)",
    "Visa Status",
    "GitHub URL",
    "LinkedIn URL",
    "Match Score",
    "Candidate Type",
  ];

  // Prepare CSV rows
  const rows = candidates.map((candidate) => [
    candidate.name || "",
    candidate.title || "",
    candidate.skills?.join("; ") || "",
    candidate.location || "",
    candidate.experience?.toString() || "",
    candidate.visaStatus || "",
    candidate.githubUrl || "",
    candidate.linkedinUrl || "",
    candidate.matchScore?.toString() || "",
    candidate.id?.startsWith("upload_") ? "Your Upload" : "Demo",
  ]);

  // Create CSV content
  const csvContent = [
    headers.join(","),
    ...rows.map((row) =>
      row
        .map((field) =>
          typeof field === "string" &&
          (field.includes(",") || field.includes('"'))
            ? `"${field}"`
            : field
        )
        .join(",")
    ),
  ].join("\n");

  // Download file
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);
  link.setAttribute("href", url);

  // Generate filename with timestamp and search query
  const timestamp = new Date().toISOString().split("T")[0];
  const sanitizedQuery = searchQuery
    .replace(/[^a-z0-9]/gi, "_")
    .substring(0, 20);
  const filename = `recruiter_radar_${
    sanitizedQuery || "search"
  }_${timestamp}.csv`;

  link.setAttribute("download", filename);
  link.style.visibility = "hidden";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

export function CandidateGrid({
  candidates,
  isLoading,
  searchQuery = "", // 🔥 NEW
  onGenerateOutreach, // 🔥 NEW
}: {
  candidates: Candidate[];
  isLoading: boolean;
  searchQuery?: string; // 🔥 NEW
  onGenerateOutreach?: (candidateId: string) => void; // 🔥 NEW
}) {
  const { toast } = useToast();
  const [savedCandidates, setSavedCandidates] = useState<Set<string>>(
    new Set()
  );
  const [comparisonCandidates, setComparisonCandidates] = useState<Candidate[]>(
    []
  );
  const [showComparison, setShowComparison] = useState(false);

  const toggleSave = (candidateId: string) => {
    const newSaved = new Set(savedCandidates);
    if (newSaved.has(candidateId)) {
      newSaved.delete(candidateId);
    } else {
      newSaved.add(candidateId);
    }
    setSavedCandidates(newSaved);
  };

  const addToComparison = (candidate: Candidate) => {
    if (
      comparisonCandidates.length < 3 &&
      !comparisonCandidates.find((c) => c.id === candidate.id)
    ) {
      setComparisonCandidates([...comparisonCandidates, candidate]);
    }
  };

  const removeFromComparison = (candidateId: string) => {
    setComparisonCandidates(
      comparisonCandidates.filter((c) => c.id !== candidateId)
    );
  };

  const clearComparison = () => {
    setComparisonCandidates([]);
    setShowComparison(false);
  };

  const handleExportCsv = () => {
    if (candidates.length === 0) {
      toast({
        title: "No data to export",
        description: "Please search for candidates first before exporting.",
        variant: "destructive",
      });
      return;
    }

    try {
      exportToCsv(candidates, searchQuery);
      toast({
        title: "📊 Export successful!",
        description: `Exported ${candidates.length} candidate${
          candidates.length !== 1 ? "s" : ""
        } to CSV`,
      });
    } catch (error) {
      console.error("CSV export error:", error);
      toast({
        title: "Export failed",
        description: "There was an error exporting the data. Please try again.",
        variant: "destructive",
      });
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-center py-8">
          <div className="text-center space-y-4">
            <div className="w-16 h-16 border-4 border-purple-400 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-gray-400">🧠 AI analyzing candidates...</p>
          </div>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} delay={i * 50} />
          ))}
        </div>
      </div>
    );
  }

  if (candidates.length === 0) {
    return (
      <div className="text-center py-16 space-y-6">
        <div className="w-24 h-24 mx-auto bg-gray-800 rounded-full flex items-center justify-center">
          <Star className="w-12 h-12 text-gray-600" />
        </div>
        <div className="space-y-2">
          <h3 className="text-xl font-semibold text-white">
            No candidates found
          </h3>
          <p className="text-gray-400">
            Try adjusting your search criteria or filters
          </p>
        </div>
        <Button
          variant="outline"
          className="border-white/20 text-white hover:bg-white/10"
        >
          Clear Filters
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 🔥 NEW: Enhanced Results Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h2 className="text-lg font-semibold text-white flex items-center space-x-2">
            <Brain className="w-5 h-5 text-purple-400" />
            <span>Found {candidates.length} AI-matched candidates</span>
          </h2>
          {searchQuery && (
            <div className="text-sm text-gray-400 bg-gray-800/50 px-3 py-1 rounded-full">
              for "{searchQuery}"
            </div>
          )}
        </div>

        {comparisonCandidates.length > 0 && (
          <div className="text-sm text-purple-400 bg-purple-500/10 px-3 py-1 rounded-full border border-purple-400/20">
            {comparisonCandidates.length}/3 selected for comparison
          </div>
        )}
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Comparison Bar */}
        {comparisonCandidates.length > 0 && (
          <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 z-40">
            <ComparisonBar
              candidates={comparisonCandidates}
              onRemove={removeFromComparison}
              onCompare={() => setShowComparison(true)}
              onClear={clearComparison}
            />
          </div>
        )}

        {/* Comparison Modal */}
        <CandidateComparison
          candidates={comparisonCandidates}
          isOpen={showComparison}
          onClose={() => setShowComparison(false)}
          onRemove={removeFromComparison}
        />

        {candidates.map((candidate, index) => (
          <CandidateCard
            key={candidate.id}
            candidate={candidate}
            searchQuery={searchQuery} // 🔥 NEW
            isSaved={savedCandidates.has(candidate.id)}
            onToggleSave={() => toggleSave(candidate.id)}
            onAddToComparison={() => addToComparison(candidate)}
            onGenerateOutreach={() => onGenerateOutreach?.(candidate.id)} // �� NEW
            isInComparison={comparisonCandidates.some(
              (c) => c.id === candidate.id
            )}
            delay={index * 50}
          />
        ))}
      </div>

      <div className="mt-6">
        <Button
          variant="outline"
          className="w-full border-white/20 text-white hover:bg-white/10 group"
          onClick={handleExportCsv}
        >
          <span>Export to CSV</span>
          <Download className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
        </Button>
      </div>
    </div>
  );
}

// 🔥 ENHANCED: Your existing CandidateCard with AI intelligence
function CandidateCard({
  candidate,
  searchQuery = "", // 🔥 NEW
  isSaved,
  onToggleSave,
  onAddToComparison,
  onGenerateOutreach, // 🔥 NEW
  isInComparison,
  delay,
}: {
  candidate: Candidate;
  searchQuery?: string; // 🔥 NEW
  isSaved: boolean;
  onToggleSave: () => void;
  onAddToComparison: () => void;
  onGenerateOutreach?: () => void; // 🔥 NEW
  isInComparison: boolean;
  delay: number;
}) {
  const [isHovered, setIsHovered] = useState(false);
  const [showAIAnalysis, setShowAIAnalysis] = useState(false); // 🔥 NEW

  // 🧠 NEW: Generate AI match analysis
  const generateMatchAnalysis = () => {
    const queryWords = searchQuery
      .toLowerCase()
      .split(" ")
      .filter((word) => word.length > 2);
    const skillsLower = candidate.skills.map((s) => s.toLowerCase());

    const matchedSkills = candidate.skills.filter((skill) =>
      queryWords.some((word) => skill.toLowerCase().includes(word))
    );

    const matchReasons: string[] = [];

    if (matchedSkills.length > 0) {
      matchReasons.push(
        `🎯 ${matchedSkills.length} skill match${
          matchedSkills.length > 1 ? "es" : ""
        }: ${matchedSkills.slice(0, 3).join(", ")}`
      );
    }

    if ((candidate.experience ?? 0) >= 5) {
      matchReasons.push(`⭐ Senior-level (${candidate.experience ?? 0} years)`);
    }

    if (candidate.isVerified) {
      matchReasons.push(`✅ Verified profile`);
    }

    if (candidate.isOnline) {
      matchReasons.push(`🟢 Currently active`);
    }

    return {
      matchedSkills,
      matchReasons,
      confidenceScore: Math.min(
        100,
        candidate.matchScore + matchedSkills.length * 10
      ),
    };
  };

  // 🎨 NEW: Get skill relevance color
  const getSkillRelevance = (skill: string) => {
    const queryWords = searchQuery.toLowerCase().split(" ");
    const skillLower = skill.toLowerCase();
    return queryWords.some((word) => skillLower.includes(word)) ? 95 : 60;
  };

  const matchAnalysis = generateMatchAnalysis();

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: delay / 1000 }}
      className="group relative w-full h-auto min-h-[400px] rounded-xl overflow-hidden cursor-pointer transform transition-all duration-300 hover:scale-102 hover:shadow-2xl hover:shadow-purple-500/25"
      style={{
        background: "rgba(255,255,255,0.05)",
        backdropFilter: "blur(12px)",
        border: "1px solid rgba(255,255,255,0.1)",
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Gradient border animation */}
      <div className="absolute inset-0 bg-gradient-to-r from-purple-500/50 to-blue-500/50 opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-xl" />
      <div className="absolute inset-[1px] bg-gray-900/90 rounded-xl" />

      <div className="relative p-6 h-full flex flex-col space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            <div className="relative">
              <img
                src={candidate.avatar || "/placeholder.svg"}
                alt={candidate.name}
                className="w-12 h-12 rounded-full object-cover"
              />
              {candidate.isOnline && (
                <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-green-400 rounded-full border-2 border-gray-900 animate-pulse" />
              )}
            </div>

            <div>
              <div className="flex items-center space-x-1">
                <h3 className="font-semibold text-white">{candidate.name}</h3>
                {candidate.isVerified && (
                  <CheckCircle className="w-4 h-4 text-blue-400" />
                )}
                {matchAnalysis.confidenceScore >= 90 && (
                  <Sparkles className="w-4 h-4 text-yellow-400" />
                )}
              </div>

              <div className="flex items-center gap-2">
                <p className="text-sm text-gray-400 truncate">
                  {candidate.title}
                </p>
                {/* Upload Type Badge */}
                <Badge
                  variant={
                    candidate.id?.startsWith("upload_") ? "default" : "outline"
                  }
                  className={
                    candidate.id?.startsWith("upload_")
                      ? "bg-green-600 hover:bg-green-700 text-white text-xs px-2 py-0.5"
                      : "border-purple-500/30 text-purple-400 text-xs px-2 py-0.5"
                  }
                >
                  {candidate.id?.startsWith("upload_")
                    ? "📄 Your Upload"
                    : "🎯 Demo"}
                </Badge>
              </div>
            </div>
          </div>

          {/* Enhanced Match Score */}
          <div className="relative w-12 h-12">
            <svg className="w-12 h-12 transform -rotate-90">
              <defs>
                <linearGradient
                  id={`gradient-${candidate.id}`}
                  x1="0%"
                  y1="0%"
                  x2="100%"
                  y2="0%"
                >
                  <stop offset="0%" stopColor="#8b5cf6" />
                  <stop offset="100%" stopColor="#3b82f6" />
                </linearGradient>
              </defs>
              <circle
                cx="24"
                cy="24"
                r="20"
                stroke="rgba(255,255,255,0.1)"
                strokeWidth="3"
                fill="none"
              />
              <circle
                cx="24"
                cy="24"
                r="20"
                stroke={`url(#gradient-${candidate.id})`}
                strokeWidth="3"
                fill="none"
                strokeDasharray={`${candidate.matchScore * 1.26} 126`}
                className="transition-all duration-1000"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-xs font-bold text-white">
                {candidate.matchScore}%
              </span>
            </div>
          </div>
        </div>

        {/* 🧠 NEW: AI Analysis Toggle */}
        {searchQuery && (
          <div className="flex items-center justify-between">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowAIAnalysis(!showAIAnalysis)}
              className="text-purple-400 hover:text-purple-300 h-6 px-2 text-xs"
            >
              <Brain className="w-3 h-3 mr-1" />
              AI Analysis
              {showAIAnalysis ? (
                <ChevronUp className="w-3 h-3 ml-1" />
              ) : (
                <ChevronDown className="w-3 h-3 ml-1" />
              )}
            </Button>
            <div className="flex items-center space-x-1">
              <Target className="w-3 h-3 text-green-400" />
              <span className="text-xs text-green-400 font-medium">
                {matchAnalysis.confidenceScore}% confidence
              </span>
            </div>
          </div>
        )}

        {/* 🔥 NEW: AI Analysis Panel */}
        <AnimatePresence>
          {showAIAnalysis && searchQuery && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="bg-gradient-to-r from-purple-500/10 to-blue-500/10 rounded-lg p-3 border border-purple-400/20"
            >
              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <Brain className="w-3 h-3 text-purple-400" />
                  <span className="text-xs font-semibold text-purple-200">
                    Match Intelligence
                  </span>
                  <Progress
                    value={matchAnalysis.confidenceScore}
                    className="w-12 h-1"
                  />
                </div>

                {matchAnalysis.matchReasons.length > 0 && (
                  <div className="space-y-1">
                    {matchAnalysis.matchReasons
                      .slice(0, 3)
                      .map((reason, index) => (
                        <p
                          key={index}
                          className="text-xs text-blue-200 bg-blue-500/10 px-2 py-1 rounded"
                        >
                          {reason}
                        </p>
                      ))}
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Enhanced Skills */}
        <div className="flex flex-wrap gap-1">
          {candidate.skills.slice(0, 3).map((skill) => {
            const relevance = getSkillRelevance(skill);
            const isHighRelevance = relevance >= 90;

            return (
              <motion.span
                key={skill}
                whileHover={{ scale: 1.05 }}
                className={`px-2 py-1 text-xs rounded-full transition-all ${
                  isHighRelevance
                    ? "bg-green-500/20 text-green-300 border border-green-400/30 shadow-sm"
                    : "bg-white/10 text-gray-300 group-hover:bg-purple-500/20 group-hover:text-purple-200"
                }`}
              >
                <div className="flex items-center space-x-1">
                  <span>{skill}</span>
                  {isHighRelevance && <Star className="w-2 h-2 fill-current" />}
                </div>
              </motion.span>
            );
          })}
          {candidate.skills.length > 3 && (
            <span className="px-2 py-1 text-xs bg-white/10 text-gray-400 rounded-full">
              +{candidate.skills.length - 3}
            </span>
          )}
        </div>

        {/* Location & Experience */}
        <div className="space-y-2">
          <div className="flex items-center space-x-1 text-sm text-gray-400">
            <MapPin className="w-3 h-3" />
            <span>{candidate.location}</span>
            {candidate.distance && (
              <span className="text-xs">({candidate.distance})</span>
            )}
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-400">
              {candidate.experience} years exp
            </span>
            <div className="flex-1 bg-gray-700 rounded-full h-1">
              <div
                className="bg-gradient-to-r from-purple-500 to-blue-500 h-1 rounded-full transition-all duration-1000"
                style={{
                  width: `${Math.min((candidate.experience ?? 0) * 10, 100)}%`,
                }}
              />
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="mt-auto space-y-3">
          <Button
            variant="outline"
            className="w-full border-white/20 text-white hover:bg-white/10 group"
          >
            <span>View Profile</span>
            <ExternalLink className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
          </Button>

          {/* 🔥 ENHANCED: Action buttons with AI outreach */}
          <div className="flex space-x-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={onToggleSave}
              className={`flex-1 ${
                isSaved ? "text-yellow-400" : "text-gray-400"
              } hover:text-yellow-300`}
            >
              <Bookmark
                className={`w-4 h-4 ${isSaved ? "fill-current" : ""}`}
              />
            </Button>

            <Button
              size="sm"
              variant="ghost"
              onClick={onAddToComparison}
              disabled={isInComparison}
              className={`flex-1 ${
                isInComparison ? "text-purple-400" : "text-gray-400"
              } hover:text-purple-300 disabled:opacity-50`}
            >
              <Versus className="w-4 h-4" />
            </Button>

            {/* 🔥 NEW: AI Outreach Button */}
            <Button
              size="sm"
              onClick={onGenerateOutreach}
              className="flex-1 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-xs"
            >
              <Zap className="w-3 h-3 mr-1" />
              AI Outreach
            </Button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// Keep all your existing components exactly the same
function SkeletonCard({ delay }: { delay: number }) {
  return (
    <div
      className="w-full h-72 rounded-xl overflow-hidden animate-pulse"
      style={{
        background: "rgba(255,255,255,0.03)",
        backdropFilter: "blur(12px)",
        border: "1px solid rgba(255,255,255,0.1)",
        animationDelay: `${delay}ms`,
      }}
    >
      <div className="p-6 space-y-4">
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 bg-gray-700 rounded-full" />
          <div className="space-y-2">
            <div className="w-24 h-4 bg-gray-700 rounded" />
            <div className="w-32 h-3 bg-gray-700 rounded" />
          </div>
        </div>

        <div className="flex space-x-2">
          <div className="w-16 h-6 bg-gray-700 rounded-full" />
          <div className="w-20 h-6 bg-gray-700 rounded-full" />
          <div className="w-14 h-6 bg-gray-700 rounded-full" />
        </div>

        <div className="space-y-2">
          <div className="w-full h-3 bg-gray-700 rounded" />
          <div className="w-3/4 h-3 bg-gray-700 rounded" />
        </div>

        <div className="w-full h-10 bg-gray-700 rounded" />
      </div>
    </div>
  );
}

interface ComparisonBarProps {
  candidates: Candidate[];
  onRemove: (candidateId: string) => void;
  onCompare: () => void;
  onClear: () => void;
}

function ComparisonBar({
  candidates,
  onRemove,
  onCompare,
  onClear,
}: ComparisonBarProps) {
  return (
    <div className="bg-gray-800 rounded-full shadow-lg p-4 flex items-center space-x-4">
      {candidates.map((candidate) => (
        <div key={candidate.id} className="flex items-center space-x-2">
          <img
            src={candidate.avatar || "/placeholder.svg"}
            alt={candidate.name}
            className="w-8 h-8 rounded-full object-cover"
          />
          <button
            onClick={() => onRemove(candidate.id)}
            className="text-gray-500 hover:text-red-500"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="currentColor"
              className="w-4 h-4"
            >
              <path
                fillRule="evenodd"
                d="M5.47 5.47a.75.75 0 011.06 0L12 10.94l5.47-5.47a.75.75 0 111.06 1.06L13.06 12l5.47 5.47a.75.75 0 01-1.06-1.06L10.94 12 5.47 6.53a.75.75 0 010-1.06z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>
      ))}
      <Button size="sm" onClick={onCompare} disabled={candidates.length < 2}>
        Compare
      </Button>
      <Button size="sm" variant="destructive" onClick={onClear}>
        Clear
      </Button>
    </div>
  );
}

interface CandidateComparisonProps {
  candidates: Candidate[];
  isOpen: boolean;
  onClose: () => void;
  onRemove: (candidateId: string) => void;
}

function CandidateComparison({
  candidates,
  isOpen,
  onClose,
  onRemove,
}: CandidateComparisonProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/75">
      <div className="bg-gray-800 rounded-xl shadow-lg p-6 w-3/4 max-h-[80vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-white">
            Candidate Comparison
          </h2>
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
        </div>

        {candidates.length < 2 ? (
          <p className="text-gray-400">
            Select at least two candidates to compare.
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {candidates.map((candidate) => (
              <div
                key={candidate.id}
                className="p-4 rounded-xl border border-gray-700"
              >
                <div className="flex justify-between items-center mb-2">
                  <h3 className="text-lg font-semibold text-white">
                    {candidate.name}
                  </h3>
                  <button
                    onClick={() => onRemove(candidate.id)}
                    className="text-gray-500 hover:text-red-500"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 24 24"
                      fill="currentColor"
                      className="w-4 h-4"
                    >
                      <path
                        fillRule="evenodd"
                        d="M5.47 5.47a.75.75 0 011.06 0L12 10.94l5.47-5.47a.75.75 0 111.06 1.06L13.06 12l5.47 5.47a.75.75 0 01-1.06-1.06L10.94 12 5.47 6.53a.75.75 0 010-1.06z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </button>
                </div>
                <p className="text-gray-400">{candidate.title}</p>
                <div className="mt-2">
                  <p className="text-sm text-gray-400">
                    Match Score: {candidate.matchScore}%
                  </p>
                  <p className="text-sm text-gray-400">
                    Experience: {candidate.experience} years
                  </p>
                  <p className="text-sm text-gray-400">
                    Skills: {candidate.skills.join(", ")}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
