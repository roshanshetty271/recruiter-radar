/**
 * API Service for RecruiterRadar
 * Handles communication with the backend API
 */
import {
  BackendSearchResponse,
  OutreachRequestBody,
  OutreachResponse,
  UploadStatusResponse,
  ChatRequestBody,
  ChatResponse,
} from "./types";
import { parseLocationFromQuery, normalizeSkills } from "./searchUtils";
import { config } from "./config";

// Client-side cache interface
interface CachedResponse {
  data: any;
  timestamp: number;
  ttl: number;
}

class ClientCache {
  private readonly CACHE_PREFIX = "rr_cache_";
  private readonly DEFAULT_TTL = 10 * 60 * 1000; // 10 minutes

  private getCacheKey(key: string): string {
    return `${this.CACHE_PREFIX}${key}`;
  }

  private isExpired(cached: CachedResponse): boolean {
    return Date.now() > cached.timestamp + cached.ttl;
  }

  get(key: string): any | null {
    try {
      const cacheKey = this.getCacheKey(key);
      const cached = localStorage.getItem(cacheKey);

      if (!cached) return null;

      const parsedCache: CachedResponse = JSON.parse(cached);

      if (this.isExpired(parsedCache)) {
        localStorage.removeItem(cacheKey);
        return null;
      }

      console.log(`🎯 Cache HIT for: ${key}`);
      return parsedCache.data;
    } catch (error) {
      console.warn(`Cache get error for ${key}:`, error);
      return null;
    }
  }

  set(key: string, data: any, ttl: number = this.DEFAULT_TTL): void {
    try {
      const cacheKey = this.getCacheKey(key);
      const cached: CachedResponse = {
        data,
        timestamp: Date.now(),
        ttl,
      };

      localStorage.setItem(cacheKey, JSON.stringify(cached));
      console.log(`💾 Cache SET for: ${key} (TTL: ${ttl / 1000}s)`);
    } catch (error) {
      console.warn(`Cache set error for ${key}:`, error);
      // If localStorage is full, try to clear old cache entries
      this.cleanup();
    }
  }

  private cleanup(): void {
    try {
      const keys = Object.keys(localStorage);
      const cacheKeys = keys.filter((key) => key.startsWith(this.CACHE_PREFIX));

      // Remove expired entries first
      let expiredCount = 0;
      cacheKeys.forEach((key) => {
        try {
          const cached = JSON.parse(localStorage.getItem(key) || "");
          if (this.isExpired(cached)) {
            localStorage.removeItem(key);
            expiredCount++;
          }
        } catch (e) {
          localStorage.removeItem(key); // Remove malformed entries
        }
      });

      console.log(`🧹 Cache cleanup: removed ${expiredCount} expired entries`);
    } catch (error) {
      console.warn("Cache cleanup error:", error);
    }
  }

  clear(): void {
    try {
      const keys = Object.keys(localStorage);
      const cacheKeys = keys.filter((key) => key.startsWith(this.CACHE_PREFIX));
      cacheKeys.forEach((key) => localStorage.removeItem(key));
      console.log(`🗑️ Cleared ${cacheKeys.length} cache entries`);
    } catch (error) {
      console.warn("Cache clear error:", error);
    }
  }
}

class RecruiterRadarAPI {
  private baseURL: string;
  private timeout: number;
  private cache: ClientCache;

  constructor() {
    this.baseURL = config.api.baseUrl;
    this.timeout = config.api.timeout;
    this.cache = new ClientCache();
  }

  private getSessionId(): string {
    return localStorage.getItem("rr_session_id") || "anonymous";
  }

