"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Candidate } from "@/lib/api";

interface CandidateListProps {
  candidates: Candidate[];
  isLoading: boolean;
  searchQuery: string;
  searchFilters: {
    location: string;
    visaStatus: string;
    minExperience: number;
    skills: string[];
  };
  onSelectCandidate: (candidate: Candidate) => void;
  searchTimeMs: number;
  totalResults: number;
}

export function CandidateList({
  candidates,
  isLoading,
  searchQuery,
  searchFilters,
  onSelectCandidate,
  searchTimeMs,
  totalResults,
}: CandidateListProps) {
  return (
    <div className="mt-8">
      <div className="flex items-center justify-between mb-4">
        <div className="text-lg font-medium">
          {totalResults} candidates found in {searchTimeMs}ms
        </div>
        {/* Add filter summary, export, etc. here if needed */}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <AnimatePresence>
          {candidates.map((candidate) => (
            <motion.div
              key={candidate.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.2 }}
              className="bg-card rounded-lg shadow p-4 cursor-pointer hover:ring-2 hover:ring-blue-500 transition"
              onClick={() => onSelectCandidate(candidate)}
            >
              {/* TODO: Replace with CandidateCard component */}
              <div className="font-bold text-lg mb-1">{candidate.name}</div>
              <div className="text-sm text-muted-foreground mb-2">
                {candidate.match_context}
              </div>
              <div className="flex flex-wrap gap-1">
                {candidate.skills?.map((skill) => (
                  <span
                    key={skill}
                    className="bg-muted px-2 py-0.5 rounded text-xs"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
