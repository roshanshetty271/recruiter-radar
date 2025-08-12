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
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Search,
  Upload,
  Star,
  RefreshCw,
  Wifi,
  WifiOff,
  AlertTriangle,
  CheckCircle,
} from "lucide-react";
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

// 🔒 NEW: Enhanced error state management
interface ErrorState {
  hasError: boolean;
  message: string;
  type: "network" | "server" | "validation" | "timeout" | "unknown";
  isRetryable: boolean;
  retryCount: number;
  lastErrorTime: number;
  suggestions: string[];
}

// 🔒 NEW: Loading state with detailed status
interface LoadingState {
  isLoading: boolean;
  stage: "idle" | "searching" | "processing" | "formatting" | "retrying";
  progress: number; // 0-100
  message: string;
  startTime: number;
}

// 🔒 NEW: Network status monitoring
interface NetworkStatus {
  isOnline: boolean;
  isSlowConnection: boolean;
  lastChecked: number;
}

export default function Dashboard() {
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [hasSearched, setHasSearched] = useState<boolean>(false);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] =
    useState<boolean>(false);
  const [candidates, setCandidates] = useState<FrontendCandidate[]>([]);

  // 🔒 NEW: Enhanced loading and error states
  const [loadingState, setLoadingState] = useState<LoadingState>({
    isLoading: false,
    stage: "idle",
    progress: 0,
    message: "",
    startTime: 0,
  });

  const [errorState, setErrorState] = useState<ErrorState>({
    hasError: false,
    message: "",
    type: "unknown",
    isRetryable: false,
    retryCount: 0,
    lastErrorTime: 0,
    suggestions: [],
  });

  const [networkStatus, setNetworkStatus] = useState<NetworkStatus>({
    isOnline: navigator.onLine,
    isSlowConnection: false,
    lastChecked: Date.now(),
  });

  const [searchMetrics, setSearchMetrics] = useState<SearchMetrics>({
    totalResults: 0,
    searchTimeMs: 0,
    queryInterpretation: null,
  });

  // 🧠 NEW: Progressive search metadata state
  const [searchMetadata, setSearchMetadata] = useState<any>(null);

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

  // 🔒 NEW: Network status monitoring
  useEffect(() => {
    const updateNetworkStatus = () => {
      setNetworkStatus((prev) => ({
        ...prev,
        isOnline: navigator.onLine,
        lastChecked: Date.now(),
      }));
    };

    const handleNetworkChange = () => {
      updateNetworkStatus();

      if (navigator.onLine) {
        toast({
          title: "🌐 Connection Restored",
          description: "Your internet connection is back online",
        });

        // Clear network-related errors
        if (errorState.type === "network") {
          setErrorState((prev) => ({ ...prev, hasError: false, message: "" }));
        }
      } else {
        toast({
          title: "📡 Connection Lost",
          description: "You're currently offline. Some features may not work.",
          variant: "destructive",
        });
      }
    };

    // Add event listeners
    window.addEventListener("online", handleNetworkChange);
    window.addEventListener("offline", handleNetworkChange);

    // Check connection speed (simple test)
    const checkConnectionSpeed = async () => {
      if (!navigator.onLine) return;

      const startTime = Date.now();
      try {
        await fetch("/api/ping", { method: "HEAD", cache: "no-cache" });
        const duration = Date.now() - startTime;

        setNetworkStatus((prev) => ({
          ...prev,
          isSlowConnection: duration > 2000, // Consider slow if > 2 seconds
        }));
      } catch (error) {
        // Ignore ping errors
      }
    };

    // Check connection speed periodically
    const speedCheckInterval = setInterval(checkConnectionSpeed, 30000); // Every 30 seconds

    return () => {
      window.removeEventListener("online", handleNetworkChange);
      window.removeEventListener("offline", handleNetworkChange);
      clearInterval(speedCheckInterval);
    };
  }, [errorState.type]);

  // 🔒 NEW: Enhanced error classification
  const classifyError = (error: any): Partial<ErrorState> => {
    if (!networkStatus.isOnline) {
      return {
        type: "network",
        message:
          "No internet connection. Please check your network and try again.",
        isRetryable: true,
        suggestions: [
          "Check your internet connection",
          "Try refreshing the page",
          "Switch to a different network if available",
        ],
      };
    }

    if (error?.type) {
      switch (error.type) {
        case "network_error":
          return {
            type: "network",
            message:
              "Network connection failed. Please check your internet and try again.",
            isRetryable: true,
            suggestions: [
              "Check your internet connection",
              "Disable VPN if you're using one",
              "Try refreshing the page",
            ],
          };
        case "timeout_error":
          return {
            type: "timeout",
            message: "Request timed out. The server might be busy.",
            isRetryable: true,
            suggestions: [
              "The server is taking longer than usual",
              "Try again in a few seconds",
              "Consider simplifying your search",
            ],
          };
        case "server_error":
          return {
            type: "server",
            message: "Server error occurred. Our team has been notified.",
            isRetryable: true,
            suggestions: [
              "Try again in a moment",
              "The issue is usually temporary",
              "Contact support if the problem persists",
            ],
          };
        case "validation_error":
          return {
            type: "validation",
            message:
              error.message ||
              "Invalid search parameters. Please check your input.",
            isRetryable: false,
            suggestions: [
              "Check your search terms for special characters",
              "Try a shorter, simpler search",
              "Remove some filters and try again",
            ],
          };
        case "rate_limit_error":
          return {
            type: "server",
            message: "Too many requests. Please wait a moment and try again.",
            isRetryable: true,
            suggestions: [
              "Wait 30 seconds before searching again",
              "Try fewer searches in quick succession",
              "Consider upgrading for higher limits",
            ],
          };
        default:
          return {
            type: "unknown",
            message: error.message || "An unexpected error occurred.",
            isRetryable: true,
            suggestions: [
              "Try refreshing the page",
              "Clear your browser cache",
              "Contact support if the issue continues",
            ],
          };
      }
    }

    // Fallback for unknown errors
    return {
      type: "unknown",
      message: error.message || "Something went wrong. Please try again.",
      isRetryable: true,
      suggestions: [
        "Try refreshing the page",
        "Check your internet connection",
        "Contact support if the problem persists",
      ],
    };
  };

  // 🔒 NEW: Enhanced loading state management
  const setLoadingStage = (
    stage: LoadingState["stage"],
    message: string,
    progress: number = 0
  ) => {
    setLoadingState((prev) => ({
      ...prev,
      stage,
      message,
      progress: Math.min(100, Math.max(0, progress)),
      startTime: stage !== "idle" ? prev.startTime || Date.now() : 0,
    }));
  };

  // 🔒 NEW: Auto-retry mechanism
  const performSearchWithRetry = async (
    query: string,
    filters: any,
    page: number,
    retryCount: number = 0
  ): Promise<any> => {
    const maxRetries = 3;
    const baseDelay = 1000; // 1 second

    try {
      setLoadingStage(
        "searching",
        `Searching candidates${
          retryCount > 0 ? ` (attempt ${retryCount + 1})` : ""
        }...`,
        20
      );

      const searchResults = await apiService.searchCandidates(query, {
        ...activeFilters,
        ...filters,
        page: page,
        page_size: pageSize,
      } as any);

      setLoadingStage("processing", "Processing results...", 60);
      return searchResults;
    } catch (error) {
      console.error(`Search attempt ${retryCount + 1} failed:`, error);

      const errorClassification = classifyError(error);

      if (errorClassification.isRetryable && retryCount < maxRetries) {
        const delay = baseDelay * Math.pow(2, retryCount); // Exponential backoff

        setLoadingStage(
          "retrying",
          `Retrying in ${delay / 1000} seconds...`,
          10
        );

        toast({
          title: "🔄 Retrying Search",
          description: `Attempt ${retryCount + 1} failed. Trying again in ${
            delay / 1000
          } seconds...`,
        });

        await new Promise((resolve) => setTimeout(resolve, delay));
        return performSearchWithRetry(query, filters, page, retryCount + 1);
      }

      // Update error state with classification
      setErrorState((prev) => ({
        ...prev,
        hasError: true,
        ...errorClassification,
        retryCount: retryCount + 1,
        lastErrorTime: Date.now(),
      }));

      throw error;
    }
  };

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
          setLoadingStage("searching", "Loading candidate for outreach...", 50);

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
          const errorClassification = classifyError(error);
          setErrorState((prev) => ({
            ...prev,
            hasError: true,
            ...errorClassification,
          }));

          toast({
            title: "Candidate Not Found",
            description: "Could not find the candidate you were working with.",
            variant: "destructive",
          });
        } finally {
          setLoadingStage("idle", "", 0);
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
    setErrorState((prev) => ({ ...prev, hasError: false, message: "" })); // Clear error on new search
    setLoadingStage("searching", "Preparing search...", 10);

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
      // Use enhanced search with retry mechanism
      const searchResults = await performSearchWithRetry(
        query,
        filters,
        targetPage
      );

      setLoadingStage("formatting", "Formatting results...", 80);

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

      // 🧠 NEW: Capture progressive search metadata
      setSearchMetadata(searchResults);

      // 📄 SET PAGINATION INFO
      if (searchResults.pagination) {
        setPaginationInfo(searchResults.pagination);
        setCurrentPage(searchResults.pagination.current_page);
      }

      setLoadingStage("idle", "Search complete!", 100);

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
      setLoadingStage("idle", "", 0);

      const errorClassification = classifyError(error);
      setErrorState((prev) => ({
        ...prev,
        hasError: true,
        ...errorClassification,
      }));

      // Only show error toast for NEW searches
      if (resetPagination) {
        toast({
          title: "❌ Search Failed",
          description:
            errorClassification.message ||
            "Failed to search candidates. Please try again.",
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
                          isLoading={
                            loadingState.isLoading ||
                            loadingState.stage !== "idle"
                          }
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
                          searchMetadata={searchMetadata}
                        />

                        {/* 📄 PAGINATION COMPONENT - Only show for search results, not saved */}
                        {paginationInfo &&
                          !(
                            loadingState.isLoading ||
                            loadingState.stage !== "idle"
                          ) &&
                          !showSavedCandidates && (
                            <CandidatePagination
                              pagination={paginationInfo}
                              onPageChange={handlePageChange}
                              onPageSizeChange={handlePageSizeChange}
                              onLoadMore={handleLoadMore}
                              onExportAll={handleExportAll}
                              loading={
                                loadingState.isLoading ||
                                loadingState.stage !== "idle"
                              }
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
