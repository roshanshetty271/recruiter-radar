"use client";

import { useState, useCallback, useRef } from "react";
import { apiService } from "../services/apiService";
import type { ChatMessage, FrontendCandidate } from "../lib/types";

interface UseBulletproofChatReturn {
  messages: ChatMessage[];
  isTyping: boolean;
  remainingMessages: number;
  error: string | null;
  isLoading: boolean;
  performanceMetrics: ChatPerformanceMetrics | null;
  sendMessage: (
    message: string,
    sessionId: string,
    useBulletproof?: boolean
  ) => Promise<void>;
  clearChat: () => void;
  retryLastMessage: () => Promise<void>;
  getChatMetrics: () => Promise<void>;
}

interface ChatPerformanceMetrics {
  totalRequests: number;
  assistantSuccessRate: number;
  fallbackRate: number;
  cacheHitRate: number;
  avgResponseTime: number;
  systemHealth: "healthy" | "degraded";
}

export function useBulletproofChat(): UseBulletproofChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [remainingMessages, setRemainingMessages] = useState(10);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [performanceMetrics, setPerformanceMetrics] =
    useState<ChatPerformanceMetrics | null>(null);

  // Store last message for retry functionality
  const lastMessageRef = useRef<{
    message: string;
    sessionId: string;
    useBulletproof: boolean;
  } | null>(null);

  const generateMessageId = () =>
    `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

  const mapBackendCandidateToFrontend = useCallback(
    (backendCandidate: any): FrontendCandidate => {
      // Handle skills conversion - ensure it's always an array
      let skillsArray: string[] = [];
      if (Array.isArray(backendCandidate.skills)) {
        skillsArray = backendCandidate.skills;
      } else if (typeof backendCandidate.skills === "string") {
        skillsArray = backendCandidate.skills
          .split(",")
          .map((s: string) => s.trim())
          .filter((s: string) => s.length > 0);
      }

      return {
        id: backendCandidate.id || `candidate_${Math.random()}`,
        name: backendCandidate.name || "Unknown Candidate",
        title:
          backendCandidate.title ||
          backendCandidate.current_title ||
          "Unknown Role",
        location: backendCandidate.location || "Location not specified",
        matchScore:
          backendCandidate.relevance_score || backendCandidate.match_score || 0,
        experience: backendCandidate.experience_years || 0,
        skills: skillsArray,
        isOnline: Math.random() > 0.5, // Random for demo
        isVerified: Math.random() > 0.3, // Random for demo
        avatar: `https://api.dicebear.com/7.x/avataaars/svg?seed=${
          backendCandidate.name || "unknown"
        }`,
        distance: "", // Empty until we implement distance calculation
        visaStatus: backendCandidate.visa_status || "Not specified",
        githubUrl: backendCandidate.github_url,
        linkedinUrl: backendCandidate.linkedin_url,
        isDemo:
          backendCandidate.session_id === "demo" ||
          backendCandidate.source === "demo",
      };
    },
    []
  );

  const sendMessage = useCallback(
    async (
      message: string,
      sessionId: string,
      useBulletproof: boolean = true
    ): Promise<void> => {
      if (!message.trim()) return;

      setError(null);
      setIsLoading(true);
      setIsTyping(true);

      // Store for retry functionality
      lastMessageRef.current = { message, sessionId, useBulletproof };

      // Add user message immediately
      const userMessage: ChatMessage = {
        id: generateMessageId(),
        role: "user",
        content: message.trim(),
        timestamp: new Date(),
        isFromBulletproof: useBulletproof,
      };

      setMessages((prev) => [...prev, userMessage]);

      try {
        console.log(
          `🚀 Sending ${
            useBulletproof ? "bulletproof" : "standard"
          } chat message...`
        );

        // Choose chat method based on useBulletproof flag
        const response = useBulletproof
          ? await apiService.bulletproofChat(message, sessionId)
          : await apiService.chat(message, sessionId);

        console.log(`✅ Chat response received:`, {
          source: response.source,
          responseTime: response.response_time,
          candidateCount: response.candidates.length,
        });

        // Map backend candidates to frontend format
        const frontendCandidates = response.candidates.map(
          mapBackendCandidateToFrontend
        );

        // Create assistant message
        const assistantMessage: ChatMessage = {
          id: generateMessageId(),
          role: "assistant",
          content: response.ai_message,
          candidates: frontendCandidates,
          timestamp: new Date(),
          source: response.source as
            | "assistant"
            | "fallback"
            | "cache"
            | "emergency_fallback"
            | undefined,
          responseTime: response.response_time,
          isFromBulletproof: useBulletproof,
        };

        setMessages((prev) => [...prev, assistantMessage]);
        setRemainingMessages(response.remaining_messages);

        // Log performance insights
        if (response.source === "cache") {
          console.log(
            `⚡ Cache hit! Ultra-fast response in ${response.response_time?.toFixed(
              3
            )}s`
          );
        } else if (response.source === "assistant") {
          console.log(
            `🤖 OpenAI Assistant success - enhanced conversation features active`
          );
        } else if (response.source === "fallback") {
          console.log(
            `🛡️ Fallback protection activated - reliable search results delivered`
          );
        }
      } catch (err) {
        console.error("❌ Chat error:", err);

        const errorMessage =
          err instanceof Error ? err.message : "Unknown error occurred";
        setError(errorMessage);

        // Add error message to chat
        const errorChatMessage: ChatMessage = {
          id: generateMessageId(),
          role: "assistant",
          content: `Sorry, I encountered an error: ${errorMessage}. Please try again.`,
          timestamp: new Date(),
          source: "emergency_fallback",
          isFromBulletproof: useBulletproof,
        };

        setMessages((prev) => [...prev, errorChatMessage]);
      } finally {
        setIsTyping(false);
        setIsLoading(false);
      }
    },
    [mapBackendCandidateToFrontend]
  );

  const retryLastMessage = useCallback(async (): Promise<void> => {
    if (!lastMessageRef.current) {
      console.warn("No previous message to retry");
      return;
    }

    const { message, sessionId, useBulletproof } = lastMessageRef.current;
    console.log("🔄 Retrying last message...");

    // Remove the last assistant message if it was an error
    setMessages((prev) => {
      const lastMessage = prev[prev.length - 1];
      if (
        lastMessage?.role === "assistant" &&
        lastMessage.source === "emergency_fallback"
      ) {
        return prev.slice(0, -1);
      }
      return prev;
    });

    await sendMessage(message, sessionId, useBulletproof);
  }, [sendMessage]);

  const getChatMetrics = useCallback(async (): Promise<void> => {
    try {
      const metrics = await apiService.getChatMetrics();

      const processedMetrics: ChatPerformanceMetrics = {
        totalRequests: metrics.total_requests || 0,
        assistantSuccessRate:
          metrics.performance_rates?.assistant_success_rate || 0,
        fallbackRate: metrics.performance_rates?.fallback_rate || 0,
        cacheHitRate: metrics.cache_stats?.hit_rate_percentage || 0,
        avgResponseTime: metrics.avg_response_time || 0,
        systemHealth: metrics.system_health?.status || "healthy",
      };

      setPerformanceMetrics(processedMetrics);
      console.log("📊 Performance metrics updated:", processedMetrics);
    } catch (err) {
      console.error("❌ Failed to fetch chat metrics:", err);
    }
  }, []);

  const clearChat = useCallback(() => {
    setMessages([]);
    setError(null);
    setPerformanceMetrics(null);
    lastMessageRef.current = null;
    console.log("🧹 Chat cleared");
  }, []);

  return {
    messages,
    isTyping,
    remainingMessages,
    error,
    isLoading,
    performanceMetrics,
    sendMessage,
    clearChat,
    retryLastMessage,
    getChatMetrics,
  };
}
