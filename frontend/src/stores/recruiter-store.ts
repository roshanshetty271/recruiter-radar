import { create } from "zustand";
import { devtools } from "zustand/middleware";
import type { Candidate } from "@/lib/api";

interface RecruiterState {
  // Search State
  searchQuery: string;
  searchFilters: {
    location: string;
    visaStatus: string;
    minExperience: number;
    skills: string[];
  };
  isSearching: boolean;
  searchProgress: string;

  // Results State
  candidates: Candidate[];
  totalResults: number;
  searchTimeMs: number;

  // Session Metrics
  sessionStart: Date;
  totalSearches: number;
  outreachGenerated: number;
  candidatesViewed: Set<string>;
  estimatedTimeSaved: number;

  // UI State
  selectedCandidate: Candidate | null;
  showOutreachModal: boolean;
  showCommandPalette: boolean;
  recentSearches: string[];

  // Actions
  setSearchQuery: (query: string) => void;
  setSearchFilters: (filters: Partial<RecruiterState["searchFilters"]>) => void;
  setSearchProgress: (progress: string) => void;
  setCandidates: (
    candidates: Candidate[],
    totalResults: number,
    searchTimeMs: number
  ) => void;
  selectCandidate: (candidate: Candidate) => void;
  incrementSearch: () => void;
  incrementOutreach: () => void;
  viewCandidate: (candidateId: string) => void;
  toggleCommandPalette: () => void;
  addRecentSearch: (query: string) => void;
  setShowOutreachModal: (show: boolean) => void;
}

export const useRecruiterStore = create<RecruiterState>()(
  devtools(
    (set) => ({
      // Initial State
      searchQuery: "",
      searchFilters: {
        location: "",
        visaStatus: "",
        minExperience: 0,
        skills: [],
      },
      isSearching: false,
      searchProgress: "",
      candidates: [],
      totalResults: 0,
      searchTimeMs: 0,
      sessionStart: new Date(),
      totalSearches: 0,
      outreachGenerated: 0,
      candidatesViewed: new Set(),
      estimatedTimeSaved: 0,
      selectedCandidate: null,
      showOutreachModal: false,
      showCommandPalette: false,
      recentSearches: [],

      // Actions
      setSearchQuery: (query) => set({ searchQuery: query }),

      setSearchFilters: (filters) =>
        set((state) => ({
          searchFilters: { ...state.searchFilters, ...filters },
        })),

      setSearchProgress: (progress) =>
        set({
          searchProgress: progress,
          isSearching: progress !== "",
        }),

      setCandidates: (candidates, totalResults, searchTimeMs) =>
        set({
          candidates,
          totalResults,
          searchTimeMs,
          isSearching: false,
          searchProgress: "",
        }),

      selectCandidate: (candidate) =>
        set({
          selectedCandidate: candidate,
          showOutreachModal: true,
        }),

      incrementSearch: () =>
        set((state) => ({
          totalSearches: state.totalSearches + 1,
          estimatedTimeSaved: state.estimatedTimeSaved + 15,
        })),

      incrementOutreach: () =>
        set((state) => ({
          outreachGenerated: state.outreachGenerated + 1,
          estimatedTimeSaved: state.estimatedTimeSaved + 30,
        })),

      viewCandidate: (candidateId) =>
        set((state) => ({
          candidatesViewed: new Set([...state.candidatesViewed, candidateId]),
        })),

      toggleCommandPalette: () =>
        set((state) => ({
          showCommandPalette: !state.showCommandPalette,
        })),

      addRecentSearch: (query) =>
        set((state) => ({
          recentSearches: [
            query,
            ...state.recentSearches.filter((q) => q !== query),
          ].slice(0, 5),
        })),

      setShowOutreachModal: (show) => set({ showOutreachModal: show }),
    }),
    {
      name: "recruiter-store",
    }
  )
);
