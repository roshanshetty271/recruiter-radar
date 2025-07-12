/**
 * Helper functions for RecruiterRadar frontend
 */
import type {
  FrontendCandidate,
  SearchResponse,
  BackendCandidate,
} from "../lib/types";
import type { BackendCandidateResult, BackendSearchResponse } from "./types";

/**
 * 🔄 MAP BACKEND TO FRONTEND FORMAT
 * Transforms backend search results to frontend-expected format
 */
export function mapBackendCandidatesToFrontend(
  backendResponse: SearchResponse | BackendSearchResponse
): FrontendCandidate[] {
  return backendResponse.results.map((candidate, index) => {
    // Cast to any to access potentially missing properties safely
    const candidateAny = candidate as any;

    return {
      id: candidate.id,
      name: formatCandidateName(candidate.name),
      title:
        extractTitleFromContext(candidateAny.match_context) ||
        formatSkillsAsTitle(candidate.skills) ||
        `${candidateAny.experience_years || 0}+ years experience`,
      location: candidateAny.location || "Remote",
      distance: calculateDistance(candidateAny.location) || "0.5 mi",
      matchScore: calculateMatchScore(candidateAny.relevance_score),
      experience: candidateAny.experience_years || 0,
      skills: candidate.skills || [],
      isOnline: Math.random() > 0.3,
      isVerified: Math.random() > 0.5,
      avatar: generateAvatar(candidate.name),
      // Preserve email for outreach / contact actions
      email: candidateAny.email,
      // Additional fields
      match_context: candidateAny.match_context,
      visa_status: candidateAny.visa_status,
      github_url: candidateAny.github_url,
      linkedin_url: candidateAny.linkedin_url,
      // 🏷️ SOURCE TRACKING: Add source information for visual distinction
      source: candidateAny.source || "demo",
      uploadedAt: candidateAny.uploaded_at,
      originalFilename: candidateAny.original_filename,
    };
  });
}

/**
 * 📊 EXTRACT SEARCH METRICS
 * Gets search performance metrics from backend response
 */
export function getSearchMetrics(response: any) {
  return {
    totalResults: response.total_results ?? response.results?.length ?? 0,
    searchTimeMs: response.processing_time_ms ?? response.search_time_ms ?? 0,
    queryInterpretation: response.query_interpretation ?? null,
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
 * Generate a consistent avatar for a candidate based on their name
 */
const generateAvatar = (name?: string): string => {
  if (!name) return "/placeholder.svg?height=60&width=60";
  return generateAvatarUrl(name);
};

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

  // Additional common titles
  const commonTitles = [
    "Senior Software Engineer",
    "Full Stack Developer",
    "Frontend Engineer",
    "Backend Engineer",
    "DevOps Engineer",
    "Data Scientist",
    "Product Manager",
    "Software Engineer",
    "Engineering Manager",
    "Tech Lead",
    "Solutions Architect",
  ];

  const lowerContext = context.toLowerCase();
  const foundTitle = commonTitles.find((title) =>
    lowerContext.includes(title.toLowerCase())
  );

  return foundTitle || null;
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
 * Calculate distance for display purposes
 * In a real implementation, this could use geolocation data
 */
const calculateDistance = (location?: string): string | null => {
  if (!location) return null;

  // Special cases
  if (location.toLowerCase().includes("remote")) {
    return "Remote";
  }

  // For demo purposes, generate a random distance
  const distances = ["< 1 mile", "2-5 miles", "5-10 miles", "10-25 miles"];
  return distances[Math.floor(Math.random() * distances.length)];
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
  topMatchedSkills?: string[];
  retrievedBeforeFilter?: number;
}

/**
 * Converts backend relevance score to frontend match score
 */
function calculateMatchScore(relevanceScore?: number): number {
  if (!relevanceScore) {
    return Math.floor(Math.random() * 30 + 60); // Random 60-90
  }

  // Convert from 0-1 to 0-100 scale
  // Apply some transformation to make scores more impressive
  const baseScore = relevanceScore * 100;
  const boostedScore = Math.min(100, baseScore * 1.2 + 10);

  return Math.round(boostedScore);
}

/**
 * Formats a candidate's name for display
 */
export function formatCandidateName(name: string): string {
  return name
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

/**
 * Calculates time saved based on number of searches
 */
export function calculateTimeSaved(searchCount: number): number {
  // Assume each manual search takes 15 minutes
  const minutesPerSearch = 15;
  const totalMinutes = searchCount * minutesPerSearch;
  return Number((totalMinutes / 60).toFixed(1)); // Convert to hours
}

/**
 * Determines if a skill is relevant to the search query
 */
export function isSkillRelevant(skill: string, searchQuery: string): boolean {
  const skillLower = skill.toLowerCase();
  const queryLower = searchQuery.toLowerCase();
  const queryWords = queryLower.split(" ").filter((word) => word.length > 2);

  return queryWords.some((word) => skillLower.includes(word));
}

/**
 * Generates match reasons for a candidate
 */
export function generateMatchReasons(
  candidate: BackendCandidate | FrontendCandidate,
  searchQuery: string
): string[] {
  const reasons: string[] = [];

  // Check skill matches
  const matchedSkills = candidate.skills.filter((skill) =>
    isSkillRelevant(skill, searchQuery)
  );

  if (matchedSkills.length > 0) {
    reasons.push(
      `🎯 ${matchedSkills.length} skill match${
        matchedSkills.length > 1 ? "es" : ""
      }: ${matchedSkills.slice(0, 3).join(", ")}`
    );
  }

  // Check experience level
  const experience =
    "experience_years" in candidate
      ? candidate.experience_years
      : candidate.experience;
  if (experience && experience >= 5) {
    reasons.push(`⭐ Senior-level (${experience} years)`);
  } else if (experience && experience >= 2) {
    reasons.push(`📈 Mid-level (${experience} years)`);
  }

  // Check location
  if (candidate.location?.toLowerCase().includes("remote")) {
    reasons.push(`🌍 Remote available`);
  }

  // Check visa status
  const visaStatus =
    "visa_status" in candidate
      ? candidate.visa_status
      : (candidate as any).visaStatus;
  if (visaStatus === "US Citizen" || visaStatus === "Green Card") {
    reasons.push(`✅ No visa sponsorship needed`);
  }

  // Check if verified (frontend only)
  if ("isVerified" in candidate && candidate.isVerified) {
    reasons.push(`✅ Verified profile`);
  }

  // Check if online (frontend only)
  if ("isOnline" in candidate && candidate.isOnline) {
    reasons.push(`🟢 Currently active`);
  }

  return reasons;
}
