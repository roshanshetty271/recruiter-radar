/**
 * Helper functions for RecruiterRadar frontend
 */
import { BackendSearchResponse, FrontendCandidate } from "./types";

/**
 * 🔄 MAP BACKEND TO FRONTEND FORMAT
 * Transforms backend search results to frontend-expected format
 */
export function mapBackendCandidatesToFrontend(
  backendResponse: BackendSearchResponse
): FrontendCandidate[] {
  return backendResponse.results.map((candidate, index) => ({
    id: candidate.id,
    name: candidate.name,
    title: `${candidate.experience_years}+ years experience`,
    location: candidate.location || "Remote",
    distance: "0.5 mi",
    matchScore: Math.round((candidate.relevance_score || 0.7) * 100),
    experience: candidate.experience_years || 0,
    skills: candidate.skills || [],
    isOnline: Math.random() > 0.3,
    isVerified: Math.random() > 0.5,
    avatar: `https://api.dicebear.com/7.x/avataaars/svg?seed=${candidate.name}`,
    match_context: candidate.match_context,
    visa_status: candidate.visa_status,
    github_url: candidate.github_url,
    linkedin_url: candidate.linkedin_url,
  }));
}

/**
 * 📊 EXTRACT SEARCH METRICS
 * Gets search performance metrics from backend response
 */
export function getSearchMetrics(backendResponse: BackendSearchResponse) {
  return {
    totalResults:
      backendResponse.total_results || backendResponse.results.length,
    searchTimeMs: backendResponse.search_time_ms || 0,
    queryInterpretation: backendResponse.query_interpretation || null,
  };
}

/**
 * 🎨 GENERATE AVATAR URL
 * Creates consistent avatar URLs for candidates
 */
export function generateAvatarUrl(
  name: string,
  style: "avataaars" | "personas" = "avataaars"
): string {
  const seed = encodeURIComponent(name.replace(/\s+/g, ""));
  return `https://api.dicebear.com/7.x/${style}/svg?seed=${seed}`;
}

/**
 * 🏷️ SKILL COLOR MAPPING
 * Returns consistent colors for skill badges
 */
export function getSkillColor(skill: string): string {
  const colors = [
    "bg-blue-500/20 text-blue-200",
    "bg-green-500/20 text-green-200",
    "bg-purple-500/20 text-purple-200",
    "bg-orange-500/20 text-orange-200",
    "bg-pink-500/20 text-pink-200",
    "bg-indigo-500/20 text-indigo-200",
    "bg-yellow-500/20 text-yellow-200",
    "bg-red-500/20 text-red-200",
  ];
  const hash = skill.split("").reduce((a, b) => {
    a = (a << 5) - a + b.charCodeAt(0);
    return a & a;
  }, 0);
  return colors[Math.abs(hash) % colors.length];
}

/**
 * ⏱️ FORMAT DURATION
 * Formats milliseconds to human readable duration
 */
export function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.round(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`;
}

/**
 * 🔍 HIGHLIGHT TEXT
 * Highlights search terms in text
 */
export function highlightSearchTerms(
  text: string,
  searchTerms: string[]
): string {
  let highlightedText = text;
  searchTerms.forEach((term) => {
    if (term.length > 2) {
      const regex = new RegExp(`(${term})`, "gi");
      highlightedText = highlightedText.replace(
        regex,
        '<mark class="bg-yellow-200 text-yellow-900 px-1 rounded">$1</mark>'
      );
    }
  });
  return highlightedText;
}

/**
 * Extract a title from the match context (resume text)
 */
const extractTitleFromContext = (context?: string): string | null => {
  if (!context) return null;

  // Look for patterns that might indicate a job title
  const titlePatterns = [
    /\b(Senior|Lead|Principal|Staff|Junior|Associate)\s+[A-Z][a-z]+((\s+[A-Z][a-z]+)+)?\b/,
    /\b(Software|Frontend|Backend|Full Stack|Data|Machine Learning|DevOps)\s+[A-Z][a-z]+((\s+[A-Z][a-z]+)+)?\b/,
    /\b[A-Z][a-z]+((\s+[A-Z][a-z]+){1,2})\s+(Engineer|Developer|Architect|Scientist|Analyst)\b/,
  ];

  for (const pattern of titlePatterns) {
    const match = context.match(pattern);
    if (match) {
      return match[0];
    }
  }

  return null;
};

/**
 * Format skills as a title when we can't extract one
 */
const formatSkillsAsTitle = (skills: string[]): string => {
  if (!skills || !skills.length) return "Software Professional";

  const topSkills = skills.slice(0, 3);
  if (topSkills.length === 1) {
    return `${topSkills[0]} Developer`;
  }

  return `${topSkills.join(", ")} Developer`;
};

/**
 * Generate a consistent avatar for a candidate based on their name
 */
const generateAvatar = (name?: string): string => {
  if (!name) return "/placeholder.svg?height=60&width=60";

  // Use a placeholder service that generates avatars from names
  // For a real implementation, consider using a service like DiceBear, UI Avatars, etc.
  return `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(
    name
  )}`;
};

/**
 * Calculate distance for display purposes
 * In a real implementation, this could use geolocation data
 */
const calculateDistance = (location?: string): string | null => {
  if (!location) return null;

  // For demo purposes, generate a random distance
  const distance = (Math.random() * 9.5 + 0.5).toFixed(1);
  return `${distance} miles`;
};

/**
 * Format date for display
 */
export const formatDate = (dateString?: string): string => {
  if (!dateString) return "";

  const date = new Date(dateString);
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
};

/**
 * Get search metrics for display
 */
export interface SearchMetrics {
  totalResults: number;
  searchTimeMs: number;
  queryInterpretation: string | null;
}
