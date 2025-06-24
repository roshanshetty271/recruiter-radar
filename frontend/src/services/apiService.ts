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

class RecruiterRadarAPI {
  private baseURL: string;
  private timeout: number;

  constructor() {
    this.baseURL = config.api.baseUrl;
    this.timeout = config.api.timeout;
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
      console.log(`🔧 Using normalized skills: ${cleanedSkills}`);
    }

    try {
      console.log(
        `🚀 Searching: "${cleanQuery}" with enhanced params:`,
        params.toString()
      );

      const response = await this.fetchWithTimeout(
        `${this.baseURL}/api/v1/candidates/query?${params.toString()}`
      );

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ message: response.statusText }));
        throw new Error(
          errorData.detail || errorData.message || `Error: ${response.status}`
        );
      }

      const data: BackendSearchResponse = await response.json();

      console.log(
        `✅ Search completed: ${data.results.length} results in ${data.search_time_ms}ms`
      );

      // 📈 LOG INTELLIGENCE METRICS
      if (extractedLocation) {
        console.log(
          `🎯 Smart location extraction: "${extractedLocation}" from "${query}"`
        );
      }
      if (cleanedSkills !== filters.skills) {
        console.log(
          `🔧 Smart skill normalization: "${filters.skills}" → "${cleanedSkills}"`
        );
      }

      return data;
    } catch (error) {
      let errorMessage = "Unknown error";
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      console.error("❌ Intelligent search failed:", errorMessage);
      throw new Error(errorMessage);
    }
  }

  /**
   * Generate an outreach message for a candidate
   */
  async generateOutreach(
    candidateId: string,
    jobRoleData: OutreachRequestBody
  ): Promise<OutreachResponse> {
    try {
      const response = await this.fetchWithTimeout(
        `${this.baseURL}/api/v1/candidates/${candidateId}/generate-outreach`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(jobRoleData),
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
      let errorMessage = "Unknown error";
      if (error instanceof Error) {
        errorMessage = error.message;
      } else if (
        typeof error === "object" &&
        error !== null &&
        "message" in error
      ) {
        errorMessage = String((error as any).message);
      } else {
        errorMessage = String(error);
      }
      console.error("Outreach generation error:", errorMessage);
      throw new Error(errorMessage);
    }
  }

  /**
   * Upload a resume PDF for processing
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
          body: formData,
          headers: {
            "X-Session-ID": sessionId,
          },
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

      return (await response.json()) as UploadStatusResponse;
    } catch (error) {
      let errorMessage = "Unknown error";
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      console.error("Resume upload error:", errorMessage);
      throw new Error(errorMessage);
    }
  }

  /**
   * Send a chat query to backend and receive candidates & AI response
   */
  async chat(message: string, sessionId: string): Promise<ChatResponse> {
    const body = {
      message,
    };

    try {
      const response = await this.fetchWithTimeout(
        `${this.baseURL}/api/v1/chat`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Session-ID": sessionId,
          },
          body: JSON.stringify(body),
        },
        30000 // 30 second timeout for chat (GPT calls can be slow)
      );

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ message: response.statusText }));
        throw new Error(
          errorData.detail || errorData.message || `Error: ${response.status}`
        );
      }

      return (await response.json()) as ChatResponse;
    } catch (error) {
      let errorMessage = "Unknown error";
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      console.error("Chat API error:", errorMessage);
      throw new Error(errorMessage);
    }
  }

  /**
   * Get session status from backend
   */
  async getSessionStatus(sessionId: string): Promise<any> {
    try {
      const response = await this.fetchWithTimeout(
        `${this.baseURL}/api/v1/session/status?session_id=${encodeURIComponent(
          sessionId
        )}`
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
