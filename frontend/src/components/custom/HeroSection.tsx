"use client";

import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface HeroSectionProps {
  onExampleClick: (query: string) => void;
}

const exampleQueries = [
  "Senior Python developer with FastAPI",
  "React engineer with 5+ years",
  "DevOps expert with Kubernetes",
  "Full stack developer in San Francisco",
];

export function HeroSection({ onExampleClick }: HeroSectionProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="text-center mb-12"
    >
      <Badge variant="outline" className="glass mb-4">
        <Sparkles className="w-3 h-3 mr-1" />
        AI-Powered Talent Discovery
      </Badge>

      <h1 className="text-5xl md:text-6xl font-bold mb-4">
        Find your next <span className="gradient-text">$1M engineer</span> in
        0.8 seconds
      </h1>

      <p className="text-lg text-muted-foreground mb-8 max-w-2xl mx-auto">
        Our AI analyzes thousands of candidates instantly, finding perfect
        matches that traditional search would miss. Save hours, hire better.
      </p>

      <div className="flex flex-wrap gap-2 justify-center">
        <p className="text-sm text-muted-foreground w-full mb-2">
          Try an example search:
        </p>
        {exampleQueries.map((query) => (
          <Button
            key={query}
            variant="outline"
            size="sm"
            className="glass"
            onClick={() => onExampleClick(query)}
          >
            {query}
          </Button>
        ))}
      </div>
    </motion.div>
  );
}
