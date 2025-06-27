"use client";

import { useState, useEffect } from "react";
import { MetricsBar } from "../components/metrics-bar";
import { HeroSection } from "../components/hero-section";
import { SearchInterface } from "../components/search-interface";
import { ChatSection } from "../components/chat/ChatSection";
import { TalentHeatMap } from "../components/talent-heat-map";
import { CandidateGrid } from "../components/candidate-grid";
import { CommandPalette } from "../components/command-palette";
import { AnimatedBackground } from "../components/animated-background";
import { OutreachModal } from "../components/custom/outreach-modal";
import UploadModal from "../components/upload/UploadModal";
// Import our services
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

  const [hasSearched, setHasSearched] = useState<boolean>(false);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] =
    useState<boolean>(false);
  const [candidates, setCandidates] = useState<FrontendCandidate[]>([]);
  const [searchMetrics, setSearchMetrics] = useState<SearchMetrics>({
    totalResults: 0,
    searchTimeMs: 0,
    queryInterpretation: null,
  });

  // 🚀 Chat-First State - No more search/chat mode toggle!
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isChatTyping, setIsChatTyping] = useState<boolean>(false);
  const [remainingMessages, setRemainingMessages] = useState<number>(10);
  const [lastQueryInterpretation, setLastQueryInterpretation] =
    useState<string>("");

  // Outreach modal state
  const [isOutreachModalOpen, setIsOutreachModalOpen] = useState(false);
  const [selectedCandidateForOutreach, setSelectedCandidateForOutreach] =
    useState<FrontendCandidate | null>(null);

  // Upload modal state
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  // Session metrics state
  const [sessionMetrics, setSessionMetrics] = useState<SessionMetrics>({
    totalSearches: 0,
    candidatesViewed: 0,
    outreachGenerated: 0,
    timeSpent: 0,
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

  // Generate outreach messages
  const handleGenerateOutreach = async (candidateId: string) => {
    try {
      const candidate = candidates.find((c) => c.id === candidateId);

      if (!candidate) {
        throw new Error("Candidate not found");
      }

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

  // Handle outreach success
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

  // 🚀 Enhanced Chat Handler - Now the primary interaction method!
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

    // Update session metrics
    setSessionMetrics((prev) => ({
      ...prev,
      totalSearches: prev.totalSearches + 1,
    }));

    try {
      // Call our bulletproof conversational chat API
      const response = await apiService.bulletproofChat(
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
        source: response.source as
          | "assistant"
          | "fallback"
          | "cache"
          | "emergency_fallback"
          | undefined,
        responseTime: response.response_time,
        isFromBulletproof: true,
      };

      // Update chat and remaining messages count
      setChatMessages((prev) => [...prev, assistantMessage]);
      setRemainingMessages(response.remaining_messages);

      // Store query interpretation for refinements
      setLastQueryInterpretation(response.ai_message);

      // Refresh session to get updated counts
      await refreshSession();

      // ALWAYS update candidate grid - even if empty to clear previous results
      if (frontendCandidates !== undefined) {
        setCandidates(frontendCandidates);
        setHasSearched(true);

        // Update search metrics
        setSearchMetrics({
          totalResults: frontendCandidates.length,
          searchTimeMs: response.processing_time_ms,
          queryInterpretation: response.ai_message,
        });
      }

      // Enhanced toast with better feedback
      if (frontendCandidates !== undefined) {
        if (frontendCandidates.length === 0) {
          toast({
            title: "🔍 No Results Found",
            description: `No candidates match your search. Try adjusting your criteria.`,
            variant: "destructive",
          });
        } else {
          toast({
            title: "🤖 AI Found Results",
            description: `Found ${frontendCandidates.length} candidates via ${
              response.source || "system"
            } in ${response.response_time?.toFixed(2) || "instant"}s`,
          });
        }
      } else {
        toast({
          title: "💬 AI Assistant",
          description: `AI responded via ${response.source || "system"} in ${
            response.response_time?.toFixed(2) || "instant"
          }s`,
        });
      }
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

  // 🚀 Simplified Command Palette Search (uses chat behind the scenes)
  const handleCommandPaletteSearch = async (query: string) => {
    setIsCommandPaletteOpen(false);
    await handleChat(query); // Everything goes through chat now!
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
        />

        <main className="container mx-auto px-4 pt-20">
          {/* 🚀 ENHANCED HERO SECTION - Chat-First Messaging */}
          <HeroSection onSearch={handleChat} />

          {/* 🚀 BEAUTIFUL CHAT-FIRST SEARCH INTERFACE */}
          <div className="mt-8 mb-8">
            <SearchInterface
              onChat={handleChat}
              onUploadClick={() => setIsUploadModalOpen(true)}
              remainingUploads={getRemainingUploads()}
              isTyping={isChatTyping}
              remainingMessages={remainingMessages}
              lastQueryInterpretation={lastQueryInterpretation}
              showRefinements={hasSearched && candidates.length > 0}
            />
          </div>

          {/* 🚀 CHAT SECTION - Always visible when there are messages */}
          {chatMessages.length > 0 && (
            <div className="mt-4 mb-8">
              <ChatSection messages={chatMessages} isTyping={isChatTyping} />
            </div>
          )}

          {/* 🚀 RESULTS SECTION - Show after any search */}
          {hasSearched && (
            <div className="space-y-8">
              <div className="grid lg:grid-cols-4 gap-8">
                <div className="lg:col-span-1">
                  <TalentHeatMap />
                </div>
                <div className="lg:col-span-3">
                  {candidates.length > 0 ? (
                    <CandidateGrid
                      candidates={candidates}
                      isLoading={isChatTyping}
                      searchQuery={lastQueryInterpretation}
                      onGenerateOutreach={handleGenerateOutreach}
                    />
                  ) : (
                    <div className="text-center py-12">
                      <div className="text-gray-400 text-lg mb-4">
                        No candidates found for your search
                      </div>
                      <div className="text-gray-500 text-sm">
                        Try adjusting your criteria or asking differently
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onSearch={handleCommandPaletteSearch}
      />

      {/* Upload Modal */}
      <UploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadComplete={(results) => {
          console.log("Upload completed:", results);
        }}
      />

      {/* Outreach Modal */}
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
