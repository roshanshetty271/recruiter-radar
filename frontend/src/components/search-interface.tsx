"use client";

import type React from "react";
import { useState, useEffect, useCallback } from "react";
import {
  Search,
  Mic,
  Filter,
  Brain,
  TrendingUp,
  Zap,
  Target,
  Upload,
} from "lucide-react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Badge } from "./ui/badge";
import { Progress } from "./ui/progress";
import { AdvancedFilters } from "./advanced-filters";
import { motion, AnimatePresence } from "framer-motion";

interface SearchIntelligence {
  query_complexity: "simple" | "moderate" | "complex";
  semantic_themes: string[];
  suggested_refinements: string[];
  market_insights: string[];
  confidence_score: number;
}

export function SearchInterface({
  onSearch,
  initialQuery = "",
  onFilterChange = () => {},
  onUploadClick,
  remainingUploads = 10,
}: {
  onSearch: (query: string, filters?: any) => void;
  initialQuery?: string;
  onFilterChange?: (filters: any) => void;
  onUploadClick?: () => void;
  remainingUploads?: number;
}) {
  const [query, setQuery] = useState(initialQuery);
  const [isSearching, setIsSearching] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [activeFilters, setActiveFilters] = useState(0);
  const [filters, setFilters] = useState({});

  // 🧠 NEW: AI Intelligence State
  const [debouncedQuery, setDebouncedQuery] = useState(query);
  const [queryIntelligence, setQueryIntelligence] =
    useState<SearchIntelligence | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [showIntelligence, setShowIntelligence] = useState(false);

  // 🚀 NEW: Debounced query for real-time analysis
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query);
    }, 500);

    return () => clearTimeout(timer);
  }, [query]);

  // 🧠 NEW: Real-time AI analysis
  useEffect(() => {
    if (debouncedQuery.trim().length > 3) {
      analyzeQuery(debouncedQuery);
    } else {
      setQueryIntelligence(null);
      setShowIntelligence(false);
    }
  }, [debouncedQuery]);

  // 🔥 NEW: Smart AI Query Analysis
  const analyzeQuery = useCallback(async (searchQuery: string) => {
    setIsAnalyzing(true);

    // Simulate AI processing
    await new Promise((resolve) => setTimeout(resolve, 800));

    const mockIntelligence: SearchIntelligence = {
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
    };

    setQueryIntelligence(mockIntelligence);
    setShowIntelligence(true);
    setIsAnalyzing(false);
  }, []);

  // 🎯 NEW: Extract semantic themes
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

  // 💡 NEW: Generate smart suggestions
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

  // 📈 NEW: Market insights
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

  const handleSearch = async () => {
    if (!query.trim()) return;

    setIsSearching(true);
    await onSearch(query, filters);
    setIsSearching(false);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSearch();
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

  return (
    <div className="space-y-6">
      <div className="relative">
        <div
          className="relative group"
          style={{
            background: "rgba(255,255,255,0.05)",
            backdropFilter: "blur(12px)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: "16px",
          }}
        >
          <div className="flex items-center p-4 space-x-4">
            <div className="flex-shrink-0">
              {isSearching ? (
                <div className="w-6 h-6 border-2 border-purple-400 border-t-transparent rounded-full animate-spin" />
              ) : isAnalyzing ? (
                <Brain className="w-6 h-6 text-purple-400 animate-pulse" />
              ) : (
                <Search className="w-6 h-6 text-gray-400" />
              )}
            </div>

            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Describe your ideal candidate... (AI will analyze as you type)"
              className="flex-1 bg-transparent border-0 text-white placeholder-gray-400 text-lg focus:ring-0 focus:outline-none"
            />

            <div className="flex items-center space-x-2">
              <Button
                variant="ghost"
                size="sm"
                className="text-gray-400 hover:text-white"
              >
                <Mic className="w-5 h-5" />
              </Button>

              {/* 🧠 NEW: Intelligence Toggle */}
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

          <div className="flex items-center justify-between px-4 pb-4">
            <div className="flex items-center space-x-4">
              <div className="text-xs text-gray-500">
                {query.length}/100 characters
              </div>

              {/* 🎯 NEW: Intelligence Indicator */}
              {queryIntelligence && (
                <div className="flex items-center space-x-2">
                  <div className="flex items-center space-x-1">
                    <Target className="w-3 h-3 text-purple-400" />
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
                </div>
              )}
            </div>

            <div className="flex items-center space-x-2">
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
                onClick={handleSearch}
                disabled={!query.trim() || isSearching}
                className="px-6 py-2 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 disabled:opacity-50 rounded-lg"
              >
                {isSearching ? (
                  "Searching..."
                ) : (
                  <div className="flex items-center space-x-2">
                    <Zap className="w-4 h-4" />
                    <span>Search</span>
                  </div>
                )}
              </Button>
            </div>
          </div>
        </div>

        {/* 🔥 NEW: AI Intelligence Panel */}
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
                {/* Header */}
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

                {/* Semantic Themes */}
                {queryIntelligence.semantic_themes.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-gray-300 mb-2">
                      🎯 Detected Focus Areas:
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {queryIntelligence.semantic_themes.map((theme, index) => (
                        <Badge
                          key={index}
                          className="bg-purple-500/20 text-purple-200 border-purple-400/30"
                        >
                          {theme}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Market Insights */}
                {queryIntelligence.market_insights.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-gray-300 mb-2 flex items-center">
                      <TrendingUp className="w-3 h-3 mr-1" />
                      Market Intelligence:
                    </p>
                    <div className="space-y-1">
                      {queryIntelligence.market_insights.map(
                        (insight, index) => (
                          <p
                            key={index}
                            className="text-xs text-blue-200 bg-blue-500/10 px-2 py-1 rounded border border-blue-400/20"
                          >
                            {insight}
                          </p>
                        )
                      )}
                    </div>
                  </div>
                )}

                {/* Suggestions */}
                {queryIntelligence.suggested_refinements.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-gray-300 mb-2">
                      💡 Optimization Tips:
                    </p>
                    <div className="space-y-1">
                      {queryIntelligence.suggested_refinements.map(
                        (suggestion, index) => (
                          <p
                            key={index}
                            className="text-xs text-yellow-200 bg-yellow-500/10 px-2 py-1 rounded border border-yellow-400/20"
                          >
                            {suggestion}
                          </p>
                        )
                      )}
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {showFilters && <AdvancedFilters onFiltersChange={handleFiltersChange} />}
    </div>
  );
}