  private async fetchWithTimeout(
    url: string,
    options: RequestInit = {},
    timeout = this.timeout
  ): Promise<Response> {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
      });
      clearTimeout(id);
      return response;
    } catch (error) {
      clearTimeout(id);
      if (error instanceof Error && error.name === "AbortError") {
        throw new Error("Request timeout - please try again");
      }
      throw error;
    }
  }

  /**
   * Search for candidates matching the query and filters
   */
  async searchCandidates(
    query: string,
    filters: {
      limit?: number;
      location?: string;
      visa_status?: string;
      min_experience?: number;
      skills?: string;
    } = {}
  ): Promise<BackendSearchResponse> {
    console.log("🔍 Starting intelligent search...");

    // Create cache key for this search
    const cacheKey = `search_${query}_${JSON.stringify(filters)}`;

    // Check cache first
    const cached = this.cache.get(cacheKey);
    if (cached) {
      console.log("💾 Cache HIT for search:", query);
      return cached;
    }

    // 🧠 SMART QUERY PROCESSING
    const { cleanQuery, location: extractedLocation } = config.features
      .enableLocationExtraction
      ? parseLocationFromQuery(query)
      : { cleanQuery: query, location: undefined };

    // 🔧 SMART SKILL NORMALIZATION
    const cleanedSkills =
      filters.skills && config.features.enableSkillNormalization
        ? normalizeSkills(filters.skills)
        : filters.skills;

    // 📊 BUILD ENHANCED PARAMETERS
    const params = new URLSearchParams({
      q: cleanQuery || query, // Use cleaned query for better semantic matching
    });

    // Use extracted location if no explicit location filter
    const finalLocation = filters.location || extractedLocation;
    if (finalLocation) {
      params.append("location", finalLocation);
      console.log(
        `🧠 Using location: ${finalLocation} ${
          extractedLocation ? "(auto-extracted)" : "(manual)"
        }`
      );
    }

    if (filters.limit && filters.limit > 0) {
      params.append("limit", String(filters.limit));
    }
    if (filters.visa_status) {
      params.append("visa_status", filters.visa_status);
    }
    if (filters.min_experience !== undefined && filters.min_experience >= 0) {
      params.append("min_experience", String(filters.min_experience));
    }
    if (cleanedSkills) {
      params.append("skills", cleanedSkills);
      console.log(
        `🧠 Skills: ${cleanedSkills} ${
          cleanedSkills !== filters.skills ? "(normalized)" : "(original)"
        }`
      );
    }

    const startTime = performance.now();

    try {
      const response = await this.fetchWithTimeout(
        `${this.baseURL}/api/v1/query?${params}`
      );

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ message: response.statusText }));
        throw new Error(
          errorData.detail || errorData.message || `Error: ${response.status}`
        );
      }

      const data = await response.json();
      const endTime = performance.now();

      // 🚀 ENHANCED RESPONSE with intelligent metrics
      const enhancedData = {
        ...data,
        processing_time_ms: Math.round(endTime - startTime),
        intelligence: getSearchIntelligence(query, filters),
      };

      console.log(
        `✅ Search completed in ${enhancedData.processing_time_ms}ms with ${data.final_count_after_post_filter} results`
      );

      // Cache successful results
      this.cache.set(cacheKey, enhancedData);

      return enhancedData;
    } catch (error) {
      console.error("Search error:", error);
      let errorMessage = "Unknown error";
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      throw new Error(errorMessage);
    }
  }

  /**
   * Generate outreach content for a specific candidate
   */
  async generateOutreach(
    candidateId: string,
    jobRoleData: OutreachRequestBody
  ): Promise<OutreachResponse> {
    try {
      const response = await this.fetchWithTimeout(
        `${this.baseURL}/api/v1/generate-outreach`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            candidate_id: candidateId,
            ...jobRoleData,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ message: response.statusText }));
        throw new Error(
          errorData.detail || errorData.message || `Error: ${response.status}`
        );
      }

      return await response.json();
    } catch (error) {
      console.error("Outreach generation error:", error);
      let errorMessage = "Unknown error";
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      throw new Error(errorMessage);
    }
  }

  /**
   * Upload resume file
   */
  async uploadResume(
    file: File,
    sessionId: string
  ): Promise<UploadStatusResponse> {
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await this.fetchWithTimeout(
        `${this.baseURL}/api/v1/upload/resume`,
        {
          method: "POST",
          headers: {
            "X-Session-ID": sessionId,
          },
          body: formData,
        }
      );

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ message: response.statusText }));
        throw new Error(
          errorData.detail || errorData.message || `Error: ${response.status}`
        );
      }

      return await response.json();
    } catch (error) {
      console.error("Upload error:", error);
      let errorMessage = "Unknown error";
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      throw new Error(errorMessage);
    }
  }

  /**
   * Send chat message
   */
  async chat(message: string, sessionId: string): Promise<ChatResponse> {
    try {
      const response = await this.fetchWithTimeout(
        `${this.baseURL}/api/v1/chat`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Session-ID": sessionId,
          },
          body: JSON.stringify({ message }),
        }
      );

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ message: response.statusText }));
        throw new Error(
          errorData.detail || errorData.message || `Error: ${response.status}`
        );
      }

      return await response.json();
    } catch (error) {
      console.error("Chat error:", error);
      let errorMessage = "Unknown error";
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      throw new Error(errorMessage);
    }
  }

  /**
   * 🚀 BULLETPROOF: Send bulletproof chat message with fallback handling
   */
  async bulletproofChat(
    message: string,
    sessionId: string
  ): Promise<ChatResponse> {
    try {
      // 🚨 LOG K: HTTP Request Details
      console.log(
        `🚨 LOG K [HTTP_REQUEST]: url=${
          this.baseURL
        }/api/v1/chat/bulletproof, sessionId=${sessionId}, payload=${JSON.stringify(
          { message }
        )}`
      );

      const response = await this.fetchWithTimeout(
        `${this.baseURL}/api/v1/chat/bulletproof`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Session-ID": sessionId,
          },
          body: JSON.stringify({ message }),
        }
      );

      if (!response.ok) {
        // If bulletproof fails, try regular chat as fallback
        console.warn("Bulletproof chat failed, falling back to regular chat");
        return await this.chat(message, sessionId);
      }

      return await response.json();
    } catch (error) {
      console.error("Bulletproof chat error, trying regular chat:", error);
      // Final fallback to regular chat
      try {
        return await this.chat(message, sessionId);
      } catch (fallbackError) {
        console.error("All chat methods failed:", fallbackError);
        let errorMessage = "Chat service unavailable";
        if (fallbackError instanceof Error) {
          errorMessage = fallbackError.message;
        }
        throw new Error(errorMessage);
      }
    }
  }

  /**
   * Get chat performance metrics
   */
  async getChatMetrics(): Promise<any> {
    try {
      const response = await this.fetchWithTimeout(
        `${this.baseURL}/api/v1/chat/metrics`
      );

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ message: response.statusText }));
        throw new Error(
          errorData.detail || errorData.message || `Error: ${response.status}`
        );
      }

      return await response.json();
    } catch (error) {
      let errorMessage = "Unknown error";
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      console.error("Chat metrics error:", errorMessage);
      throw new Error(errorMessage);
    }
  }

  /**
   * Get session status
   */
  async getSessionStatus(sessionId: string): Promise<any> {
    try {
      const response = await this.fetchWithTimeout(
        `${this.baseURL}/api/v1/session/status?session_id=${sessionId}`
      );

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ message: response.statusText }));
        throw new Error(
          errorData.detail || errorData.message || `Error: ${response.status}`
        );
      }

      return await response.json();
    } catch (error) {
      let errorMessage = "Unknown error";
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      console.error("Session status error:", errorMessage);
      throw new Error(errorMessage);
    }
  }

  /**
   * Get example chat queries to help users get started
   */
  async getChatExamples(): Promise<any> {
    try {
      const response = await this.fetchWithTimeout(
        `${this.baseURL}/api/v1/chat/examples`
      );

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ message: response.statusText }));
        throw new Error(
          errorData.detail || errorData.message || `Error: ${response.status}`
        );
      }

      return await response.json();
    } catch (error) {
      let errorMessage = "Unknown error";
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      console.error("Chat examples error:", errorMessage);
      throw new Error(errorMessage);
    }
  }

  /**
   * 💾 Manage saved candidates (persistent across sessions)
   */
  async manageSavedCandidates(
    candidateIds: string[],
    action: "add" | "remove" | "clear" = "add"
  ): Promise<{ saved_candidate_ids: string[]; total_saved: number }> {
    const cacheKey = `saved_candidates_${action}`;

    try {
      const response = await this.fetchWithTimeout(
        `${this.baseURL}/api/v1/session/saved-candidates`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Session-ID": this.getSessionId(),
          },
          body: JSON.stringify({
            candidate_ids: candidateIds,
            action: action,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ message: response.statusText }));
        throw new Error(
          errorData.detail || errorData.message || `Error: ${response.status}`
        );
      }

      const result = await response.json();

      // Cache the result for immediate feedback
      this.cache.set(cacheKey, result, 5 * 60 * 1000); // 5 min cache

      console.log(`💾 Saved candidates ${action}:`, result);
      return result;
    } catch (error) {
      console.error(`Failed to ${action} saved candidates:`, error);
      throw error;
    }
  }

  /**
   * 📋 Get current saved candidates
   */
  async getSavedCandidates(): Promise<{
    saved_candidate_ids: string[];
    total_saved: number;
  }> {
    const cacheKey = "saved_candidates_list";

    // Check cache first
    const cached = this.cache.get(cacheKey);
    if (cached) {
      console.log("💾 Cache HIT for saved candidates list");
      return cached;
    }

    try {
      const response = await this.fetchWithTimeout(
        `${this.baseURL}/api/v1/session/saved-candidates`,
        {
          method: "GET",
          headers: {
            "X-Session-ID": this.getSessionId(),
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to get saved candidates: ${response.status}`);
      }

      const result = await response.json();

      // Cache for quick access
      this.cache.set(cacheKey, result, 10 * 60 * 1000); // 10 min cache

      return result;
    } catch (error) {
      console.error("Failed to get saved candidates:", error);
      throw error;
    }
  }

  /**
   * ⚖️ Manage comparison list (max 3 candidates)
   */
  async manageComparisonList(
    candidateIds: string[],
    action: "set" | "add" | "remove" | "clear" = "set"
  ): Promise<{
    comparison_candidate_ids: string[];
    total_in_comparison: number;
  }> {
    const cacheKey = `comparison_list_${action}`;

    try {
      const response = await this.fetchWithTimeout(
        `${this.baseURL}/api/v1/session/comparison-list`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Session-ID": this.getSessionId(),
          },
          body: JSON.stringify({
            candidate_ids: candidateIds,
            action: action,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ message: response.statusText }));
        throw new Error(
          errorData.detail || errorData.message || `Error: ${response.status}`
        );
      }

      const result = await response.json();

      // Cache the result
      this.cache.set(cacheKey, result, 5 * 60 * 1000); // 5 min cache

      console.log(`⚖️ Comparison list ${action}:`, result);
      return result;
    } catch (error) {
      console.error(`Failed to ${action} comparison list:`, error);
      throw error;
    }
  }

  /**
   * 📊 Get current comparison list
   */
  async getComparisonList(): Promise<{
    comparison_candidate_ids: string[];
    total_in_comparison: number;
  }> {
    const cacheKey = "comparison_list";

    // Check cache first
    const cached = this.cache.get(cacheKey);
    if (cached) {
      console.log("⚖️ Cache HIT for comparison list");
      return cached;
    }

    try {
      const response = await this.fetchWithTimeout(
        `${this.baseURL}/api/v1/session/comparison-list`,
        {
          method: "GET",
          headers: {
            "X-Session-ID": this.getSessionId(),
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to get comparison list: ${response.status}`);
      }

      const result = await response.json();

      // Cache for quick access
      this.cache.set(cacheKey, result, 10 * 60 * 1000); // 10 min cache

      return result;
    } catch (error) {
      console.error("Failed to get comparison list:", error);
      throw error;
    }
  }

  /**
   * 📡 Connect to streaming chat with chunked candidate delivery
   */
  async *streamChat(message: string): AsyncGenerator<
    {
      status: string;
      data?: any;
      error?: string;
      candidates?: any[];
      chunk_info?: any;
    },
    void,
    unknown
  > {
    try {
      const response = await fetch(`${this.baseURL}/api/v1/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-ID": this.getSessionId(),
          Accept: "text/event-stream",
        },
        body: JSON.stringify({ message }),
      });

      if (!response.ok) {
        throw new Error(`Streaming failed: ${response.status}`);
      }

      if (!response.body) {
        throw new Error("No response body for streaming");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      try {
        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            console.log("📡 Streaming completed");
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || ""; // Keep incomplete line in buffer

          for (const line of lines) {
            if (line.trim() === "" || !line.startsWith("data: ")) {
              continue;
            }

            try {
              const jsonData = line.slice(6); // Remove 'data: ' prefix
              const eventData = JSON.parse(jsonData);

              console.log("📡 SSE Event:", eventData.status, eventData);

              yield {
                status: eventData.status,
                data: eventData,
                candidates: eventData.candidates,
                chunk_info: eventData.chunk_info,
                error: eventData.error,
              };

              // Break on completion or fatal error
              if (
                eventData.status === "complete" ||
                (eventData.status === "error" && !eventData.recoverable)
              ) {
                return;
              }
            } catch (parseError) {
              console.warn("Failed to parse SSE data:", line, parseError);
              yield {
                status: "parse_error",
                error: `Failed to parse: ${line}`,
              };
            }
          }
        }
      } finally {
        reader.releaseLock();
      }
    } catch (error) {
      console.error("Streaming chat failed:", error);
      yield {
        status: "connection_error",
        error:
          error instanceof Error ? error.message : "Unknown streaming error",
      };
    }
  }
}

export const apiService = new RecruiterRadarAPI();

// 🎯 INTELLIGENCE METRICS for UI feedback
export interface SearchIntelligence {
  locationExtracted: boolean;
  extractedLocation?: string;
  skillsNormalized: boolean;
  originalSkills?: string;
  normalizedSkills?: string;
  queryModified: boolean;
  originalQuery: string;
  cleanedQuery: string;
}

export function getSearchIntelligence(
  originalQuery: string,
  originalFilters: any
): SearchIntelligence {
  const { cleanQuery, location } = parseLocationFromQuery(originalQuery);
  const normalizedSkills = originalFilters.skills
    ? normalizeSkills(originalFilters.skills)
    : undefined;

  return {
    locationExtracted: !!location,
    extractedLocation: location,
    skillsNormalized: !!(
      originalFilters.skills && normalizedSkills !== originalFilters.skills
    ),
    originalSkills: originalFilters.skills,
    normalizedSkills,
    queryModified: cleanQuery !== originalQuery,
    originalQuery,
    cleanedQuery: cleanQuery,
  };
}
