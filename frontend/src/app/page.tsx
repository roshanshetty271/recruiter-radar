"use client";

import { useState, useEffect } from "react";
import { MetricsBar } from "@/components/metrics-bar";
import { SearchInterface } from "@/components/search-interface";
import { TalentHeatMap } from "@/components/talent-heat-map";
import { CandidateGrid } from "@/components/candidate-grid";
import { CommandPalette } from "@/components/command-palette";
import { AnimatedBackground } from "@/components/animated-background";
import { OutreachModal } from "@/components/custom/outreach-modal"; // FE-6 IMPORT
import { ResumeUpload } from "@/components/custom/resume-upload"; // Upload component
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Search, Upload, Star } from "lucide-react";
// Import our services
import { apiService } from "@/services/apiService";
import {
  mapBackendCandidatesToFrontend,
  getSearchMetrics,
} from "../services/helpers";
import { toast } from "@/hooks/use-toast";
import type { FrontendCandidate } from "../lib/types";
import { CandidatePagination } from "@/components/candidate-pagination";
import type { PaginationInfo } from "@/lib/types";
import { useSavedCandidates } from "@/hooks/use-saved-candidates";

// Define SearchMetrics type locally
interface SearchMetrics {
  totalResults: number;
  searchTimeMs: number;
  queryInterpretation: string | null;
}

// Session metrics interface
interface SessionMetrics {
  totalSearches: number;
  candidatesViewed: number;
  outreachGenerated: number;
  timeSpent: number;
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

  // Saved candidates functionality
  const { savedCandidates } = useSavedCandidates();
  const [showSavedCandidates, setShowSavedCandidates] =
    useState<boolean>(false);

  // FE-6: Outreach modal state
  const [isOutreachModalOpen, setIsOutreachModalOpen] = useState(false);
  const [selectedCandidateForOutreach, setSelectedCandidateForOutreach] =
    useState<FrontendCandidate | null>(null);

  // Session metrics state
  const [sessionMetrics, setSessionMetrics] = useState<SessionMetrics>({
    totalSearches: 0,
    candidatesViewed: 0,
    outreachGenerated: 0,
    timeSpent: 0,
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

  // 📄 PAGINATION STATE
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(20);
  const [paginationInfo, setPaginationInfo] = useState<PaginationInfo | null>(
    null
  );

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

  // Handle URL parameters for OAuth returns
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const candidateId = urlParams.get("candidate");
    const action = urlParams.get("action");
    const gmailStatus = urlParams.get("gmail");
    const errorStatus = urlParams.get("error");

    if (candidateId && action === "outreach") {
      // Search for the specific candidate and open outreach modal
      const searchForCandidate = async () => {
        try {
          setIsLoading(true);
          // Use a broad search to find candidates, then filter by ID
          const response = await apiService.searchCandidates("", {
            page: 1,
            page_size: 50,
          });

          // Map candidates and update state the same way as handleSearch does
          const mappedCandidates = mapBackendCandidatesToFrontend(response);
          setCandidates(mappedCandidates);

          // NEW ➜ Update search metrics & pagination so header counts are correct
          const metrics = getSearchMetrics(response);
          setSearchMetrics({
            totalResults: metrics.totalResults || mappedCandidates.length,
            searchTimeMs: metrics.searchTimeMs || 0,
            queryInterpretation: metrics.queryInterpretation,
          });

          if (response.pagination) {
            setPaginationInfo(response.pagination);
          }

          const targetCandidate = mappedCandidates.find(
            (c) => c.id === candidateId
          );

          if (targetCandidate) {
            setSelectedCandidateForOutreach(targetCandidate);
            setIsOutreachModalOpen(true);
            setHasSearched(true);

            // Show appropriate toast based on Gmail status
            if (gmailStatus === "connected") {
              toast({
                title: "🎉 Gmail Connected!",
                description: `Your message to ${targetCandidate.name} will be sent automatically.`,
              });
            } else if (errorStatus) {
              const errorMessages = {
                auth_failed:
                  "Gmail connection was cancelled. You can still copy your message.",
                connection_failed:
                  "Gmail connection failed. You can still copy your message.",
              } as const;
              toast({
                title: "Connection Issue",
                description:
                  errorMessages[errorStatus as keyof typeof errorMessages] ||
                  "There was an issue with Gmail connection.",
                variant: "destructive",
              });
            } else {
              // Just opened the modal after OAuth redirect
              toast({
                title: "Welcome Back!",
                description: `Continuing your outreach to ${targetCandidate.name}`,
              });
            }
          }
        } catch (error) {
          console.error("Failed to find candidate:", error);
          toast({
            title: "Candidate Not Found",
            description: "Could not find the candidate you were working with.",
            variant: "destructive",
          });
        } finally {
          setIsLoading(false);
          // Clean up URL parameters
          window.history.replaceState({}, "", window.location.pathname);
        }
      };

      searchForCandidate();
    }
  }, []);

