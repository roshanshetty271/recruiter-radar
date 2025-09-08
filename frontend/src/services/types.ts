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
  source?: string; // 'demo' or 'uploaded_resume_batch'
  uploaded_at?: string;
  original_filename?: string;
}

// Pagination metadata for search results
export interface PaginationInfo {
  current_page: number;
  page_size: number;
  total_candidates: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
  start_index: number;
  end_index: number;
}

// Enhanced search metadata
export interface SearchMetadata {
  query: string;
  processing_time_ms: number;
  filters_applied: Record<string, any>;
  ai_confidence: number;
  semantic_themes: string[];
  suggested_refinements: string[];
}

// The enhanced search response from the backend API with pagination
export interface BackendSearchResponse {
  results: BackendCandidateResult[];
  pagination: PaginationInfo;
  search_metadata: SearchMetadata;

  // Backward compatibility fields
  total_results: number;
  search_time_ms: number;
  query_interpretation?: string;
  suggested_filters?: Record<string, any>;
  search_metadata_legacy?: Record<string, any>;

  // Legacy fields (for backward compatibility)
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
  source?: string; // 'demo' or 'uploaded_resume_batch'
  uploadedAt?: string;
  originalFilename?: string;
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

// Complete candidate profile from the backend (for view profile modal)
export interface CandidateProfile {
  id: string;
  name: string;
  email?: string;
  raw_resume_text: string;
  skills: string[];
  experience_years: number;
  visa_status?: string;
  location?: string;
  github_url?: string;
  linkedin_url?: string;
}

// AI insights response for candidates
export interface CandidateInsightsResponse {
  candidate_id: string;
  candidate_name: string;
  fit_score: number;
  key_strengths: string[];
  areas_for_development: string[];
  interview_questions: string[];
  confidence_level: number;
  insights_generated_at: string;
  generation_time_ms: number;
  insights_version: string;
}

// ============= AI Comparison Analysis Types =============

// Hidden insight discovered by AI about a candidate
export interface HiddenInsight {
  candidate_id: string;
  insight_type: string;
  title: string;
  description: string;
  impact_level: "high" | "medium" | "low";
}

// Visual comparison matrix showing how candidates rank across criteria
export interface ComparisonMatrix {
  technical_match: Record<string, number>;
  culture_fit: Record<string, number>;
  retention_risk: Record<string, number>;
  growth_potential: Record<string, number>;
}

// AI's recommended candidate with reasoning
export interface ComparisonWinner {
  candidate_id: string;
  candidate_name: string;
  confidence: number;
  reasoning: string;
  key_advantages: string[];
  potential_risks: string[];
}

// Individual candidate insights (simplified version matching backend)
export interface SimpleCandidateInsights {
  candidate_id: string;
  fit_score: number;
  strengths: string[];
  interview_questions: string[];
}

// Complete AI comparison analysis response
export interface ComparisonAnalysisResponse {
  winner: ComparisonWinner;
  candidates: SimpleCandidateInsights[];
  hidden_insights: HiddenInsight[];
  comparison_matrix: ComparisonMatrix;
  analysis_timestamp: string;
  processing_time_ms: number;
  job_context?: string;
  ai_confidence: number;
}

// Request body for comparison analysis
export interface ComparisonRequest {
  candidate_ids: string[];
  job_role_title?: string;
  job_role_description?: string;
  company_context?: string;
}

// Enhanced candidate profile data from backend AI extraction
export interface WorkExperienceItem {
  company: string;
  title?: string; // Backend provides 'title'
  position?: string; // Frontend legacy field
  duration: string;
  location?: string; // Backend provides 'location'
  description?: string; // Optional field
  technologies?: string[]; // Optional field
}

export interface EducationItem {
  school?: string; // Backend provides 'school'
  institution?: string; // Frontend legacy field
  degree: string;
  field?: string;
  graduation_year?: string | null; // Backend provides 'graduation_year'
  year?: string; // Frontend legacy field
  description?: string; // Detailed education information (coursework, internships, activities)
}

export interface EnhancedCandidateProfile {
  // Basic information
  id: string;
  name: string;
  email?: string;
  location?: string;
  experience_years: number;
  skills: string[];
  visa_status?: string;
  github_url?: string;
  linkedin_url?: string;
  raw_resume_text?: string;

  // Enhanced structured data
  professional_summary?: string;
  current_title?: string;
  work_experience: WorkExperienceItem[];
  education: EducationItem[];
  certifications: string[];
  languages: string[];
  key_achievements: string[];

  // Extraction metadata
  extraction_confidence: number;
  has_structured_data: boolean;
  extraction_timestamp?: string;
}
