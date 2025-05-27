"use client";

import { motion } from "framer-motion";
import { Search, Lightbulb } from "lucide-react";
import { Button } from "@/components/ui/button";

interface EmptyStateProps {
  query: string;
}

export function EmptyState({ query }: EmptyStateProps) {
  const suggestions = [
    "Try broadening your search terms",
    "Check for typos in your query",
    "Remove some filters to see more results",
    `Try searching for "${query.split(" ")[0]}" without other terms`,
  ];

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="text-center py-12"
    >
      <motion.div
        animate={{ rotate: [0, 10, -10, 0], scale: [1, 1.1, 1] }}
        transition={{ duration: 0.5 }}
        className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-muted mb-4"
      >
        <Search className="w-8 h-8 text-muted-foreground" />
      </motion.div>

      <h3 className="text-lg font-medium mb-2">No matches found</h3>
      <p className="text-muted-foreground mb-6">
        We couldn't find any candidates matching "{query}"
      </p>

      <div className="glass rounded-lg p-4 max-w-md mx-auto mb-6">
        <div className="flex items-center gap-2 mb-3">
          <Lightbulb className="w-4 h-4 text-yellow-500" />
          <span className="text-sm font-medium">Suggestions</span>
        </div>
        <ul className="space-y-2 text-sm text-left">
          {suggestions.map((suggestion, i) => (
            <motion.li
              key={i}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.1 }}
              className="flex items-start gap-2"
            >
              <span className="text-muted-foreground">•</span>
              <span>{suggestion}</span>
            </motion.li>
          ))}
        </ul>
      </div>

      <Button variant="outline" className="glass">
        Clear filters and try again
      </Button>
    </motion.div>
  );
}
