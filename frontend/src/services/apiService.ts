/**
 * API Service for RecruiterRadar
 * Handles communication with the backend API with comprehensive error handling
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

// 🔒 NEW: Error handling constants
const ERROR_HANDLING_CONFIG = {
  MAX_RETRIES: 3,
  RETRY_DELAY_BASE: 1000, // 1 second base delay
  RETRY_DELAY_MAX: 10000, // 10 seconds max delay
  CIRCUIT_BREAKER_THRESHOLD: 5, // failures before opening circuit
  CIRCUIT_BREAKER_TIMEOUT: 30000, // 30 seconds before trying again
  NETWORK_TIMEOUT: 30000, // 30 seconds default timeout
};

// 🔒 NEW: Error types for better handling
enum ErrorType {
  NETWORK_ERROR = "network_error",
  TIMEOUT_ERROR = "timeout_error",
  VALIDATION_ERROR = "validation_error",
  SERVER_ERROR = "server_error",
  CLIENT_ERROR = "client_error",
  RATE_LIMIT_ERROR = "rate_limit_error",
  UNKNOWN_ERROR = "unknown_error",
}

interface ApiError {
  type: ErrorType;
  message: string;
  statusCode?: number;
  details?: any;
  isRetryable: boolean;
}

// 🔒 NEW: Circuit breaker state
class CircuitBreaker {
  private failures = 0;
  private isOpen = false;
  private lastFailureTime = 0;

  shouldAllowRequest(): boolean {
    if (!this.isOpen) return true;

    // Check if enough time has passed to try again
    if (
      Date.now() - this.lastFailureTime >
      ERROR_HANDLING_CONFIG.CIRCUIT_BREAKER_TIMEOUT
    ) {
      this.isOpen = false;
      this.failures = 0;
      return true;
    }

    return false;
  }

  recordSuccess(): void {
    this.failures = 0;
    this.isOpen = false;
  }

  recordFailure(): void {
    this.failures++;
    this.lastFailureTime = Date.now();

    if (this.failures >= ERROR_HANDLING_CONFIG.CIRCUIT_BREAKER_THRESHOLD) {
      this.isOpen = true;
      console.warn("🚫 Circuit breaker opened - too many failures");
    }
  }

  isCircuitOpen(): boolean {
    return this.isOpen;
  }
}

class RecruiterRadarAPI {
  private baseURL: string;
  private timeout: number;
  private circuitBreaker = new CircuitBreaker();

  constructor() {
    this.baseURL = config.api.baseUrl;
    this.timeout = config.api.timeout;

    // Add logging to debug configuration issues
    console.log("🔧 API Service initialized:");
    console.log("🔧 Base URL:", this.baseURL);
    console.log("🔧 Timeout:", this.timeout);
    console.log(
      "🔧 Environment NEXT_PUBLIC_API_URL:",
      process.env.NEXT_PUBLIC_API_URL
    );

    // Validate base URL
    if (!this.baseURL || this.baseURL === "undefined") {
      console.error("❌ Invalid base URL configuration:", this.baseURL);
      this.baseURL = "http://localhost:8000"; // Fallback
      console.log("🔧 Using fallback base URL:", this.baseURL);
    }
  }

  // 🔒 NEW: Enhanced fetch with comprehensive error handling
  private async fetchWithRetries(
    url: string,
    options: RequestInit = {},
    retryCount = 0
  ): Promise<Response> {
    // Check circuit breaker
    if (!this.circuitBreaker.shouldAllowRequest()) {
      throw this.createApiError(
        ErrorType.SERVER_ERROR,
        "Service temporarily unavailable due to repeated failures. Please try again later.",
        503
      );
    }

    try {
      const response = await this.fetchWithTimeout(url, options, this.timeout);

      // Record success for circuit breaker
      this.circuitBreaker.recordSuccess();

      return response;
    } catch (error) {
      const apiError = this.parseError(error);

      // Record failure for circuit breaker
      this.circuitBreaker.recordFailure();

      // Determine if we should retry
      const shouldRetry =
        apiError.isRetryable &&
        retryCount < ERROR_HANDLING_CONFIG.MAX_RETRIES &&
        !this.circuitBreaker.isCircuitOpen();

      if (shouldRetry) {
        const delay = this.calculateRetryDelay(retryCount);
        console.warn(
          `⏳ Retrying request in ${delay}ms (attempt ${retryCount + 1}/${
            ERROR_HANDLING_CONFIG.MAX_RETRIES
          })`
        );

        await this.sleep(delay);
        return this.fetchWithRetries(url, options, retryCount + 1);
      }

      throw apiError;
    }
  }

  // 🔒 NEW: Error parsing and classification
  private parseError(error: any): ApiError {
    if (error instanceof Error && error.name === "AbortError") {
      return this.createApiError(
        ErrorType.TIMEOUT_ERROR,
        "Request timed out. Please check your connection and try again.",
        408,
        null,
        true
      );
    }

    if (error instanceof TypeError && error.message.includes("fetch")) {
      return this.createApiError(
        ErrorType.NETWORK_ERROR,
        "Network connection failed. Please check your internet connection.",
        0,
        null,
        true
      );
    }

    if (error.statusCode) {
      if (error.statusCode >= 500) {
        return this.createApiError(
          ErrorType.SERVER_ERROR,
          error.message || "Server error occurred. Please try again.",
          error.statusCode,
          error.details,
          true
        );
      } else if (error.statusCode === 429) {
        return this.createApiError(
          ErrorType.RATE_LIMIT_ERROR,
          "Too many requests. Please wait a moment and try again.",
          429,
          error.details,
          true
        );
      } else if (error.statusCode >= 400) {
        return this.createApiError(
          ErrorType.CLIENT_ERROR,
          error.message || "Invalid request. Please check your input.",
          error.statusCode,
          error.details,
          false
        );
      }
    }

    return this.createApiError(
      ErrorType.UNKNOWN_ERROR,
      error.message || "An unexpected error occurred. Please try again.",
      0,
      error,
      false
    );
  }

  private createApiError(
    type: ErrorType,
    message: string,
    statusCode?: number,
    details?: any,
    isRetryable = false
  ): ApiError {
    // Enhance error messages with more context
    let enhancedMessage = message;

    if (statusCode === 500) {
      enhancedMessage = `Server error: ${message}. Our team has been notified.`;
    } else if (statusCode === 503) {
      enhancedMessage = `Service unavailable: ${message}. Please try again in a moment.`;
    } else if (statusCode === 429) {
      enhancedMessage = `Too many requests: Please wait a moment before trying again.`;
    } else if (statusCode === 404) {
      enhancedMessage = `Not found: ${message}. The requested resource may not exist.`;
    } else if (statusCode === 400) {
      enhancedMessage = `Invalid request: ${message}. Please check your input.`;
    } else if (type === ErrorType.NETWORK_ERROR) {
      enhancedMessage = `Network error: ${message}. Please check your internet connection.`;
    } else if (type === ErrorType.TIMEOUT_ERROR) {
      enhancedMessage = `Request timeout: ${message}. The operation took too long to complete.`;
    }

    return {
      type,
      message: enhancedMessage,
      statusCode,
      details,
      isRetryable,
    };
  }

  private calculateRetryDelay(retryCount: number): number {
    const exponentialDelay =
      ERROR_HANDLING_CONFIG.RETRY_DELAY_BASE * Math.pow(2, retryCount);
    const jitter = Math.random() * 1000; // Add randomness to prevent thundering herd
    return Math.min(
      exponentialDelay + jitter,
      ERROR_HANDLING_CONFIG.RETRY_DELAY_MAX
    );
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
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

  // 🔒 NEW: Graceful degradation for search
  private async searchWithFallback(
    query: string,
    filters: any
  ): Promise<BackendSearchResponse> {
    try {
      // Try normal search first
      return await this.performSearch(query, filters);
    } catch (error) {
      console.warn("🔄 Primary search failed, trying fallbacks...", error);

      // Fallback 1: Try with simplified query
      if (query.length > 50) {
        try {
          const simplifiedQuery = query.split(" ").slice(0, 5).join(" ");
          console.log("🔄 Trying simplified query:", simplifiedQuery);
          return await this.performSearch(simplifiedQuery, filters);
        } catch (fallbackError) {
          console.warn("🔄 Simplified query also failed");
        }
      }

      // Fallback 2: Try without filters
      if (Object.keys(filters).length > 0) {
        try {
          console.log("🔄 Trying without filters");
          return await this.performSearch(query, {});
        } catch (fallbackError) {
          console.warn("🔄 Search without filters also failed");
        }
      }

      // Fallback 3: Return empty results with helpful message
      console.log("🔄 All fallbacks failed, returning empty results");
      return this.createEmptySearchResponse(query, error);
    }
  }

  private async performSearch(
    query: string,
    filters: any
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

    const response = await this.fetchWithRetries(finalUrl);

    console.log("✅ Response received:", response.status, response.statusText);

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

      const apiError = this.createApiError(
        response.status >= 500
          ? ErrorType.SERVER_ERROR
          : ErrorType.CLIENT_ERROR,
        errorMessage,
        response.status,
        errorData
      );
      throw apiError;
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
  }

  // 🔒 NEW: Create empty search response for fallback
  private createEmptySearchResponse(
    originalQuery: string,
    error: unknown
  ): BackendSearchResponse {
    const errorMessage =
      error instanceof Error ? error.message : "Search temporarily unavailable";

    return {
      results: [],
      search_time_ms: 0,
      total_results: 0,
      pagination: {
        current_page: 1,
        page_size: 20,
        total_candidates: 0,
        total_pages: 0,
        has_next: false,
        has_previous: false,
        start_index: 0,
        end_index: 0,
      },
      search_metadata: {
        query: originalQuery,
        processing_time_ms: 0,
        filters_applied: {},
        ai_confidence: 0,
        semantic_themes: [],
        suggested_refinements: [
          "Check your internet connection",
          "Try a simpler search term",
          "Remove some filters and try again",
        ],
      },
    };
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
    try {
      return await this.searchWithFallback(query, filters);
    } catch (error: unknown) {
      console.error("💥 All search attempts failed:", error);

      // Return user-friendly error
      if (typeof error === "object" && error !== null && "type" in error) {
        throw error; // Already an ApiError
      } else {
        throw this.parseError(error);
      }
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
      const response = await this.fetchWithRetries(
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

        throw this.createApiError(
          response.status >= 500
            ? ErrorType.SERVER_ERROR
            : ErrorType.CLIENT_ERROR,
          errorMessage,
          response.status,
          errorData
        );
      }

      const result = await response.json();
      console.log("API Response Structure:", result); // DEBUG
      console.log("Keys in response:", Object.keys(result)); // DEBUG
      return result;
    } catch (error: unknown) {
      if (typeof error === "object" && error !== null && "type" in error) {
        throw error; // Already an ApiError
      }

      const apiError = this.parseError(error);
      console.error("Outreach generation error:", apiError.message);
      throw apiError;
    }
  }

  /**
   * Simple health check to test if backend is reachable
   */
  async healthCheck(): Promise<any> {
    console.log("🔍 Health check - Base URL:", this.baseURL);
    console.log(
      "🔍 Health check - Circuit breaker open:",
      this.circuitBreaker.isCircuitOpen()
    );

    try {
      // First try the docs endpoint (should be fastest)
      const docsUrl = `${this.baseURL}/docs`;
      console.log("🔍 Health check URL (docs):", docsUrl);

      const response = await fetch(docsUrl, {
        method: "GET",
        mode: "cors",
        cache: "no-cache",
      });

      console.log(
        "🔍 Health check response:",
        response.status,
        response.statusText
      );
      console.log("🔍 Health check response URL:", response.url);

      if (response.ok) {
        return { status: response.status, ok: response.ok, url: response.url };
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (error) {
      console.error("🔍 Health check failed - Full error:", error);
      console.error("🔍 Health check failed - Error type:", typeof error);
      console.error(
        "🔍 Health check failed - Error message:",
        error instanceof Error ? error.message : "Unknown"
      );

      // Try to provide more specific error information
      if (error instanceof TypeError && error.message.includes("fetch")) {
        throw new Error(
          `Network error: Cannot connect to backend at ${this.baseURL}. Is the backend server running?`
        );
      } else if (error instanceof Error) {
        throw new Error(`Backend health check failed: ${error.message}`);
      } else {
        throw new Error(`Backend health check failed with unknown error`);
      }
    }
  }

  /**
   * Batch upload up to 10 resume files with async processing
   */
  async uploadBatch(files: File[]): Promise<any> {
    console.log("🔍 uploadBatch called with files:", files.length);
    console.log("🔍 Base URL:", this.baseURL);
    console.log(
      "🔍 Circuit breaker open:",
      this.circuitBreaker.isCircuitOpen()
    );

    if (!files.length) throw new Error("No files provided");

    const form = new FormData();
    files.forEach((file) => {
      console.log(`🔍 Adding file to form: ${file.name} (${file.size} bytes)`);
      form.append("files", file);
    });

    const uploadUrl = `${this.baseURL}/api/v1/candidates/upload-batch`;
    console.log("🔍 Upload URL:", uploadUrl);

    try {
      console.log("🔍 Making fetch request to upload-batch endpoint...");
      const response = await this.fetchWithRetries(uploadUrl, {
        method: "POST",
        body: form,
      });

      console.log(
        "🔍 Response received:",
        response.status,
        response.statusText
      );

      if (!response.ok) {
        console.log("🔍 Response not ok, parsing error...");
        const errorData = await response.json().catch(() => ({}));
        console.log("🔍 Error data:", errorData);
        throw this.createApiError(
          response.status >= 500
            ? ErrorType.SERVER_ERROR
            : ErrorType.CLIENT_ERROR,
          errorData.detail || "Failed to upload files",
          response.status,
          errorData
        );
      }

      console.log("🔍 Upload successful, parsing response...");
      return await response.json();
    } catch (error) {
      console.error("🔍 uploadBatch error caught:", error);
      console.error("🔍 Error type:", typeof error);
      console.error(
        "🔍 Error constructor:",
        error instanceof Error ? error.constructor.name : "Unknown"
      );
      throw error;
    }
  }

  /**
   * Get batch upload status
   */
  async getBatchUploadStatus(taskId: string): Promise<any> {
    console.log(`🔍 Getting batch status for task: ${taskId}`);

    const statusUrl = `${this.baseURL}/api/v1/candidates/batch-status/${taskId}`;
    console.log(`🔍 Status URL: ${statusUrl}`);

    try {
      const response = await this.fetchWithRetries(statusUrl, {
        method: "GET",
      });

      console.log(
        `🔍 Status response: ${response.status} ${response.statusText}`
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.log(`🔍 Status error data:`, errorData);

        // Create a more specific error message for 404s
        if (response.status === 404) {
          throw this.createApiError(
            ErrorType.CLIENT_ERROR,
            `Task ${taskId} not found - it may have completed or expired`,
            404,
            errorData
          );
        }

        throw this.createApiError(
          response.status >= 500
            ? ErrorType.SERVER_ERROR
            : ErrorType.CLIENT_ERROR,
          errorData.detail || "Failed to get batch status",
          response.status,
          errorData
        );
      }

      const statusData = await response.json();
      console.log(`🔍 Status data:`, statusData);
      return statusData;
    } catch (error) {
      console.error(`🔍 getBatchUploadStatus error for task ${taskId}:`, error);
      throw error;
    }
  }

  /**
   * Cancel batch upload
   */
  async cancelBatchUpload(taskId: string): Promise<any> {
    const response = await this.fetchWithRetries(
      `${this.baseURL}/api/v1/candidates/batch-cancel/${taskId}`,
      {
        method: "POST",
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw this.createApiError(
        response.status >= 500
          ? ErrorType.SERVER_ERROR
          : ErrorType.CLIENT_ERROR,
        errorData.detail || "Failed to cancel batch upload",
        response.status,
        errorData
      );
    }

    return await response.json();
  }

  async getBatchStatus(task_id: string): Promise<any> {
    const response = await this.fetchWithRetries(
      `${this.baseURL}/api/v1/candidates/batch-status/${task_id}`,
      { method: "GET" }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw this.createApiError(
        response.status >= 500
          ? ErrorType.SERVER_ERROR
          : ErrorType.CLIENT_ERROR,
        errorData.detail || "Failed to fetch batch status",
        response.status,
        errorData
      );
    }
    return await response.json();
  }

  async getCandidateInsights(candidateId: string): Promise<any> {
    const response = await this.fetchWithRetries(
      `${this.baseURL}/api/v1/candidates/${candidateId}/insights`
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw this.createApiError(
        response.status >= 500
          ? ErrorType.SERVER_ERROR
          : ErrorType.CLIENT_ERROR,
        errorData.detail || "Failed to fetch insights",
        response.status,
        errorData
      );
    }
    return await response.json();
  }

  async analyzeComparison(
    request: ComparisonRequest
  ): Promise<ComparisonAnalysisResponse> {
    if (!request.candidate_ids || request.candidate_ids.length < 2) {
      throw new Error("Must provide at least 2 candidates for comparison");
    }

    if (request.candidate_ids.length > 5) {
      throw new Error("Cannot compare more than 5 candidates at once");
    }

    console.log(
      `[API] Starting AI comparison analysis for ${request.candidate_ids.length} candidates`,
      request
    );

    const response = await this.fetchWithRetries(
      `${this.baseURL}/api/v1/candidates/analyze-comparison`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(request),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      console.error("[API] AI comparison analysis failed:", {
        status: response.status,
        statusText: response.statusText,
        errorData,
      });

      throw this.createApiError(
        response.status >= 500
          ? ErrorType.SERVER_ERROR
          : ErrorType.CLIENT_ERROR,
        errorData.detail || "Failed to analyze candidate comparison",
        response.status,
        errorData
      );
    }

    const result = await response.json();

    // Validate the response structure
    if (!result) {
      console.error("[API] Empty response from comparison analysis");
      throw new Error("Empty response from server");
    }

    if (!result.winner) {
      console.error("[API] Missing winner in comparison response:", result);
      throw new Error("Invalid server response: missing winner analysis");
    }

    if (!result.candidates || !Array.isArray(result.candidates)) {
      console.error("[API] Missing candidates array in response:", result);
      throw new Error("Invalid server response: missing candidate data");
    }

    console.log(`[API] AI comparison analysis completed successfully.`, {
      winner: result.winner?.candidate_name,
      candidateCount: result.candidates.length,
      processingTime: result.processing_time_ms,
      confidence: result.ai_confidence,
    });

    return result;
  }

  async getCandidateDetails(candidateId: string): Promise<any> {
    console.log(`[API] Starting fetch for candidate details: ${candidateId}`);
    try {
      const response = await this.fetchWithRetries(
        `${this.baseURL}/api/v1/candidates/${candidateId}`
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error(
          `[API] Error fetching candidate ${candidateId}:`,
          errorData
        );

        // Provide better error messages for common scenarios
        let errorMessage = "Failed to fetch candidate details";
        if (errorData.detail) {
          errorMessage = errorData.detail;
        } else if (response.status === 404) {
          errorMessage = "Candidate not found";
        } else if (response.status === 503) {
          errorMessage = "Candidate data service temporarily unavailable";
        } else if (response.status >= 500) {
          errorMessage = "Server error occurred while fetching candidate";
        }

        throw this.createApiError(
          response.status >= 500
            ? ErrorType.SERVER_ERROR
            : ErrorType.CLIENT_ERROR,
          errorMessage,
          response.status,
          errorData
        );
      }
      const data = await response.json();
      console.log(`[API] Successfully fetched candidate ${candidateId}:`, data);
      return data;
    } catch (error: unknown) {
      console.error(
        `[API] Network error fetching candidate ${candidateId}:`,
        error
      );

      // If it's already an ApiError, re-throw it
      if (error && typeof error === "object" && "type" in error) {
        throw error;
      }

      // Handle network/connection errors
      throw this.createApiError(
        ErrorType.NETWORK_ERROR,
        `Unable to connect to server while fetching candidate ${candidateId}`,
        undefined,
        error
      );
    }
  }

  async getEnhancedCandidateDetails(candidateId: string): Promise<any> {
    console.log(
      `[API] Starting fetch for enhanced candidate details: ${candidateId}`
    );
    try {
      const response = await this.fetchWithRetries(
        `${this.baseURL}/api/v1/candidates/${candidateId}/enhanced`
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error(
          `[API] Error fetching enhanced candidate ${candidateId}:`,
          errorData
        );

        // Provide better error messages for common scenarios
        let errorMessage = "Failed to fetch enhanced candidate details";
        if (errorData.detail) {
          errorMessage = errorData.detail;
        } else if (response.status === 404) {
          errorMessage = "Candidate not found";
        } else if (response.status === 503) {
          errorMessage = "AI extraction service temporarily unavailable";
        } else if (response.status >= 500) {
          errorMessage =
            "Server error occurred while processing candidate data";
        }

        throw this.createApiError(
          response.status >= 500
            ? ErrorType.SERVER_ERROR
            : ErrorType.CLIENT_ERROR,
          errorMessage,
          response.status,
          errorData
        );
      }

      const data = await response.json();
      console.log(
        `[API] Successfully fetched enhanced candidate ${candidateId}:`,
        data
      );
      return data;
    } catch (error: unknown) {
      console.error(
        `[API] Network error fetching enhanced candidate ${candidateId}:`,
        error
      );

      // If it's already an ApiError, re-throw it
      if (error && typeof error === "object" && "type" in error) {
        throw error;
      }

      // Handle network/connection errors
      throw this.createApiError(
        ErrorType.NETWORK_ERROR,
        `Unable to connect to server while fetching enhanced candidate ${candidateId}`,
        undefined,
        error
      );
    }
  }
}

export const apiService = new RecruiterRadarAPI();

// Named exports for individual functions
export const analyzeComparison = (
  request: ComparisonRequest
): Promise<ComparisonAnalysisResponse> => apiService.analyzeComparison(request);
