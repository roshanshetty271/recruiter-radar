"use client";

import type React from "react";
import { useState, useEffect, useCallback, useRef } from "react";
import {
  Mic,
  Filter,
  Brain,
  TrendingUp,
  Zap,
  Target,
  Upload,
  Send,
  Sparkles,
  MessageCircleIcon,
} from "lucide-react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Badge } from "./ui/badge";
import { Progress } from "./ui/progress";
import { AdvancedFilters } from "./advanced-filters";
import { motion, AnimatePresence } from "framer-motion";
import { QuerySuggestions } from "./chat/QuerySuggestions";

interface QueryIntelligence {
  query_complexity: "simple" | "moderate" | "complex";
  semantic_themes: string[];
  suggested_refinements: string[];
  market_insights: string[];
  confidence_score: number;
  interpretation?: string;
}

interface QueryRefinement {
  label: string;
  action: string;
  icon: React.ReactNode;
}

export function SearchInterface({
  onChat,
  initialQuery = "",
  onFilterChange = () => {},
  onUploadClick,
  remainingUploads = 10,
  isTyping = false,
  remainingMessages = 10,
  lastQueryInterpretation,
  showRefinements = false,
}: {
  onChat: (message: string) => void;
  initialQuery?: string;
  onFilterChange?: (filters: any) => void;
  onUploadClick?: () => void;
  remainingUploads?: number;
  isTyping?: boolean;
  remainingMessages?: number;
  lastQueryInterpretation?: string;
  showRefinements?: boolean;
}) {
  const [query, setQuery] = useState(initialQuery);
  const [showFilters, setShowFilters] = useState(false);
  const [activeFilters, setActiveFilters] = useState(0);
  const [filters, setFilters] = useState({});
  const [lastQuery, setLastQuery] = useState("");

  // 🎯 Refs for keyboard shortcuts
  const inputRef = useRef<HTMLInputElement>(null);

  // 🧠 Enhanced AI Intelligence State
  const [debouncedQuery, setDebouncedQuery] = useState(query);
  const [queryIntelligence, setQueryIntelligence] =
    useState<QueryIntelligence | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [showIntelligence, setShowIntelligence] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(!query);

  // 🚀 Smart Query Refinements (appear after search)
  const [refinements, setRefinements] = useState<QueryRefinement[]>([]);

  // 🎯 Keyboard shortcuts - "/" to focus, "↑" for last query
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // "/" to focus search input
      if (
        e.key === "/" &&
        !e.ctrlKey &&
        !e.metaKey &&
        document.activeElement !== inputRef.current
      ) {
        e.preventDefault();
        inputRef.current?.focus();
      }

      // "↑" to resurface last query (when input is focused and empty)
      if (
        e.key === "ArrowUp" &&
        document.activeElement === inputRef.current &&
        !query.trim() &&
        lastQuery
      ) {
        e.preventDefault();
        setQuery(lastQuery);
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [query, lastQuery]);

  // 🚀 Debounced query for real-time analysis
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query);
    }, 500);

    return () => clearTimeout(timer);
  }, [query]);

  // 🧠 Real-time AI analysis
  useEffect(() => {
    if (debouncedQuery.trim().length > 3) {
      analyzeQuery(debouncedQuery);
    } else {
      setQueryIntelligence(null);
      setShowIntelligence(false);
      setShowSuggestions(!query);
    }
  }, [debouncedQuery]);

  // 🔥 Enhanced AI Query Analysis
  const analyzeQuery = useCallback(async (searchQuery: string) => {
    setIsAnalyzing(true);
    setShowSuggestions(false);

    // Simulate advanced AI processing
    await new Promise((resolve) => setTimeout(resolve, 600));

    const mockIntelligence: QueryIntelligence = {
      query_complexity:
        searchQuery.split(" ").length > 5
          ? "complex"
          : searchQuery.split(" ").length > 2
          ? "moderate"
          : "simple",
      semantic_themes: extractSemanticThemes(searchQuery),
      suggested_refinements: generateRefinements(searchQuery),
      market_insights: generateMarketInsights(searchQuery),
      confidence_score: Math.min(95, 60 + searchQuery.length * 1.5),
      interpretation: generateInterpretation(searchQuery),
    };

    setQueryIntelligence(mockIntelligence);
    setShowIntelligence(true);
    setIsAnalyzing(false);
  }, []);

  // 🎯 Generate human interpretation
  const generateInterpretation = (searchQuery: string): string => {
    const q = searchQuery.toLowerCase();
    let interpretation = "Looking for: ";

    if (q.includes("senior")) interpretation += "Senior ";
    if (q.includes("python")) interpretation += "Python developers";
    else if (q.includes("react")) interpretation += "React developers";
    else if (q.includes("machine learning") || q.includes("ml"))
      interpretation += "ML engineers";
    else interpretation += "candidates";

    if (
      q.includes("california") ||
      q.includes("sf") ||
      q.includes("san francisco")
    ) {
      interpretation += " in California";
    }
    if (q.includes("remote")) interpretation += " (remote work)";

    return interpretation;
  };

  // 🎯 Extract semantic themes
  const extractSemanticThemes = (searchQuery: string): string[] => {
    const themes: string[] = [];
    const q = searchQuery.toLowerCase();

    if (q.includes("senior") || q.includes("lead") || q.includes("architect"))
      themes.push("Senior Level");
    if (q.includes("full stack") || q.includes("fullstack"))
      themes.push("Full-Stack");
    if (q.includes("ai") || q.includes("machine learning") || q.includes("ml"))
      themes.push("AI/ML");
    if (q.includes("react") || q.includes("vue") || q.includes("angular"))
      themes.push("Frontend Frameworks");
    if (q.includes("startup") || q.includes("scale"))
      themes.push("Startup Experience");
    if (q.includes("remote")) themes.push("Remote Work");

    return themes.length > 0 ? themes : ["General Tech"];
  };

  // 💡 Generate smart suggestions
  const generateRefinements = (searchQuery: string): string[] => {
    const refinements: string[] = [];
    const q = searchQuery.toLowerCase();

    if (!q.includes("year") && !q.includes("experience")) {
      refinements.push("Consider adding experience level");
    }
    if (!q.includes("location") && !q.includes("remote")) {
      refinements.push("Specify location or remote preference");
    }
    if (
      q.includes("developer") &&
      !q.includes("senior") &&
      !q.includes("junior")
    ) {
      refinements.push("Add seniority level for better targeting");
    }

    return refinements;
  };

  // 📈 Market insights
  const generateMarketInsights = (searchQuery: string): string[] => {
    const insights: string[] = [];
    const q = searchQuery.toLowerCase();

    if (q.includes("react")) {
      insights.push("🔥 React devs: 85% response rate, avg 2.1 days");
      insights.push("💰 Salary trending +12% YoY");
    }
    if (q.includes("ai") || q.includes("ml")) {
      insights.push("⚡ AI roles: 3x higher engagement than avg");
      insights.push("🎯 Best outreach time: Tuesday 10-11am");
    }
    if (q.includes("senior")) {
      insights.push("⚠️ Senior roles: 40% more competition");
      insights.push("💼 Highlight growth opportunities");
    }

    return insights;
  };

  // 🚀 Generate post-search refinements
  const generatePostSearchRefinements = (
    lastQuery: string
  ): QueryRefinement[] => {
    const refinements: QueryRefinement[] = [];
    const q = lastQuery.toLowerCase();

    if (q.includes("python")) {
      refinements.push({
        label: "More Senior",
        action: "senior Python developers with 7+ years",
        icon: <TrendingUp className="w-3 h-3" />,
      });
      refinements.push({
        label: "Add AWS",
        action: "Python developers with AWS experience",
        icon: <Zap className="w-3 h-3" />,
      });
      refinements.push({
        label: "Remote Only",
        action: "remote Python developers",
        icon: <Target className="w-3 h-3" />,
      });
    }

    if (!q.includes("remote") && !q.includes("location")) {
      refinements.push({
        label: "Add Location",
        action: lastQuery + " in San Francisco",
        icon: <Target className="w-3 h-3" />,
      });
    }

    return refinements;
  };

  // Update refinements when we get results
  useEffect(() => {
    if (showRefinements && lastQueryInterpretation) {
      const newRefinements = generatePostSearchRefinements(query);
      setRefinements(newRefinements);
    }
  }, [showRefinements, lastQueryInterpretation, query]);

  const handleChat = async () => {
    if (!query.trim() || isTyping || remainingMessages <= 0) return;

    const currentQuery = query.trim();
    setLastQuery(currentQuery); // Store for ↑ shortcut
    onChat(currentQuery);
    setQuery(""); // Clear input after sending
    setShowSuggestions(true); // Show suggestions for next query
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleChat();
    }
  };

  const handleFiltersChange = (count: number, filterData: any) => {
    setActiveFilters(count);
    setFilters(filterData);
    onFilterChange(filterData);
  };

  const getComplexityColor = (complexity: string) => {
    switch (complexity) {
      case "simple":
        return "text-green-400";
      case "moderate":
        return "text-yellow-400";
      case "complex":
        return "text-red-400";
      default:
        return "text-gray-400";
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion);
    // Auto-trigger for convenience
    onChat(suggestion);
    setQuery("");
  };

  const handleRefinementClick = (refinement: QueryRefinement) => {
    setQuery(refinement.action);
    onChat(refinement.action);
    setQuery("");
  };

  const isDisabled = !query.trim() || isTyping || remainingMessages <= 0;

  // Enhanced placeholder text
  const getPlaceholder = () => {
    if (isTyping) return "AI is thinking...";
    return "Tell me what you're looking for... (e.g., 'Senior Python developers who can start next month')";
  };

  return (
    <div className="space-y-6">
      {/* 🚀 HERO CHAT INPUT - Now the star of the show! */}
      <div className="relative">
        <div
          className="relative group"
          style={{
            background: "rgba(255,255,255,0.05)",
            backdropFilter: "blur(12px)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: "20px",
            boxShadow: query ? "0 8px 32px rgba(147, 51, 234, 0.2)" : "",
          }}
        >
          <div className="flex items-center p-6 space-x-4">
            <div className="flex-shrink-0">
              {isTyping ? (
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  className="w-7 h-7 border-2 border-purple-400 border-t-transparent rounded-full"
                />
              ) : isAnalyzing ? (
                <Brain className="w-7 h-7 text-purple-400 animate-pulse" />
              ) : (
                <MessageCircleIcon className="w-7 h-7 text-purple-400" />
              )}
            </div>

            <Input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={getPlaceholder()}
              className="flex-1 bg-transparent border-0 text-white placeholder-gray-400 text-xl focus:ring-0 focus:outline-none"
              style={{ fontSize: "18px" }}
            />

            <div className="flex items-center space-x-3">
              <Button
                variant="ghost"
                size="sm"
                className="text-gray-400 hover:text-white"
              >
                <Mic className="w-5 h-5" />
              </Button>

              {/* 🧠 Intelligence Toggle */}
              {queryIntelligence && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowIntelligence(!showIntelligence)}
                  className={`text-purple-400 hover:text-purple-300 transition-all duration-300 ${
                    showIntelligence ? "bg-purple-500/20" : ""
                  }`}
                >
                  <Brain className="w-5 h-5" />
                </Button>
              )}

              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowFilters(!showFilters)}
                className={`text-gray-400 hover:text-white relative ${
                  showFilters ? "rotate-180" : ""
                } transition-transform duration-300`}
              >
                <Filter className="w-5 h-5" />
                {activeFilters > 0 && (
                  <span className="absolute -top-1 -right-1 w-4 h-4 bg-purple-500 text-white text-xs rounded-full flex items-center justify-center">
                    {activeFilters}
                  </span>
                )}
              </Button>
            </div>
          </div>

          <div className="flex items-center justify-between px-6 pb-6">
            <div className="flex items-center space-x-4">
              <div className="text-xs text-gray-500">
                {query.length}/200 characters
              </div>

              {/* 🎯 Query Intelligence Indicator */}
              {queryIntelligence && (
                <div className="flex items-center space-x-3">
                  <div className="flex items-center space-x-1">
                    <Sparkles className="w-3 h-3 text-purple-400" />
                    <span
                      className={`text-xs font-medium ${getComplexityColor(
                        queryIntelligence.query_complexity
                      )}`}
                    >
                      {queryIntelligence.query_complexity}
                    </span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <span className="text-xs text-gray-400">confidence:</span>
                    <span className="text-xs font-medium text-green-400">
                      {queryIntelligence.confidence_score}%
                    </span>
                  </div>
                  {queryIntelligence.interpretation && (
                    <div className="flex items-center space-x-1">
                      <span className="text-xs text-blue-300">
                        {queryIntelligence.interpretation}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="flex items-center space-x-3">
              {onUploadClick && (
                <Button
                  onClick={onUploadClick}
                  variant="outline"
                  className="px-4 py-2 border-purple-400/30 bg-purple-600/10 hover:bg-purple-600/20 text-purple-300 hover:text-purple-200 rounded-lg"
                >
                  <Upload className="w-4 h-4 mr-2" />
                  Upload ({remainingUploads})
                </Button>
              )}

              <Button
                onClick={handleChat}
                disabled={isDisabled}
                className="px-8 py-3 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 disabled:opacity-50 rounded-xl text-lg font-medium"
              >
                {isTyping ? (
                  <div className="flex items-center space-x-2">
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{
                        duration: 1,
                        repeat: Infinity,
                        ease: "linear",
                      }}
                    >
                      <Brain className="w-5 h-5" />
                    </motion.div>
                    <span>Thinking...</span>
                  </div>
                ) : (
                  <div className="flex items-center space-x-2">
                    <Send className="w-5 h-5" />
                    <span>Ask AI</span>
                  </div>
                )}
              </Button>

              <div className="text-xs text-gray-400">
                {remainingMessages} questions left
              </div>
            </div>
          </div>
        </div>

        {/* 🔥 AI Intelligence Panel */}
        <AnimatePresence>
          {showIntelligence && queryIntelligence && (
            <motion.div
              initial={{ opacity: 0, y: -10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.95 }}
              transition={{ duration: 0.3, ease: "easeOut" }}
              className="mt-4"
              style={{
                background: "rgba(147, 51, 234, 0.1)",
                backdropFilter: "blur(12px)",
                border: "1px solid rgba(147, 51, 234, 0.2)",
                borderRadius: "12px",
              }}
            >
              <div className="p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Brain className="w-4 h-4 text-purple-400" />
                    <span className="text-sm font-semibold text-white">
                      AI Analysis
                    </span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Progress
                      value={queryIntelligence.confidence_score}
                      className="w-20 h-2"
                    />
                    <span className="text-xs text-purple-300">
                      {queryIntelligence.confidence_score}%
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* Themes */}
                  <div>
                    <h4 className="text-xs font-medium text-gray-300 mb-2">
                      Themes
                    </h4>
                    <div className="flex flex-wrap gap-1">
                      {queryIntelligence.semantic_themes.map((theme, index) => (
                        <Badge
                          key={index}
                          variant="secondary"
                          className="text-xs bg-purple-500/20 text-purple-300"
                        >
                          {theme}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  {/* Refinements */}
                  <div>
                    <h4 className="text-xs font-medium text-gray-300 mb-2">
                      Suggestions
                    </h4>
                    <div className="space-y-1">
                      {queryIntelligence.suggested_refinements.map(
                        (refinement, index) => (
                          <div
                            key={index}
                            className="text-xs text-yellow-300 bg-yellow-500/10 px-2 py-1 rounded"
                          >
                            {refinement}
                          </div>
                        )
                      )}
                    </div>
                  </div>

                  {/* Market Insights */}
                  <div>
                    <h4 className="text-xs font-medium text-gray-300 mb-2">
                      Market Insights
                    </h4>
                    <div className="space-y-1">
                      {queryIntelligence.market_insights.map(
                        (insight, index) => (
                          <div
                            key={index}
                            className="text-xs text-blue-300 bg-blue-500/10 px-2 py-1 rounded"
                          >
                            {insight}
                          </div>
                        )
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* 🚀 POST-SEARCH REFINEMENT CHIPS */}
        <AnimatePresence>
          {showRefinements && refinements.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              className="mt-4"
            >
              <div className="flex items-center space-x-2 mb-2">
                <Sparkles className="w-4 h-4 text-purple-400" />
                <span className="text-sm text-gray-300">
                  Quick refinements:
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                {refinements.map((refinement, index) => (
                  <Button
                    key={index}
                    variant="outline"
                    size="sm"
                    onClick={() => handleRefinementClick(refinement)}
                    className="border-purple-400/30 bg-purple-600/10 hover:bg-purple-600/20 text-purple-300 hover:text-purple-200"
                  >
                    {refinement.icon}
                    <span className="ml-1">{refinement.label}</span>
                  </Button>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* 🎯 QUERY SUGGESTIONS (when input is empty) */}
        <AnimatePresence>
          {showSuggestions && !query && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              className="mt-4"
            >
              <QuerySuggestions onSuggestionClick={handleSuggestionClick} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Advanced Filters Panel */}
      <AnimatePresence>
        {showFilters && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
          >
            <AdvancedFilters onFiltersChange={handleFiltersChange} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
