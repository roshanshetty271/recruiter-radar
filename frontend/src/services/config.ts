// services/config.ts
export const config = {
  api: {
    baseUrl: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    timeout: 15000,
    // Timeout (in ms) for heavy, long-running operations such as multi-file resume uploads
    longTimeout: 120000,
    retries: 3,
  },
  app: {
    name: process.env.NEXT_PUBLIC_APP_NAME || "RecruiterRadar",
    version: process.env.NEXT_PUBLIC_VERSION || "1.0.0",
    enableAnalytics: process.env.NEXT_PUBLIC_ENABLE_ANALYTICS === "true",
  },
  features: {
    enableLocationExtraction: true,
    enableSkillNormalization: true,
    enableFuzzyMatching: true,
    enableOutreachVariations: false, // MVP V1
    enableAdvancedFilters: true,
  },
} as const;
