"use client";

import { motion } from "framer-motion";
import { useRecruiterStore } from "@/stores/recruiter-store";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import { MetricsBar } from "@/components/custom/MetricsBar";
import { HeroSection } from "@/components/custom/HeroSection";
import { SearchInterface } from "@/components/custom/SearchInterface";
import { CandidateList } from "@/components/custom/CandidateList";
import { LocationHeatMap } from "@/components/custom/LocationHeatMap";
import { CommandPalette } from "@/components/custom/CommandPalette";
import { OutreachModal } from "@/components/custom/OutreachModal";
import { EmptyState } from "@/components/custom/EmptyState";
import { api } from "@/lib/api";

export default function TalentPage() {
  const store = useRecruiterStore();

  // Keyboard shortcuts
  useKeyboardShortcuts({
    "cmd+k": () => store.toggleCommandPalette(),
    "ctrl+k": () => store.toggleCommandPalette(),
    "/": () => {
      const searchInput = document.getElementById("main-search");
      searchInput?.focus();
    },
    escape: () => {
      if (store.showOutreachModal) {
        store.setShowOutreachModal(false);
      }
      if (store.showCommandPalette) {
        store.toggleCommandPalette();
      }
    },
  });

  // Handle search
  const handleSearch = async () => {
    if (!store.searchQuery.trim()) return;

    store.incrementSearch();
    store.addRecentSearch(store.searchQuery);

    try {
      const response = await api.searchCandidates(store.searchQuery, {
        ...store.searchFilters,
        skills: store.searchFilters.skills.join(","),
        onProgress: store.setSearchProgress,
      });

      store.setCandidates(
        response.results,
        response.total_results,
        response.search_time_ms
      );
    } catch (error) {
      console.error("Search failed:", error);
      store.setSearchProgress("❌ Search failed, please try again");
    }
  };

  // Calculate session duration
  const sessionDuration = Math.floor(
    (Date.now() - store.sessionStart.getTime()) / 1000
  );

  return (
    <>
      {/* Metrics Bar - Always visible */}
      <MetricsBar
        sessionDuration={sessionDuration}
        totalSearches={store.totalSearches}
        outreachGenerated={store.outreachGenerated}
        candidatesViewed={store.candidatesViewed.size}
        estimatedTimeSaved={store.estimatedTimeSaved}
      />

      {/* Main Content */}
      <main className="relative z-10 container mx-auto px-4 py-8">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          {/* Hero Section - Only show when no searches yet */}
          {store.totalSearches === 0 && (
            <HeroSection
              onExampleClick={(query: string) => {
                store.setSearchQuery(query);
                handleSearch();
              }}
            />
          )}

          {/* Search Interface - The Command Center */}
          <SearchInterface
            value={store.searchQuery}
            onChange={store.setSearchQuery}
            filters={store.searchFilters}
            onFiltersChange={store.setSearchFilters}
            onSearch={handleSearch}
            isSearching={store.isSearching}
            searchProgress={store.searchProgress}
            recentSearches={store.recentSearches}
          />

          {/* Location Heat Map - Show when we have results */}
          {store.candidates.length > 0 && <LocationHeatMap />}

          {/* Results or Empty State */}
          {store.totalSearches > 0 &&
            (store.candidates.length > 0 ? (
              <CandidateList
                candidates={store.candidates}
                isLoading={store.isSearching}
                searchQuery={store.searchQuery}
                searchFilters={store.searchFilters}
                onSelectCandidate={(candidate) => {
                  store.viewCandidate(candidate.id);
                  store.selectCandidate(candidate);
                }}
                searchTimeMs={store.searchTimeMs}
                totalResults={store.totalResults}
              />
            ) : (
              !store.isSearching && <EmptyState query={store.searchQuery} />
            ))}
        </motion.div>
      </main>

      {/* Command Palette */}
      <CommandPalette
        open={store.showCommandPalette}
        onOpenChange={store.toggleCommandPalette}
        recentSearches={store.recentSearches}
        onSearch={(query: string) => {
          store.setSearchQuery(query);
          handleSearch();
          store.toggleCommandPalette();
        }}
      />

      {/* Outreach Modal */}
      <OutreachModal
        candidate={store.selectedCandidate}
        open={store.showOutreachModal}
        onOpenChange={store.setShowOutreachModal}
        onGenerated={store.incrementOutreach}
      />
    </>
  );
}
