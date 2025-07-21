"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertCircle,
  CheckCircle,
  Info,
  Lightbulb,
  TrendingUp,
  Search,
  Filter,
  MapPin,
  Users,
} from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface ProgressiveSearchFeedbackProps {
  searchMetadata?: {
    search_metadata_legacy?: {
      search_strategy?: string;
      fallback_level?: number;
      search_insights?: {
        search_effectiveness?: string;
        optimization_tips?: string[];
      };
    };
    search_metadata?: {
      suggested_refinements?: string[];
      ai_confidence?: number;
    };
  };
  resultCount: number;
  isVisible: boolean;
}

export function ProgressiveSearchFeedback({
  searchMetadata,
  resultCount,
  isVisible,
}: ProgressiveSearchFeedbackProps) {
  if (!isVisible || !searchMetadata) return null;

  const legacy = searchMetadata.search_metadata_legacy || {};
  const metadata = searchMetadata.search_metadata || {};

  const fallbackLevel = legacy.fallback_level || 0;
  const searchStrategy = legacy.search_strategy || "exact_match";
  const suggestions = metadata.suggested_refinements || [];
  const aiConfidence = metadata.ai_confidence || 0.8;
  const effectiveness = legacy.search_insights?.search_effectiveness || "good";
  const optimizationTips = legacy.search_insights?.optimization_tips || [];

  // Don't show if it's a perfect exact match with good results
  if (fallbackLevel === 0 && resultCount > 5 && suggestions.length === 0) {
    return null;
  }

  const getStrategyInfo = () => {
    switch (searchStrategy) {
      case "exact_match":
        return {
          icon: CheckCircle,
          color: "text-green-400",
          bgColor: "bg-green-500/10",
          borderColor: "border-green-400/20",
          title: "Perfect Match",
          description: "Found candidates matching all your criteria exactly",
        };
      case "relaxed_location":
        return {
          icon: MapPin,
          color: "text-blue-400",
          bgColor: "bg-blue-500/10",
          borderColor: "border-blue-400/20",
          title: "Expanded Location Search",
          description: "Broadened location search to find more candidates",
        };
      case "core_skills_only":
        return {
          icon: Filter,
          color: "text-purple-400",
          bgColor: "bg-purple-500/10",
          borderColor: "border-purple-400/20",
          title: "Core Skills Focus",
          description:
            "Focused on essential skills to find relevant candidates",
        };
      case "essential_match":
        return {
          icon: Search,
          color: "text-yellow-400",
          bgColor: "bg-yellow-500/10",
          borderColor: "border-yellow-400/20",
          title: "Essential Match",
          description: "Relaxed some filters to find potential candidates",
        };
      case "broad_search":
        return {
          icon: Users,
          color: "text-orange-400",
          bgColor: "bg-orange-500/10",
          borderColor: "border-orange-400/20",
          title: "Broad Search",
          description:
            "Used very broad criteria to find any relevant candidates",
        };
      default:
        return {
          icon: Info,
          color: "text-gray-400",
          bgColor: "bg-gray-500/10",
          borderColor: "border-gray-400/20",
          title: "Smart Search",
          description: "Used intelligent search strategies",
        };
    }
  };

  const getEffectivenessColor = () => {
    switch (effectiveness) {
      case "excellent":
        return "text-green-400";
      case "good":
        return "text-blue-400";
      case "moderate":
        return "text-yellow-400";
      case "challenging":
        return "text-red-400";
      default:
        return "text-gray-400";
    }
  };

  const strategyInfo = getStrategyInfo();
  const StrategyIcon = strategyInfo.icon;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        transition={{ duration: 0.3 }}
        className="space-y-3"
      >
        {/* Search Strategy Feedback */}
        {fallbackLevel > 0 && (
          <Alert
            className={`${strategyInfo.bgColor} ${strategyInfo.borderColor} border`}
          >
            <StrategyIcon className={`h-4 w-4 ${strategyInfo.color}`} />
            <AlertDescription className="flex items-center justify-between">
              <div>
                <span className="font-medium text-white">
                  {strategyInfo.title}
                </span>
                <p className="text-sm text-gray-300 mt-1">
                  {strategyInfo.description}
                </p>
              </div>
              <Badge variant="secondary" className="ml-2">
                Level {fallbackLevel}
              </Badge>
            </AlertDescription>
          </Alert>
        )}

        {/* AI Confidence & Effectiveness */}
        {(aiConfidence < 0.8 || effectiveness !== "excellent") && (
          <div className="flex items-center space-x-4 p-3 bg-gray-500/5 rounded-lg border border-gray-400/20">
            <TrendingUp className={`h-4 w-4 ${getEffectivenessColor()}`} />
            <div className="flex-1">
              <div className="flex items-center space-x-2">
                <span className="text-sm font-medium text-white">
                  Search Quality:
                </span>
                <Badge
                  variant="outline"
                  className={`${getEffectivenessColor()}`}
                >
                  {effectiveness.charAt(0).toUpperCase() +
                    effectiveness.slice(1)}
                </Badge>
                <span className="text-xs text-gray-400">
                  ({Math.round(aiConfidence * 100)}% confidence)
                </span>
              </div>
              {optimizationTips.length > 0 && (
                <p className="text-xs text-gray-300 mt-1">
                  {optimizationTips[0]}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Intelligent Suggestions */}
        {suggestions.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            className="space-y-2"
          >
            <div className="flex items-center space-x-2">
              <Lightbulb className="h-4 w-4 text-yellow-400" />
              <span className="text-sm font-medium text-white">
                💡 Smart Suggestions:
              </span>
            </div>

            <div className="grid gap-2">
              {suggestions.slice(0, 3).map((suggestion, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="flex items-start space-x-2 p-2 bg-yellow-500/5 rounded border border-yellow-400/20"
                >
                  <div className="w-1.5 h-1.5 bg-yellow-400 rounded-full mt-2 flex-shrink-0" />
                  <p className="text-xs text-yellow-200 flex-1">{suggestion}</p>
                </motion.div>
              ))}

              {suggestions.length > 3 && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-xs text-yellow-400 hover:text-yellow-300 h-6"
                >
                  Show {suggestions.length - 3} more suggestions...
                </Button>
              )}
            </div>
          </motion.div>
        )}

        {/* No Results Specific Feedback */}
        {resultCount === 0 && (
          <Alert className="bg-red-500/10 border-red-400/20 border">
            <AlertCircle className="h-4 w-4 text-red-400" />
            <AlertDescription>
              <div className="space-y-2">
                <span className="font-medium text-white">
                  No candidates found
                </span>
                <p className="text-sm text-gray-300">
                  We tried progressively broader searches but couldn't find
                  matching candidates. Try the suggestions above or consider
                  different search terms.
                </p>
              </div>
            </AlertDescription>
          </Alert>
        )}
      </motion.div>
    </AnimatePresence>
  );
}
