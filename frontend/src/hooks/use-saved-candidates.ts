import { useState, useEffect } from "react";

export interface SavedCandidate {
  id: string;
  name: string;
  skills: string[];
  experience_years: number;
  location?: string;
  savedAt: string;
  notes?: string;
}

export function useSavedCandidates() {
  const [savedCandidates, setSavedCandidates] = useState<SavedCandidate[]>([]);

  // Load saved candidates from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem("saved-candidates");
    if (saved) {
      try {
        setSavedCandidates(JSON.parse(saved));
      } catch (error) {
        console.error("Failed to parse saved candidates:", error);
        setSavedCandidates([]);
      }
    }
  }, []);

  // Save to localStorage whenever savedCandidates changes
  useEffect(() => {
    localStorage.setItem("saved-candidates", JSON.stringify(savedCandidates));
  }, [savedCandidates]);

  const saveCandidate = (candidate: Omit<SavedCandidate, "savedAt">) => {
    const newSavedCandidate: SavedCandidate = {
      ...candidate,
      savedAt: new Date().toISOString(),
    };

    setSavedCandidates((prev) => {
      // Check if already saved
      if (prev.some((c) => c.id === candidate.id)) {
        return prev;
      }
      return [...prev, newSavedCandidate];
    });
  };

  const removeCandidate = (candidateId: string) => {
    setSavedCandidates((prev) => prev.filter((c) => c.id !== candidateId));
  };

  const isSaved = (candidateId: string) => {
    return savedCandidates.some((c) => c.id === candidateId);
  };

  const clearAll = () => {
    setSavedCandidates([]);
  };

  return {
    savedCandidates,
    saveCandidate,
    removeCandidate,
    isSaved,
    clearAll,
    count: savedCandidates.length,
  };
}
