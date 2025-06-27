"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Badge } from "../ui/badge";
import { Sparkles, MessageCircle } from "lucide-react";

interface QuerySuggestionsProps {
  onSuggestionClick: (suggestion: string) => void;
  visible?: boolean;
}

// 🚀 Chat-First Suggestions - Natural language recruiting queries
const conversationalSuggestions = [
  "Show me senior Python developers with 5+ years experience",
  "Find React engineers who know TypeScript",
  "Who are my best machine learning candidates?",
  "Show me full-stack developers in California",
  "Find remote candidates who can start immediately",
  "Which candidates have startup experience?",
  "Show me AI engineers with TensorFlow skills",
  "Find senior engineers open to remote work",
];

// 🎯 Quick action suggestions for follow-up queries
const quickRefinements = [
  "More senior candidates",
  "Remote workers only",
  "California based",
  "Startup experience",
  "Available immediately",
  "5+ years experience",
];

export function QuerySuggestions({
  onSuggestionClick,
  visible = true,
}: QuerySuggestionsProps) {
  if (!visible) return null;

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 10 }}
          transition={{ duration: 0.3 }}
          className="space-y-4"
        >
          {/* Header */}
          <div className="flex items-center space-x-2">
            <MessageCircle className="w-4 h-4 text-purple-400" />
            <span className="text-sm text-gray-300 font-medium">
              Get started with AI search
            </span>
          </div>

          {/* Main conversational suggestions */}
          <div>
            <div className="text-xs text-gray-400 mb-3">
              💬 Try asking me naturally:
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {conversationalSuggestions.map((suggestion, index) => (
                <motion.div
                  key={suggestion}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{
                    duration: 0.2,
                    delay: index * 0.05,
                    ease: "easeOut",
                  }}
                >
                  <Badge
                    variant="outline"
                    className="
                      w-full
                      justify-start
                      cursor-pointer 
                      px-4 py-2
                      bg-white/5 
                      border-white/20 
                      text-gray-300 
                      hover:bg-purple-600/20
                      hover:border-purple-400/50 
                      hover:text-white 
                      transition-all 
                      duration-200
                      text-xs
                      h-auto
                      whitespace-normal
                    "
                    onClick={() => onSuggestionClick(suggestion)}
                  >
                    {suggestion}
                  </Badge>
                </motion.div>
              ))}
            </div>
          </div>

          {/* Quick refinements */}
          <div>
            <div className="flex items-center space-x-2 mb-3">
              <Sparkles className="w-3 h-3 text-purple-400" />
              <div className="text-xs text-gray-400">Or quick filters:</div>
            </div>
            <div className="flex flex-wrap gap-2">
              {quickRefinements.map((refinement, index) => (
                <motion.div
                  key={refinement}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{
                    duration: 0.2,
                    delay: 0.4 + index * 0.03,
                    ease: "easeOut",
                  }}
                >
                  <Badge
                    variant="outline"
                    className="
                      cursor-pointer 
                      px-3 py-1 
                      bg-purple-600/10
                      border-purple-400/30 
                      text-purple-300 
                      hover:bg-purple-600/20
                      hover:border-purple-400/50 
                      hover:text-purple-200 
                      transition-all 
                      duration-200
                      text-xs
                    "
                    onClick={() => onSuggestionClick(refinement)}
                  >
                    {refinement}
                  </Badge>
                </motion.div>
              ))}
            </div>
          </div>

          {/* Helpful tip */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3, delay: 0.8 }}
            className="text-xs text-gray-500 text-center"
          >
            💡{" "}
            <span className="text-gray-400">
              Tip: Be specific! "Senior Python developers in SF with startup
              experience" works great
            </span>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
