"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Badge } from "../ui/badge";
import { SearchMode } from "../search-interface";

interface QuerySuggestionsProps {
  mode: SearchMode;
  onSuggestionClick: (suggestion: string) => void;
  visible?: boolean;
}

const searchSuggestions = [
  "Senior Python developers",
  "Frontend engineers with React",
  "Full-stack developers in San Francisco",
  "Machine learning engineers 5+ years",
  "DevOps engineers remote",
  "Mobile app developers iOS Swift",
];

const chatSuggestions = [
  "Show me Python developers with 5+ years experience",
  "Find frontend engineers who know React and TypeScript",
  "Who are the most senior candidates?",
  "Which candidates have machine learning experience?",
  "Show me remote candidates in US timezone",
  "Find candidates with startup experience",
];

export function QuerySuggestions({
  mode,
  onSuggestionClick,
  visible = true,
}: QuerySuggestionsProps) {
  const suggestions = mode === "search" ? searchSuggestions : chatSuggestions;

  if (!visible) return null;

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 10 }}
          transition={{ duration: 0.2 }}
          className="mt-4"
        >
          <div className="text-xs text-gray-400 mb-2">
            {mode === "search" ? "Try searching for:" : "Try asking:"}
          </div>

          <div className="flex flex-wrap gap-2">
            {suggestions.map((suggestion, index) => (
              <motion.div
                key={suggestion}
                initial={{ opacity: 0, scale: 0.9 }}
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
                    cursor-pointer 
                    px-3 py-1 
                    bg-white/5 
                    border-white/20 
                    text-gray-300 
                    hover:bg-white/10 
                    hover:border-purple-400/50 
                    hover:text-white 
                    transition-all 
                    duration-200
                    text-xs
                  "
                  onClick={() => onSuggestionClick(suggestion)}
                >
                  {suggestion}
                </Badge>
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
