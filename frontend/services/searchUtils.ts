/**
 * Search utility functions for RecruiterRadar
 */

/**
 * Common location abbreviations and their full names
 */
const LOCATION_MAP: Record<string, string> = {
  sf: "San Francisco",
  "bay area": "San Francisco",
  nyc: "New York",
  ny: "New York",
  la: "Los Angeles",
  chicago: "Chicago",
  seattle: "Seattle",
  austin: "Austin",
  boston: "Boston",
  denver: "Denver",
  dc: "Washington",
  tx: "Texas",
  ca: "California",
  wa: "Washington",
  il: "Illinois",
  ma: "Massachusetts",
};

export interface LocationParseResult {
  cleanQuery: string;
  location?: string;
}

/**
 * Clean text by removing emojis and extra whitespace
 */
export const cleanText = (text: string): string => {
  return text
    .replace(
      /[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/gu,
      ""
    )
    .trim()
    .replace(/\s+/g, " ");
};

/**
 * 🧠 SMART LOCATION EXTRACTION
 * Extracts location from natural language and maps common abbreviations
 */
export function parseLocationFromQuery(query: string): LocationParseResult {
  const locationPatterns = [
    /\b(?:in|at|from|near|around|based\s+in)\s+([A-Za-z\s,]+?)(?:\s*$|\s+(?:with|and|or|who|that|looking|seeking))/i,
    /\b([A-Za-z\s,]+?)\s+(?:based|located|area|region)\b/i,
    /\b(remote|onsite|hybrid|work\s+from\s+home|wfh)\b/i,
    /\b([A-Z]{2})\s*(?:,|\s|$)/i,
  ];
  let location: string | undefined;
  let cleanQuery = query;
  const locationMapping: Record<string, string> = {
    sf: "San Francisco",
    "san fran": "San Francisco",
    "bay area": "San Francisco",
    "silicon valley": "San Francisco",
    "palo alto": "San Francisco",
    nyc: "New York",
    "new york city": "New York",
    manhattan: "New York",
    brooklyn: "New York",
    la: "Los Angeles",
    "los angeles": "Los Angeles",
    hollywood: "Los Angeles",
    chi: "Chicago",
    chicago: "Chicago",
    "windy city": "Chicago",
    atx: "Austin",
    austin: "Austin",
    sea: "Seattle",
    seattle: "Seattle",
    "emerald city": "Seattle",
    bos: "Boston",
    boston: "Boston",
    "bean town": "Boston",
    den: "Denver",
    denver: "Denver",
    "mile high": "Denver",
    dc: "Washington",
    "washington dc": "Washington",
    dmv: "Washington",
    ca: "California",
    california: "California",
    ny: "New York",
    tx: "Texas",
    texas: "Texas",
    wa: "Washington",
    washington: "Washington",
    il: "Illinois",
    illinois: "Illinois",
    ma: "Massachusetts",
    massachusetts: "Massachusetts",
    co: "Colorado",
    colorado: "Colorado",
    remote: "Remote",
    wfh: "Remote",
    "work from home": "Remote",
    onsite: "On-site",
    hybrid: "Hybrid",
  };
  for (const pattern of locationPatterns) {
    const match = query.match(pattern);
    if (match) {
      const extractedLocation = match[1]?.trim().toLowerCase();
      if (extractedLocation) {
        location =
          locationMapping[extractedLocation] ||
          extractedLocation
            .split(" ")
            .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
            .join(" ");
        cleanQuery = query.replace(match[0], " ").replace(/\s+/g, " ").trim();
        break;
      }
    }
  }
  return { cleanQuery, location };
}

/**
 * 🔧 SKILL NORMALIZATION
 * Cleans emojis and normalizes skills
 */
export function normalizeSkills(skills: string): string {
  return skills
    .split(",")
    .map((skill) =>
      skill
        .replace(
          /[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/gu,
          ""
        )
        .trim()
        .toLowerCase()
    )
    .filter((skill) => skill.length > 0)
    .map((skill) => {
      const skillMappings: Record<string, string> = {
        js: "javascript",
        ts: "typescript",
        node: "nodejs",
        "react.js": "react",
        "vue.js": "vue",
        python3: "python",
        py: "python",
        postgres: "postgresql",
        mongo: "mongodb",
        k8s: "kubernetes",
        "ai/ml": "machine learning",
        ml: "machine learning",
        ai: "artificial intelligence",
        devops: "dev ops",
        fullstack: "full stack",
        "full-stack": "full stack",
        backend: "back end",
        frontend: "front end",
      };
      return skillMappings[skill] || skill;
    })
    .join(",");
}

/**
 * 🎯 EXTRACT SEARCH TERMS
 * For highlighting in results
 */
export function extractSearchTerms(query: string): string[] {
  return query
    .toLowerCase()
    .split(/\s+/)
    .filter((term) => term.length > 2)
    .map((term) => term.replace(/[^\w]/g, ""))
    .filter((term) => term.length > 0);
}
