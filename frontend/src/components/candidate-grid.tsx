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
  Upload,
  Database,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { ViewProfileModal } from "@/components/custom/view-profile-modal";
import { useSavedCandidates } from "@/hooks/use-saved-candidates";
import { toast } from "@/hooks/use-toast";
import { CandidateComparison as CandidateComparisonModal } from "./candidate-comparison";
import { ProgressiveSearchFeedback } from "@/components/custom/progressive-search-feedback";
import { FrontendCandidate } from "@/services/types";

export function CandidateGrid({
  candidates,
  isLoading,
  searchQuery = "", // 🔥 NEW
  onGenerateOutreach, // 🔥 NEW
  totalCandidates, // 🔥 NEW
  searchMetadata, // 🔥 NEW: Progressive search metadata
}: {
  candidates: FrontendCandidate[];
  isLoading: boolean;
  searchQuery?: string; // 🔥 NEW
  onGenerateOutreach?: (candidateId: string) => void; // 🔥 NEW
  totalCandidates: number; // 🔥 NEW
  searchMetadata?: any; // 🔥 NEW: Progressive search metadata
}) {
  const { saveCandidate, removeCandidate, isSaved } = useSavedCandidates();
  const [comparisonCandidates, setComparisonCandidates] = useState<
    FrontendCandidate[]
  >([]);
  const [showComparison, setShowComparison] = useState(false);

  const toggleSave = (candidate: FrontendCandidate) => {
    if (isSaved(candidate.id)) {
      removeCandidate(candidate.id);
      toast({
        title: "⭐ Removed from Saved",
        description: `${candidate.name} removed from saved candidates`,
      });
    } else {
      saveCandidate({
        id: candidate.id,
        name: candidate.name,
        skills: candidate.skills,
        experience_years: candidate.experience || 0,
        location: candidate.location,
      });
      toast({
        title: "⭐ Saved Candidate",
        description: `${candidate.name} added to saved candidates`,
      });
    }
  };

  const addToComparison = (candidate: FrontendCandidate) => {
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
      <div className="space-y-6">
        {/* 🧠 Progressive Search Feedback for Empty Results */}
        <ProgressiveSearchFeedback
          searchMetadata={searchMetadata}
          resultCount={0}
          isVisible={true}
        />

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
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 🔥 NEW: Enhanced Results Header */}
      <div
        className="flex items-center justify-between"
        data-candidate-results
        data-testid="candidate-results"
        id="candidate-results-header"
      >
        <div className="flex items-center space-x-4">
          <h2 className="text-lg font-semibold text-white flex items-center space-x-2">
            <Brain className="w-5 h-5 text-purple-400" />
            <span>Found {totalCandidates} AI-matched candidates</span>
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

      {/* 🧠 Progressive Search Feedback for Results */}
      <ProgressiveSearchFeedback
        searchMetadata={searchMetadata}
        resultCount={totalCandidates}
        isVisible={searchQuery.length > 0} // Only show when there's an active search
      />

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
        <CandidateComparisonModal
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
            isSaved={isSaved(candidate.id)}
            onToggleSave={() => toggleSave(candidate)}
            onAddToComparison={() => addToComparison(candidate)}
            onGenerateOutreach={() => onGenerateOutreach?.(candidate.id)} // 🔥 NEW
            isInComparison={comparisonCandidates.some(
              (c) => c.id === candidate.id
            )}
            delay={index * 50}
          />
        ))}
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
  candidate: FrontendCandidate;
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
  const [open, setOpen] = useState(false);

  // 🧠 ENHANCED: Generate proper AI match analysis with only real skills
  const generateMatchAnalysis = () => {
    if (!searchQuery || searchQuery.trim().length === 0) {
      return {
        matchedSkills: [],
        matchReasons: [],
        confidenceScore: candidate.matchScore,
      };
    }

    // Extract skills from search query (same logic as backend)
    const extractSkillsFromQuery = (query: string): string[] => {
      const queryLower = query.toLowerCase();
      const roleSkillMapping: { [key: string]: string[] } = {
        "web developer": [
          "html",
          "css",
          "javascript",
          "react",
          "vue",
          "angular",
          "node.js",
          "web development",
        ],
        "web dev": [
          "html",
          "css",
          "javascript",
          "react",
          "vue",
          "angular",
          "node.js",
          "web development",
        ],
        "frontend developer": [
          "html",
          "css",
          "javascript",
          "react",
          "vue",
          "angular",
          "typescript",
          "frontend",
        ],
        "front end developer": [
          "html",
          "css",
          "javascript",
          "react",
          "vue",
          "angular",
          "typescript",
          "frontend",
        ],
        "backend developer": [
          "python",
          "java",
          "node.js",
          "api",
          "database",
          "sql",
          "backend",
        ],
        "back end developer": [
          "python",
          "java",
          "node.js",
          "api",
          "database",
          "sql",
          "backend",
        ],
        "full stack developer": [
          "javascript",
          "python",
          "react",
          "node.js",
          "database",
          "api",
          "full stack",
        ],
        "fullstack developer": [
          "javascript",
          "python",
          "react",
          "node.js",
          "database",
          "api",
          "full stack",
        ],
        "data scientist": [
          "python",
          "machine learning",
          "sql",
          "pandas",
          "data science",
          "ai",
        ],
        "devops engineer": [
          "docker",
          "kubernetes",
          "aws",
          "ci/cd",
          "devops",
          "infrastructure",
        ],
        "mobile developer": [
          "ios",
          "android",
          "swift",
          "kotlin",
          "react native",
          "flutter",
          "mobile",
        ],
      };

      const skillKeywords = [
        "python",
        "java",
        "javascript",
        "typescript",
        "react",
        "angular",
        "vue",
        "node.js",
        "html",
        "css",
        "docker",
        "kubernetes",
        "aws",
        "azure",
        "gcp",
        "sql",
        "nosql",
        "mongodb",
        "postgresql",
        "redis",
        "machine learning",
        "ml",
        "ai",
        "tensorflow",
        "pytorch",
        "data science",
        "devops",
        "git",
        "api",
        "microservices",
        "spring",
        "django",
        "flask",
        "fastapi",
        "graphql",
        "rest",
      ];

      let extractedSkills: string[] = [];

      // Check for role-based patterns
      for (const [role, skills] of Object.entries(roleSkillMapping)) {
        if (queryLower.includes(role)) {
          extractedSkills.push(...skills);
        }
      }

      // Check for explicit skill mentions
      for (const skill of skillKeywords) {
        if (queryLower.includes(skill)) {
          extractedSkills.push(skill);
        }
      }

      // Remove duplicates and normalize
      return [...new Set(extractedSkills)].map(
        (skill) => skill.charAt(0).toUpperCase() + skill.slice(1).toLowerCase()
      );
    };

    const querySkills = extractSkillsFromQuery(searchQuery);

    // Find skills that match the query
    const matchedSkills = candidate.skills.filter((candidateSkill) => {
      const candidateSkillLower = candidateSkill.toLowerCase();
      return querySkills.some((querySkill) => {
        const querySkillLower = querySkill.toLowerCase();
        return (
          candidateSkillLower.includes(querySkillLower) ||
          querySkillLower.includes(candidateSkillLower) ||
          candidateSkillLower === querySkillLower
        );
      });
    });

    // Generate ONLY skill-based match reasons (no fake UI elements)
    const matchReasons: string[] = [];

    if (matchedSkills.length > 0) {
      const skillText = matchedSkills.slice(0, 3).join(", ");
      const remainingCount = matchedSkills.length - 3;
      const suffix = remainingCount > 0 ? `, +${remainingCount} more` : "";

      matchReasons.push(`🎯 Skills: ${skillText}${suffix}`);
    }

    // Only add experience if it's genuinely relevant to the query
    const candidateExperience = candidate.experience || 0;
    if (
      candidateExperience >= 5 &&
      (searchQuery.toLowerCase().includes("senior") ||
        searchQuery.toLowerCase().includes("lead"))
    ) {
      matchReasons.push(`⭐ ${candidateExperience} years experience`);
    }

    return {
      matchedSkills,
      matchReasons,
      confidenceScore: Math.min(
        100,
        candidate.matchScore + matchedSkills.length * 5
      ),
    };
  };

  // 🎨 ENHANCED: Better skill relevance detection
  const getSkillRelevance = (skill: string) => {
    if (!searchQuery || searchQuery.trim().length === 0) return 60;

    const queryLower = searchQuery.toLowerCase();
    const skillLower = skill.toLowerCase();

    // High relevance for exact matches or substring matches
    if (queryLower.includes(skillLower) || skillLower.includes(queryLower)) {
      return 95;
    }

    // Medium relevance for related terms
    const queryWords = queryLower
      .split(/\s+/)
      .filter((word) => word.length > 2);
    if (
      queryWords.some(
        (word) => skillLower.includes(word) || word.includes(skillLower)
      )
    ) {
      return 80;
    }

    return 60;
  };

  const matchAnalysis = generateMatchAnalysis();

  // 🔍 ENHANCED: Filter and prioritize skills for display
  const getDisplaySkills = () => {
    if (!searchQuery || searchQuery.trim().length === 0) {
      return candidate.skills.slice(0, 5);
    }

    // Prioritize matched skills first, then others
    const matchedSkills = matchAnalysis.matchedSkills;
    const otherSkills = candidate.skills.filter(
      (skill) =>
        !matchedSkills.some(
          (matched) => matched.toLowerCase() === skill.toLowerCase()
        )
    );

    // Show matched skills first, then fill remaining slots with other skills
    const displaySkills = [
      ...matchedSkills.slice(0, 4),
      ...otherSkills.slice(0, Math.max(0, 5 - matchedSkills.length)),
    ];

    return displaySkills.slice(0, 5);
  };

  const displaySkills = getDisplaySkills();

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: delay / 1000 }}
      className="group relative w-full rounded-xl overflow-hidden cursor-pointer transform transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl hover:shadow-purple-500/25"
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
      <div className="absolute inset-[1px] bg-gray-900/95 rounded-xl" />

      <div className="relative p-4 h-full flex flex-col space-y-3">
        {/* Header Section - Improved Layout */}
        <div className="flex items-start justify-between space-x-3">
          <div className="flex items-start space-x-3 flex-1 min-w-0">
            <div className="relative flex-shrink-0">
              <img
                src={candidate.avatar || "/placeholder.svg"}
                alt={candidate.name}
                className="w-10 h-10 rounded-full object-cover"
              />
              {candidate.isOnline && (
                <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-400 rounded-full border-2 border-gray-900 animate-pulse" />
              )}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-1 mb-1">
                <h3 className="font-semibold text-white text-sm leading-tight truncate">
                  {candidate.name}
                </h3>
                {candidate.isVerified && (
                  <CheckCircle className="w-3 h-3 text-blue-400 flex-shrink-0" />
                )}
                {matchAnalysis.confidenceScore >= 90 && (
                  <Sparkles className="w-3 h-3 text-yellow-400 flex-shrink-0" />
                )}
              </div>
              {/* Improved Job Title with Better Line Wrapping */}
              <p className="text-xs text-gray-400 leading-tight line-clamp-2 break-words">
                {candidate.title}
              </p>
            </div>
          </div>

          {/* Compact Match Score and Source Badge */}
          <div className="flex flex-col items-end space-y-1 flex-shrink-0">
            {/* Source Badge - Smaller */}
            {candidate.source === "uploaded_resume_batch" ? (
              <Badge className="bg-purple-500/20 text-purple-400 border-purple-500/30 text-xs px-1.5 py-0.5 h-5">
                <Upload className="w-2.5 h-2.5 mr-1" />
                New
              </Badge>
            ) : (
              <Badge className="bg-gray-700/50 text-gray-400 border-gray-700 text-xs px-1.5 py-0.5 h-5">
                <Database className="w-2.5 h-2.5 mr-1" />
                Demo
              </Badge>
            )}

            {/* Compact Match Score */}
            <div className="relative w-10 h-10">
              <svg className="w-10 h-10 transform -rotate-90">
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
                  cx="20"
                  cy="20"
                  r="16"
                  stroke="rgba(255,255,255,0.1)"
                  strokeWidth="2.5"
                  fill="none"
                />
                <circle
                  cx="20"
                  cy="20"
                  r="16"
                  stroke={`url(#gradient-${candidate.id})`}
                  strokeWidth="2.5"
                  fill="none"
                  strokeDasharray={`${candidate.matchScore * 1.005} 100.5`}
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
        </div>

        {/* AI Analysis Toggle - More Compact */}
        {searchQuery && (
          <div className="flex items-center justify-between">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowAIAnalysis(!showAIAnalysis)}
              className="text-purple-400 hover:text-purple-300 h-5 px-2 text-xs"
            >
              <Brain className="w-3 h-3 mr-1" />
              Analysis
              {showAIAnalysis ? (
                <ChevronUp className="w-3 h-3 ml-1" />
              ) : (
                <ChevronDown className="w-3 h-3 ml-1" />
              )}
            </Button>
            <div className="flex items-center space-x-1">
              <Target className="w-3 h-3 text-green-400" />
              <span className="text-xs text-green-400 font-medium">
                {matchAnalysis.confidenceScore}%
              </span>
            </div>
          </div>
        )}

        {/* AI Analysis Panel - Improved */}
        <AnimatePresence>
          {showAIAnalysis && searchQuery && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="bg-gradient-to-r from-purple-500/10 to-blue-500/10 rounded-md p-2 border border-purple-400/20"
            >
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <Brain className="w-3 h-3 text-purple-400" />
                  <span className="text-xs font-semibold text-purple-200">
                    Match Analysis
                  </span>
                  <Progress
                    value={matchAnalysis.confidenceScore}
                    className="w-8 h-1"
                  />
                </div>

                {matchAnalysis.matchReasons.length > 0 && (
                  <div className="space-y-1">
                    {matchAnalysis.matchReasons
                      .slice(0, 2)
                      .map((reason, index) => (
                        <p
                          key={index}
                          className="text-xs text-blue-200 bg-blue-500/10 px-1.5 py-0.5 rounded text-left"
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

        {/* Enhanced Skills - More Compact and Responsive */}
        <div className="flex flex-wrap gap-1">
          {displaySkills.map((skill) => {
            const relevance = getSkillRelevance(skill);
            const isHighRelevance = relevance >= 90;

            return (
              <span
                key={skill}
                className={`px-2 py-0.5 text-xs rounded-full transition-all ${
                  isHighRelevance
                    ? "bg-green-500/20 text-green-300 border border-green-400/30"
                    : "bg-white/10 text-gray-300 group-hover:bg-purple-500/20 group-hover:text-purple-200"
                }`}
              >
                <div className="flex items-center space-x-1">
                  <span className="truncate">{skill}</span>
                  {isHighRelevance && (
                    <Star className="w-2 h-2 fill-current flex-shrink-0" />
                  )}
                </div>
              </span>
            );
          })}
          {candidate.skills.length > 5 && (
            <span className="px-2 py-0.5 text-xs bg-white/10 text-gray-400 rounded-full">
              +{candidate.skills.length - 5}
            </span>
          )}
        </div>

        {/* Location & Experience - Compact */}
        <div className="space-y-1.5">
          <div className="flex items-center space-x-1 text-xs text-gray-400">
            <MapPin className="w-3 h-3 flex-shrink-0" />
            <span className="truncate">{candidate.location}</span>
            <span className="text-xs flex-shrink-0">
              ({candidate.distance})
            </span>
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-xs text-gray-400 flex-shrink-0">
              {candidate.experience || 0} years
            </span>
            <div className="flex-1 bg-gray-700 rounded-full h-1">
              <div
                className="bg-gradient-to-r from-purple-500 to-blue-500 h-1 rounded-full transition-all duration-1000"
                style={{
                  width: `${Math.min((candidate.experience || 0) * 10, 100)}%`,
                }}
              />
            </div>
          </div>
        </div>

        {/* Actions - Improved Layout */}
        <div className="mt-auto space-y-2 pt-2">
          <Button
            variant="outline"
            className="w-full border-white/20 text-white hover:bg-white/10 group h-8 text-xs"
            onClick={() => setOpen(true)}
          >
            <span>View Profile</span>
            <ExternalLink className="w-3 h-3 ml-2 group-hover:translate-x-1 transition-transform" />
          </Button>

          {open && (
            <ViewProfileModal
              open={open}
              onClose={() => setOpen(false)}
              candidate={{
                id: candidate.id,
                name: candidate.name,
                professional_summary: candidate.title,
                skills: candidate.skills,
                experience_years: candidate.experience || 0,
              }}
            />
          )}

          {/* Action buttons - More Compact */}
          <div className="flex space-x-1">
            <Button
              size="sm"
              variant="ghost"
              onClick={onToggleSave}
              className={`flex-1 h-7 ${
                isSaved ? "text-yellow-400" : "text-gray-400"
              } hover:text-yellow-300`}
            >
              <Bookmark
                className={`w-3 h-3 ${isSaved ? "fill-current" : ""}`}
              />
            </Button>

            <Button
              size="sm"
              variant="ghost"
              onClick={onAddToComparison}
              disabled={isInComparison}
              className={`flex-1 h-7 ${
                isInComparison ? "text-purple-400" : "text-gray-400"
              } hover:text-purple-300 disabled:opacity-50`}
            >
              <Versus className="w-3 h-3" />
            </Button>

            {/* AI Outreach Button - Improved */}
            <Button
              size="sm"
              onClick={onGenerateOutreach}
              className="flex-1 h-7 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-xs px-2"
            >
              <Zap className="w-3 h-3 mr-1" />
              <span className="hidden sm:inline">AI</span> Outreach
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
  candidates: FrontendCandidate[];
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

interface LegacyCandidateComparisonProps {
  candidates: FrontendCandidate[];
  isOpen: boolean;
  onClose: () => void;
  onRemove: (candidateId: string) => void;
}

function LegacyCandidateComparison({
  candidates,
  isOpen,
  onClose,
  onRemove,
}: LegacyCandidateComparisonProps) {
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
                    Experience: {candidate.experience || 0} years
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
