/**
 * TypeScript interfaces for the RecruiterRadar API
 */

// The raw candidate result from the backend API
export interface BackendCandidateResult {
  id: string;
  name: string;
  summary_text?: string;
  skills: string[];
  experience_years?: number;
  location?: string;
  visa_status?: string;
  relevance_score: number;
  match_context?: string;
  linkedin_url?: string;
  github_url?: string;
}

// The search response from the backend API
export interface BackendSearchResponse {
  results: BackendCandidateResult[];
  total_results: number;
  search_time_ms: number;
  query_interpretation?: string;
  retrieved_count_before_post_filter?: number;
  final_count_after_post_filter?: number;
  top_matched_query_skills?: string[];
}

// The candidate format used by the frontend UI
export interface FrontendCandidate {
  id: string;
  name: string;
  title: string;
  location: string;
  distance?: string;
  matchScore: number;
  experience?: number;
  skills: string[];
  isOnline: boolean;
  isVerified: boolean;
  avatar: string;
  visaStatus?: string;
  githubUrl?: string;
  linkedinUrl?: string;
}

// The request body for generating outreach
export interface OutreachRequestBody {
  job_role_title: string;
  job_role_description?: string;
  tone?: string;
  company_context?: string;
  additional_instructions?: string;
  generate_variations?: boolean;
  custom_tones?: string[];
}

// The response from the outreach generation API
export interface OutreachResponse {
  draft_message: string;
  candidate_name: string;
  candidate_id: string;
  job_role_title: string;
  generated_at: string;
  generation_time_ms: number;
  word_count: number;
  character_count: number;
  tone_used: string;
  personalization_elements?: string[];
  variations?: OutreachVariation[];
  total_variations_generated: number;
  recommended_variation_index?: number;
}

export interface BackendCandidate {
  id: string;
  name: string;
  skills: string[];
  experience_years: number;
  location: string;
  visa_status: string;
  match_context: string;
  relevance_score: number;
  github_url?: string;
  linkedin_url?: string;
}

export interface OutreachVariation {
  tone: string;
  draft_message: string;
  word_count: number;
  character_count: number;
  personalization_score?: number;
}

export interface SearchFilters {
  location: string;
  visa_status: string;
  min_experience: number;
  skills: string;
}

export interface SearchMetrics {
  totalResults: number;
  searchTimeMs: number;
  queryInterpretation: string | null;
}
