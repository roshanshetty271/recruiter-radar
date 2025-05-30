"use client";

import { useState, useEffect } from "react";
import { MetricsBar } from "@/src/components/metrics-bar";
import { HeroSection } from "@/src/components/hero-section";
import { SearchInterface } from "@/src/components/search-interface";
import { TalentHeatMap } from "@/src/components/talent-heat-map";
import { CandidateGrid } from "@/src/components/candidate-grid";
import { CommandPalette } from "@/src/components/command-palette";
import { AnimatedBackground } from "@/src/components/animated-background";
// Import our new services
import { apiService } from "../../services/apiService";
import {
  mapBackendCandidatesToFrontend,
  getSearchMetrics,
} from "../../services/helpers";
import { toast } from "@/src/hooks/use-toast";
import type { FrontendCandidate } from "../../services/types";

// Define SearchMetrics type locally
interface SearchMetrics {
  totalResults: number;
  searchTimeMs: number;
  queryInterpretation: string | null;
}

export default function Dashboard() {
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [hasSearched, setHasSearched] = useState<boolean>(false);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] =
    useState<boolean>(false);
  const [candidates, setCandidates] = useState<FrontendCandidate[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [searchMetrics, setSearchMetrics] = useState<SearchMetrics>({
    totalResults: 0,
    searchTimeMs: 0,
    queryInterpretation: null,
  });

  // Track active filters
  const [activeFilters, setActiveFilters] = useState<{
    location: string;
    visa_status: string;
    min_experience: number;
    skills: string;
  }>({
    location: "",
    visa_status: "",
    min_experience: 0,
    skills: "",
  });

  const [errorMessage, setErrorMessage] = useState<string>("");

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setIsCommandPaletteOpen(true);
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  // 🔥 NEW: Handler for generating outreach messages
  const handleGenerateOutreach = async (candidateId: string) => {
    try {
      // Find the candidate details
      const candidate = candidates.find((c) => c.id === candidateId);

      if (!candidate) {
        throw new Error("Candidate not found");
      }

      toast({
        title: "🚀 AI Outreach Generator",
        description: `Opening intelligent outreach generator for ${candidate.name}`,
      });

      // TODO: Open outreach modal when FE-6 is implemented
      console.log("Generate outreach for candidate:", {
        id: candidateId,
        name: candidate.name,
        title: candidate.title,
        skills: candidate.skills,
      });

      // Show additional AI processing toast
      setTimeout(() => {
        toast({
          title: "🧠 AI Analysis Complete",
          description: `Ready to generate personalized outreach for ${candidate.name} - ${candidate.title}`,
        });
      }, 1000);
    } catch (error) {
      console.error("Outreach generation error:", error);
      toast({
        title: "Error",
        description: "Failed to generate outreach. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleSearch = async (
    query: string,
    filters: Partial<typeof activeFilters> = {}
  ) => {
    setSearchQuery(query);
    setHasSearched(true);
    setErrorMessage(""); // Clear error on new search
    setIsLoading(true);

    try {
      // Call the API service with the query and filters
      const searchResults = await apiService.searchCandidates(query, {
        ...activeFilters,
        ...filters,
      });

      // Map the backend data to the format expected by our frontend
      const mappedCandidates = mapBackendCandidatesToFrontend(searchResults);
      setCandidates(mappedCandidates);

      // Extract and set search metrics
      const metrics = getSearchMetrics(searchResults);
      setSearchMetrics(metrics);

      setIsLoading(false);

      // Show success toast if there are results
      if (mappedCandidates.length > 0) {
        toast({
          title: "🎯 AI Search Complete",
          description: `Found ${
            metrics.totalResults
          } candidates in ${metrics.searchTimeMs.toFixed(
            2
          )}ms with intelligent matching`,
        });
      } else {
        toast({
          title: "No results found",
          description: "Try adjusting your search query or filters",
          variant: "destructive",
        });
      }
    } catch (error: any) {
      const message =
        error && error.message ? error.message : "Please try again";
      setErrorMessage(message);
      console.error("Search failed:", error);
      toast({
        title: "Search failed",
        description: message,
        variant: "destructive",
      });
      setIsLoading(false);
    }
  };

  // Handler for filter changes
  const handleFilterChange = (filters: Partial<typeof activeFilters>) => {
    setActiveFilters({ ...activeFilters, ...filters });

    // If we've already searched, rerun the search with new filters
    if (hasSearched && searchQuery) {
      handleSearch(searchQuery, filters);
    }
  };

  return (
    <div className="min-h-screen relative overflow-hidden">
      <AnimatedBackground />

      <div className="relative z-10">
        {errorMessage && (
          <div
            className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4"
            role="alert"
          >
            <span className="block sm:inline">{errorMessage}</span>
            <button
              className="absolute top-0 bottom-0 right-0 px-4 py-3"
              onClick={() => setErrorMessage("")}
              aria-label="Close"
            >
              <span aria-hidden="true">&times;</span>
            </button>
          </div>
        )}
        <MetricsBar
          totalSearches={hasSearched ? 1 : 0}
          totalResults={searchMetrics.totalResults}
          searchTimeMs={searchMetrics.searchTimeMs}
        />

        <main className="container mx-auto px-4 pt-20">
          {!hasSearched ? (
            <HeroSection onSearch={handleSearch} />
          ) : (
            <div className="space-y-8">
              <SearchInterface
                onSearch={handleSearch}
                initialQuery={searchQuery}
                onFilterChange={handleFilterChange}
              />

              <div className="grid lg:grid-cols-4 gap-8">
                <div className="lg:col-span-1">
                  <TalentHeatMap />
                </div>
                <div className="lg:col-span-3">
                  <CandidateGrid
                    candidates={candidates.map((c) => ({
                      ...c,
                      distance: c.distance ?? "",
                      experience: c.experience ?? 0,
                    }))}
                    isLoading={isLoading}
                    searchQuery={searchQuery}
                    onGenerateOutreach={handleGenerateOutreach}
                  />
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onSearch={handleSearch}
      />
    </div>
  );
}
