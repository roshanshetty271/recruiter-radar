"use client";

import { useState, useEffect } from "react";
import { MetricsBar } from "../components/metrics-bar";
import { HeroSection } from "../components/hero-section";
import {
  SearchInterface,
  type SearchMode,
} from "../components/search-interface";
import { ChatSection } from "../components/chat/ChatSection";
import { TalentHeatMap } from "../components/talent-heat-map";
import { CandidateGrid } from "../components/candidate-grid";
import { CommandPalette } from "../components/command-palette";
import { AnimatedBackground } from "../components/animated-background";
import { OutreachModal } from "../components/custom/outreach-modal"; // FE-6 IMPORT
import UploadModal from "../components/upload/UploadModal";
// Import our services
import { api } from "../lib/api";
import {
  mapBackendCandidatesToFrontend,
  getSearchMetrics,
} from "../services/helpers";
import { apiService } from "../services/apiService";
import { useSession } from "../contexts/SessionContext";
import { toast } from "../hooks/use-toast";
import type { FrontendCandidate, ChatMessage } from "../lib/types";
import { saveChatMessages, loadChatMessages } from "../lib/chat-storage";

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
  const {
    session,
    refreshSession,
    getRemainingUploads,
    getRemainingMessages,
    canUpload,
    canSendMessage,
  } = useSession();
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

  // Chat integration state
  const [searchMode, setSearchMode] = useState<SearchMode>("search");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isChatTyping, setIsChatTyping] = useState<boolean>(false);
  const [remainingMessages, setRemainingMessages] = useState<number>(10);

  // FE-6: Outreach modal state
  const [isOutreachModalOpen, setIsOutreachModalOpen] = useState(false);
  const [selectedCandidateForOutreach, setSelectedCandidateForOutreach] =
    useState<FrontendCandidate | null>(null);

  // Step 3: Upload modal state
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

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

  // Load chat messages from localStorage on mount
  useEffect(() => {
    if (session?.session_id) {
      const storedMessages = loadChatMessages(session.session_id);
      if (storedMessages.length > 0) {
        setChatMessages(storedMessages);
      }
    }
  }, [session?.session_id]);

  // Save chat messages to localStorage when they change
  useEffect(() => {
    if (chatMessages.length > 0 && session?.session_id) {
      saveChatMessages(session.session_id, chatMessages);
    }
  }, [chatMessages, session?.session_id]);

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

    toast({
      title: "🎉 Outreach Generated!",
      description: "Your AI-powered message is ready to send",
    });
  };

  // Chat handler function - Updated for GPT-4o-mini conversational assistant
  const handleChat = async (message: string) => {
    if (!message.trim() || !canSendMessage()) return;

    // Create user message
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: message,
      timestamp: new Date(),
    };

    // Add user message to chat
    setChatMessages((prev) => [...prev, userMessage]);
    setIsChatTyping(true);

    try {
      // Call our new conversational chat API
      const response = await apiService.chat(
        message,
        session?.session_id || ""
      );

      // Transform backend candidates to frontend candidates
      const frontendCandidates = response.candidates?.length
        ? mapBackendCandidatesToFrontend({
            results: response.candidates,
            final_count_after_post_filter: response.candidates.length,
            retrieved_count_before_post_filter: response.candidates.length,
            processing_time_ms: response.processing_time_ms,
          })
        : undefined;

      // Create assistant message
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: response.ai_message,
        timestamp: new Date(),
        candidates: frontendCandidates,
      };

      // Update chat and remaining messages count
      setChatMessages((prev) => [...prev, assistantMessage]);
      setRemainingMessages(response.remaining_messages);

      // Refresh session to get updated counts
      await refreshSession();

      // Update candidate grid if candidates were returned
      if (frontendCandidates && frontendCandidates.length > 0) {
        setCandidates(frontendCandidates);
        setHasSearched(true);

        // Update search metrics
        setSearchMetrics({
          totalResults: frontendCandidates.length,
          searchTimeMs: response.processing_time_ms,
          queryInterpretation: response.ai_message,
        });
      }

      toast({
        title: "💬 AI Assistant",
        description: frontendCandidates
          ? `Found ${frontendCandidates.length} candidates`
          : "AI responded to your question",
      });
    } catch (error) {
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content:
          "Sorry, I encountered an error processing your request. Please try again.",
        timestamp: new Date(),
      };

      setChatMessages((prev) => [...prev, errorMessage]);

      toast({
        title: "Chat Error",
        description:
          error instanceof Error ? error.message : "Failed to send message",
        variant: "destructive",
      });
    } finally {
      setIsChatTyping(false);
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

    // Update session metrics
    setSessionMetrics((prev) => ({
      ...prev,
      totalSearches: prev.totalSearches + 1,
    }));

    try {
      // Call the API service with the query and filters
      const searchResults = await api.searchCandidates(query, {
        ...activeFilters,
        ...filters,
      });

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

      setIsLoading(false);

      // Show success toast if there are results
      if (mappedCandidates.length > 0) {
        const timeStr = metrics.searchTimeMs
          ? `${metrics.searchTimeMs.toFixed(2)}ms`
          : "lightning fast";

        toast({
          title: "🎯 AI Search Complete",
          description: `Found ${
            metrics.totalResults || mappedCandidates.length
          } candidates in ${timeStr} with intelligent matching`,
        });
      } else {
        toast({
          title: "No results found",
          description: "Try adjusting your search query or filters",
          variant: "destructive",
        });
      }
    } catch (error: unknown) {
      const message =
        error instanceof Error ? error.message : "Please try again";
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
          totalSearches={sessionMetrics.totalSearches}
          totalResults={searchMetrics.totalResults}
          searchTimeMs={searchMetrics.searchTimeMs}
          outreachGenerated={sessionMetrics.outreachGenerated}
          onUploadClick={() => setIsUploadModalOpen(true)}
          uploadCount={session?.upload_count || 0}
          maxUploads={10}
        />

        <main className="container mx-auto px-4 pt-20">
          {/* Always show compact hero section */}
          <HeroSection onSearch={handleSearch} />

          {/* Always show search interface prominently */}
          <div className="mt-8 mb-8">
            <SearchInterface
              onSearch={handleSearch}
              onChat={handleChat}
              initialQuery={searchQuery}
              onFilterChange={handleFilterChange}
              onUploadClick={() => setIsUploadModalOpen(true)}
              remainingUploads={getRemainingUploads()}
              mode={searchMode}
              onModeChange={setSearchMode}
              isTyping={isChatTyping}
              remainingMessages={remainingMessages}
            />
          </div>

          {/* Chat section appears when in chat mode and there are messages */}
          {searchMode === "chat" && (
            <div className="mt-4 mb-8">
              <ChatSection messages={chatMessages} isTyping={isChatTyping} />
            </div>
          )}

          {/* Show results only after search */}
          {hasSearched && (
            <div className="space-y-8">
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

      {/* Upload Modal */}
      <UploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadComplete={(results) => {
          // Handle upload completion
          console.log("Upload completed:", results);
          // Optionally refresh candidate list or show success message
        }}
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
