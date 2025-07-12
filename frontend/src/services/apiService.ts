/**
 * API Service for RecruiterRadar
 * Handles communication with the backend API
 */
import {
  BackendSearchResponse,
  OutreachRequestBody,
  OutreachResponse,
  CandidateProfile,
  CandidateInsightsResponse,
  ComparisonAnalysisResponse,
  ComparisonRequest,
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
   * Search for candidates matching the query and filters with pagination support
   */
  async searchCandidates(
    query: string,
    filters: {
      page?: number;
      page_size?: number;
      limit?: number; // Legacy support
      location?: string;
      visa_status?: string;
      min_experience?: number;
      skills?: string;
    } = {}
  ): Promise<BackendSearchResponse> {
    console.log("🔍 Starting intelligent search...");
    console.log("🔧 DEBUG - Search called with:", { query, filters });
    console.log("🔧 DEBUG - Base URL:", this.baseURL);

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

    // 📊 BUILD ENHANCED PARAMETERS with Pagination
    const params = new URLSearchParams({
      q: cleanQuery || query, // Use cleaned query for better semantic matching
    });

    // 📄 PAGINATION PARAMETERS
    if (filters.page !== undefined && filters.page > 0) {
      params.append("page", String(filters.page));
    }
    if (filters.page_size !== undefined && filters.page_size > 0) {
      params.append("page_size", String(filters.page_size));
    }

    // Legacy support for limit parameter
    if (
      filters.limit !== undefined &&
      filters.limit > 0 &&
      !filters.page_size
    ) {
      params.append("limit", String(filters.limit));
      console.log("🔄 Using legacy limit parameter for backward compatibility");
    }

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

    const finalUrl = `${
      this.baseURL
    }/api/v1/candidates/query?${params.toString()}`;
    console.log("🔧 DEBUG - Final request URL:", finalUrl);

    try {
      console.log("🚀 Making request to backend...");

      const response = await this.fetchWithTimeout(finalUrl);

      console.log(
        "✅ Response received:",
        response.status,
        response.statusText
      );

      if (!response.ok) {
        console.error(
          "❌ Response not OK:",
          response.status,
          response.statusText
        );
        const errorData = await response
          .json()
          .catch(() => ({ message: response.statusText }));

        // Handle backend error format (FastAPI ErrorResponse)
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;

        if (errorData) {
          if (typeof errorData === "string") {
            errorMessage = errorData;
          } else if (errorData.detail) {
            // FastAPI validation error format
            if (typeof errorData.detail === "string") {
              errorMessage = errorData.detail;
            } else if (Array.isArray(errorData.detail)) {
              // FastAPI validation error array
              errorMessage = errorData.detail
                .map((err: any) => err.msg || String(err))
                .join(", ");
            } else if (typeof errorData.detail === "object") {
              // FastAPI ErrorResponse format
              errorMessage =
                errorData.detail.message ||
                errorData.detail.error ||
                String(errorData.detail);
            }
          } else if (errorData.message) {
            errorMessage = errorData.message;
          } else if (errorData.error) {
            errorMessage = errorData.error;
          }
        }

        throw new Error(errorMessage);
      }

      const data: BackendSearchResponse = await response.json();
      console.log("✅ Data parsed:", data);

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
      console.error("💥 Request failed with error:", error);
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

        // Handle backend error format (FastAPI ErrorResponse)
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;

        if (errorData) {
          if (typeof errorData === "string") {
            errorMessage = errorData;
          } else if (errorData.detail) {
            // FastAPI validation error format
            if (typeof errorData.detail === "string") {
              errorMessage = errorData.detail;
            } else if (Array.isArray(errorData.detail)) {
              // FastAPI validation error array
              errorMessage = errorData.detail
                .map((err: any) => err.msg || String(err))
                .join(", ");
            } else if (typeof errorData.detail === "object") {
              // FastAPI ErrorResponse format
              errorMessage =
                errorData.detail.message ||
                errorData.detail.error ||
                String(errorData.detail);
            }
          } else if (errorData.message) {
            errorMessage = errorData.message;
          } else if (errorData.error) {
            errorMessage = errorData.error;
          }
        }

        throw new Error(errorMessage);
      }

      const result = await response.json();
      console.log("API Response Structure:", result); // DEBUG
      console.log("Keys in response:", Object.keys(result)); // DEBUG
      return result;
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
   * Batch upload up to 10 resume files
   */
  async uploadBatch(files: File[]): Promise<{ task_id: string }> {
    if (!files.length) throw new Error("No files provided");

    const form = new FormData();
    files.forEach((file) => form.append("files", file));

    const response = await this.fetchWithTimeout(
      `${this.baseURL}/api/v1/candidates/upload-batch`,
      {
        method: "POST",
        body: form,
      },
      config.api.longTimeout
    );

    if (!response.ok) {
      const errorData = await response
        .json()
        .catch(() => ({ message: response.statusText }));

      // Handle backend error format (FastAPI ErrorResponse)
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;

      if (errorData) {
        if (typeof errorData === "string") {
          errorMessage = errorData;
        } else if (errorData.detail) {
          // FastAPI validation error format
          if (typeof errorData.detail === "string") {
            errorMessage = errorData.detail;
          } else if (Array.isArray(errorData.detail)) {
            // FastAPI validation error array
            errorMessage = errorData.detail
              .map((err: any) => err.msg || String(err))
              .join(", ");
          } else if (typeof errorData.detail === "object") {
            // FastAPI ErrorResponse format
            errorMessage =
              errorData.detail.message ||
              errorData.detail.error ||
              String(errorData.detail);
          }
        } else if (errorData.message) {
          errorMessage = errorData.message;
        } else if (errorData.error) {
          errorMessage = errorData.error;
        }
      }

      throw new Error(errorMessage);
    }

    return await response.json();
  }

  async getBatchStatus(task_id: string): Promise<any> {
    const response = await this.fetchWithTimeout(
      `${this.baseURL}/api/v1/candidates/batch-status/${task_id}`,
      { method: "GET" }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || "Failed to fetch batch status");
    }
    return await response.json();
  }

  async getCandidateInsights(candidateId: string): Promise<any> {
    const response = await this.fetchWithTimeout(
      `${this.baseURL}/api/v1/candidates/${candidateId}/insights`
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || "Failed to fetch insights");
    }
    return await response.json();
  }

  /**
   * Get complete candidate details by ID
   */
  async getCandidateDetails(candidateId: string): Promise<CandidateProfile> {
    console.log(`[API] Starting fetch for candidate details: ${candidateId}`);
    try {
      const response = await this.fetchWithTimeout(
        `${this.baseURL}/api/v1/candidates/${candidateId}`
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error(
          `[API] Error fetching candidate ${candidateId}:`,
          errorData
        );
        throw new Error(
          errorData.detail || "Failed to fetch candidate details"
        );
      }
      const data = await response.json();
      console.log(`[API] Successfully fetched candidate ${candidateId}:`, data);
      return data;
    } catch (error) {
      console.error(
        `[API] Network error fetching candidate ${candidateId}:`,
        error
      );
      throw error;
    }
  }

  /**
   * 🤖 AI Hiring Advisor: Analyze multiple candidates for comparison
   *
   * This is the game-changing feature that saves recruiters 2-3 hours per comparison!
   */
  async analyzeComparison(
    request: ComparisonRequest
  ): Promise<ComparisonAnalysisResponse> {
    console.log("🤖 Starting AI Hiring Advisor analysis...", request);

    try {
      const response = await this.fetchWithTimeout(
        `${this.baseURL}/api/v1/candidates/analyze-comparison`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(request),
        },
        config.api.longTimeout // Allow extra time for AI analysis
      );

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ message: response.statusText }));

        // Handle backend error format
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;

        if (errorData) {
          if (typeof errorData === "string") {
            errorMessage = errorData;
          } else if (errorData.detail) {
            if (typeof errorData.detail === "string") {
              errorMessage = errorData.detail;
            } else if (Array.isArray(errorData.detail)) {
              errorMessage = errorData.detail
                .map((err: any) => err.msg || String(err))
                .join(", ");
            } else if (typeof errorData.detail === "object") {
              errorMessage =
                errorData.detail.message ||
                errorData.detail.error ||
                String(errorData.detail);
            }
          } else if (errorData.message) {
            errorMessage = errorData.message;
          } else if (errorData.error) {
            errorMessage = errorData.error;
          }
        }

        throw new Error(errorMessage);
      }

      const result: ComparisonAnalysisResponse = await response.json();

      console.log(
        `✅ AI Hiring Advisor completed in ${result.processing_time_ms}ms. ` +
          `Winner: ${result.winner.candidate_name} (${result.winner.confidence}% confidence)`
      );

      return result;
    } catch (error) {
      let errorMessage = "AI comparison analysis failed";
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      console.error("❌ AI Hiring Advisor failed:", errorMessage);
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

export async function getCandidateInsights(
  candidateId: string
): Promise<CandidateInsightsResponse> {
  const response = await fetch(
    `${config.api.baseUrl}/api/v1/candidates/${candidateId}/insights`,
    {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to fetch candidate insights");
  }

  return response.json();
}

// 🆕 NEW: Complete candidate details endpoint
export async function getCandidateDetails(
  candidateId: string
): Promise<CandidateProfile> {
  console.log(`[API] Starting fetch for candidate details: ${candidateId}`);
  try {
    const response = await fetch(
      `${config.api.baseUrl}/api/v1/candidates/${candidateId}`,
      {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      }
    );

    if (!response.ok) {
      const errorData = await response.json();
      console.error(
        `[API] Error fetching candidate ${candidateId}:`,
        errorData
      );
      throw new Error(errorData.detail || "Failed to fetch candidate details");
    }

    const data = await response.json();
    console.log(`[API] Successfully fetched candidate ${candidateId}:`, data);
    return data;
  } catch (error) {
    console.error(
      `[API] Network error fetching candidate ${candidateId}:`,
      error
    );
    throw error;
  }
}

// 🤖 AI Hiring Advisor: Analyze multiple candidates for comparison
export async function analyzeComparison(
  request: ComparisonRequest
): Promise<ComparisonAnalysisResponse> {
  return apiService.analyzeComparison(request);
}