  // Handle saved candidates view toggle
  const handleSavedClick = () => {
    setShowSavedCandidates(!showSavedCandidates);
    if (!showSavedCandidates && savedCandidates.length > 0) {
      // Convert saved candidates to frontend format for display
      const savedAsFrontend: FrontendCandidate[] = savedCandidates.map(
        (saved) => ({
          id: saved.id,
          name: saved.name,
          title: "Saved Candidate", // Required field
          skills: saved.skills,
          experience: saved.experience_years,
          location: saved.location || "Not specified",
          matchScore: 1.0, // High relevance for saved candidates
          isOnline: false, // Default value
          isVerified: true, // Assume saved candidates are verified
          avatar: "/placeholder-user.jpg", // Default avatar
          distance: "",
          visaStatus: "Not specified",
          githubUrl: "",
          linkedinUrl: "",
        })
      );
      setCandidates(savedAsFrontend);
      setHasSearched(true);

      toast({
        title: "⭐ Saved Candidates",
        description: `Showing ${savedCandidates.length} saved candidates`,
      });
    } else if (showSavedCandidates) {
      // Reset to normal view
      setCandidates([]);
      setHasSearched(false);

      toast({
        title: "🔍 Search Mode",
        description: "Back to search interface",
      });
    } else {
      toast({
        title: "📝 No Saved Candidates",
        description: "Save candidates from search results to see them here",
      });
    }
  };

  // FE-6: Updated handler for generating outreach messages
  const handleGenerateOutreach = async (candidateId: string) => {
    try {
      // Find the candidate details
      const candidate = candidates.find((c) => c.id === candidateId);

      if (!candidate) {
        throw new Error("Candidate not found");
      }

      // Set selected candidate and open modal
      setSelectedCandidateForOutreach(candidate);
      setIsOutreachModalOpen(true);

      toast({
        title: "🚀 AI Outreach Generator",
        description: `Opening intelligent outreach generator for ${candidate.name}`,
      });
    } catch (error) {
      console.error("Outreach generation error:", error);
      toast({
        title: "Error",
        description: "Failed to open outreach generator. Please try again.",
        variant: "destructive",
      });
    }
  };

  // FE-6: Handle outreach success
  const handleOutreachSuccess = () => {
    setSessionMetrics((prev) => ({
      ...prev,
      outreachGenerated: prev.outreachGenerated + 1,
    }));

    // Note: Specific toast messages are now handled within OutreachModal
    // This function just updates session metrics
  };

  const handleSearch = async (
    query: string,
    filters: Partial<typeof activeFilters> = {},
    page: number = 1,
    resetPagination: boolean = true
  ) => {
    // Exit saved candidates view when searching
    setShowSavedCandidates(false);

    setSearchQuery(query);
    setHasSearched(true);
    setErrorMessage(""); // Clear error on new search
    setIsLoading(true);

    // Reset to page 1 for new searches, keep current page for pagination navigation
    const targetPage = resetPagination ? 1 : page;
    if (resetPagination) {
      setCurrentPage(1);
    }

    // Only update session metrics for NEW searches, not pagination
    if (resetPagination) {
      setSessionMetrics((prev) => ({
        ...prev,
        totalSearches: prev.totalSearches + 1,
      }));
    }

    try {
      // Call the API service with the query, filters, and pagination
      const searchResults = await apiService.searchCandidates(query, {
        ...activeFilters,
        ...filters,
        page: targetPage,
        page_size: pageSize,
      } as any);

      // Map the backend data to the format expected by our frontend
      const mappedCandidates = mapBackendCandidatesToFrontend(searchResults);
      setCandidates(mappedCandidates);

      // Extract and set search metrics with defaults
      const metrics = getSearchMetrics(searchResults);
      setSearchMetrics({
        totalResults: metrics.totalResults || 0,
        searchTimeMs: metrics.searchTimeMs || 0,
        queryInterpretation: metrics.queryInterpretation || null,
      });

      // 📄 SET PAGINATION INFO
      if (searchResults.pagination) {
        setPaginationInfo(searchResults.pagination);
        setCurrentPage(searchResults.pagination.current_page);
      }

      setIsLoading(false);

      // 🔧 FIX: Only show toast for NEW searches, not pagination
      // 🔧 FIX: Show total results count, not page results count
      if (resetPagination && mappedCandidates.length > 0) {
        const timeStr = metrics.searchTimeMs
          ? `${metrics.searchTimeMs.toFixed(2)}ms`
          : "lightning fast";

        toast({
          title: "🎯 AI Search Complete",
          description: `Found ${
            metrics.totalResults ||
            searchResults.pagination?.total_candidates ||
            mappedCandidates.length
          } candidates in ${timeStr}`,
        });
      } else if (resetPagination && mappedCandidates.length === 0) {
        toast({
          title: "🔍 No Results",
          description: "Try adjusting your search terms or filters",
          variant: "destructive",
        });
      }

      // 🔧 FIX: Auto-scroll to candidate grid on pagination (not new searches)
      if (!resetPagination) {
        // Scroll to candidate results header (includes "Found X candidates" text)
        setTimeout(() => {
          // Use the ID selector for most reliable targeting
          const resultsHeader = document.getElementById(
            "candidate-results-header"
          );

          if (resultsHeader) {
            // Get the header position and add offset for better visibility
            const headerRect = resultsHeader.getBoundingClientRect();
            const offsetTop = window.pageYOffset + headerRect.top - 120; // 120px from top for better view

            window.scrollTo({
              top: Math.max(0, offsetTop), // Ensure we don't scroll above page top
              behavior: "smooth",
            });
          }
        }, 200); // Enough time for content to render
      }
    } catch (error) {
      console.error("Search error:", error);
      setIsLoading(false);
      setErrorMessage(
        error instanceof Error ? error.message : "An unexpected error occurred"
      );

      // Only show error toast for NEW searches
      if (resetPagination) {
        toast({
          title: "❌ Search Error",
          description: "Failed to search candidates. Please try again.",
          variant: "destructive",
        });
      }
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

  // 📄 PAGINATION HANDLERS
  const handlePageChange = (page: number) => {
    if (searchQuery && paginationInfo) {
      setCurrentPage(page);
      handleSearch(searchQuery, activeFilters, page, false);
    }
  };

  const handlePageSizeChange = async (newPageSize: number) => {
    // Update page size immediately
    setPageSize(newPageSize);
    setCurrentPage(1); // Reset to page 1

    // Trigger search with new page size if we have a query
    if (searchQuery) {
      await handleSearch(searchQuery, activeFilters, 1, true);
    }
  };

  const handleLoadMore = () => {
    if (paginationInfo?.has_next) {
      handlePageChange(currentPage + 1);
    }
  };

  const handleExportAll = async () => {
    toast({
      title: "🚀 Export Feature",
      description:
        "Export functionality coming soon! This will download all search results as CSV.",
    });
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
          totalSearches={sessionMetrics.totalSearches}
          totalResults={searchMetrics.totalResults}
          searchTimeMs={searchMetrics.searchTimeMs}
          outreachGenerated={sessionMetrics.outreachGenerated}
          onSavedClick={handleSavedClick}
        />

        <main className="container mx-auto px-4">
          {/* Hero Header - Always Visible */}
          <div className="text-center space-y-6 pt-32 pb-8">
            <h1 className="text-6xl md:text-7xl font-black text-white from-white via-purple-200 to-blue-200 bg-clip-text text-transparent animate-pulse">
              Recruiter Radar
            </h1>
            <p className="text-lg md:text-xl text-gray-300 max-w-2xl mx-auto">
              {showSavedCandidates
                ? `⭐ Viewing ${savedCandidates.length} saved candidates`
                : "AI-powered talent discovery. Find the perfect candidates with semantic search."}
            </p>
          </div>

          {/* Search Interface - Always Visible */}
          <div className="max-w-6xl mx-auto mb-8 px-4">
            <Tabs defaultValue="search" className="w-full">
              <TabsList className="grid w-full grid-cols-2 mb-8 bg-gray-800/50 border border-gray-700">
                <TabsTrigger
                  value="search"
                  className="flex items-center gap-2 data-[state=active]:bg-purple-600 data-[state=active]:text-white"
                >
                  <Search className="w-4 h-4" />
                  Search Candidates
                </TabsTrigger>
                <TabsTrigger
                  value="upload"
                  className="flex items-center gap-2 data-[state=active]:bg-purple-600 data-[state=active]:text-white"
                >
                  <Upload className="w-4 h-4" />
                  Upload Resume
                </TabsTrigger>
              </TabsList>

              <TabsContent value="search" className="space-y-8">
                {!showSavedCandidates && (
                  <SearchInterface
                    onSearch={handleSearch}
                    initialQuery={searchQuery}
                    onFilterChange={handleFilterChange}
                  />
                )}

                {/* Results or Welcome State */}
                {hasSearched ? (
                  <div className="space-y-8">
                    {showSavedCandidates && (
                      <div className="text-center mb-6">
                        <div className="inline-flex items-center gap-2 px-4 py-2 bg-yellow-500/20 border border-yellow-500/30 rounded-lg">
                          <Star className="w-4 h-4 text-yellow-500" />
                          <span className="text-yellow-500 font-medium">
                            Saved Candidates
                          </span>
                        </div>
                      </div>
                    )}

                    <div className="grid lg:grid-cols-4 gap-8">
                      <div className="lg:col-span-1">
                        <TalentHeatMap />
                      </div>
                      <div className="lg:col-span-3 space-y-6">
                        <CandidateGrid
                          candidates={candidates.map((c) => ({
                            ...c,
                            distance: c.distance ?? "",
                            experience: c.experience ?? 0,
                          }))}
                          isLoading={isLoading}
                          searchQuery={
                            showSavedCandidates
                              ? "Saved Candidates"
                              : searchQuery
                          }
                          onGenerateOutreach={handleGenerateOutreach}
                          totalCandidates={
                            showSavedCandidates
                              ? savedCandidates.length
                              : searchMetrics.totalResults
                          }
                        />

                        {/* 📄 PAGINATION COMPONENT - Only show for search results, not saved */}
                        {paginationInfo &&
                          !isLoading &&
                          !showSavedCandidates && (
                            <CandidatePagination
                              pagination={paginationInfo}
                              onPageChange={handlePageChange}
                              onPageSizeChange={handlePageSizeChange}
                              onLoadMore={handleLoadMore}
                              onExportAll={handleExportAll}
                              loading={isLoading}
                              showLoadMore={true}
                              showExport={true}
                            />
                          )}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center space-y-8 max-w-3xl mx-auto py-12">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <button
                        onClick={() =>
                          handleSearch(
                            "Senior React Developer in San Francisco"
                          )
                        }
                        className="group relative p-4 rounded-xl backdrop-blur-md bg-white/5 border border-white/10 hover:border-purple-400/50 transition-all duration-300 hover:scale-105 hover:shadow-lg hover:shadow-purple-500/25"
                      >
                        <div className="flex items-center space-x-3">
                          <span className="text-white/90 group-hover:text-white transition-colors">
                            Senior React Developer in SF
                          </span>
                        </div>
                      </button>

                      <button
                        onClick={() =>
                          handleSearch("Product Manager with AI experience")
                        }
                        className="group relative p-4 rounded-xl backdrop-blur-md bg-white/5 border border-white/10 hover:border-purple-400/50 transition-all duration-300 hover:scale-105 hover:shadow-lg hover:shadow-purple-500/25"
                      >
                        <div className="flex items-center space-x-3">
                          <span className="text-white/90 group-hover:text-white transition-colors">
                            Product Manager with AI experience
                          </span>
                        </div>
                      </button>

                      <button
                        onClick={() => handleSearch("Remote DevOps Engineer")}
                        className="group relative p-4 rounded-xl backdrop-blur-md bg-white/5 border border-white/10 hover:border-purple-400/50 transition-all duration-300 hover:scale-105 hover:shadow-lg hover:shadow-purple-500/25"
                      >
                        <div className="flex items-center space-x-3">
                          <span className="text-white/90 group-hover:text-white transition-colors">
                            Remote DevOps Engineer
                          </span>
                        </div>
                      </button>

                      <button
                        onClick={() =>
                          handleSearch("UX Designer at Series B startups")
                        }
                        className="group relative p-4 rounded-xl backdrop-blur-md bg-white/5 border border-white/10 hover:border-purple-400/50 transition-all duration-300 hover:scale-105 hover:shadow-lg hover:shadow-purple-500/25"
                      >
                        <div className="flex items-center space-x-3">
                          <span className="text-white/90 group-hover:text-white transition-colors">
                            UX Designer at Series B startups
                          </span>
                        </div>
                      </button>
                    </div>

                    <p className="text-gray-400 text-sm">
                      Try searching above or click on one of these popular
                      examples
                    </p>
                  </div>
                )}
              </TabsContent>

              <TabsContent value="upload" className="space-y-8">
                <ResumeUpload />
              </TabsContent>
            </Tabs>
          </div>
        </main>
      </div>

      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onSearch={handleSearch}
      />

      {/* FE-6: Outreach Modal */}
      <OutreachModal
        isOpen={isOutreachModalOpen}
        onClose={() => {
          setIsOutreachModalOpen(false);
          setSelectedCandidateForOutreach(null);
        }}
        candidate={selectedCandidateForOutreach}
        onSuccess={handleOutreachSuccess}
      />
    </div>
  );
}
