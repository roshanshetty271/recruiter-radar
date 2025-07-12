import { google } from "googleapis";

export interface GmailAuthTokens {
  access_token: string;
  refresh_token?: string;
  expiry_date?: number;
}

export class GmailAuthService {
  private static instance: GmailAuthService;
  private tokens: GmailAuthTokens | null = null;

  // Gmail API scopes
  static SCOPES = ["https://www.googleapis.com/auth/gmail.send"];

  static getInstance(): GmailAuthService {
    if (!GmailAuthService.instance) {
      GmailAuthService.instance = new GmailAuthService();
    }
    return GmailAuthService.instance;
  }

  // Generate OAuth URL for user consent
  getAuthUrl(state?: string): string {
    const params = new URLSearchParams({
      client_id: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID!,
      redirect_uri: process.env.NEXT_PUBLIC_GMAIL_REDIRECT_URI!,
      response_type: "code",
      scope: GmailAuthService.SCOPES.join(" "),
      access_type: "offline",
      prompt: "consent",
    });

    // Add state parameter if provided
    if (state) {
      params.set("state", state);
    }

    return `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
  }

  // Store tokens in localStorage (in production, consider more secure storage)
  storeTokens(tokens: GmailAuthTokens): void {
    this.tokens = tokens;
    localStorage.setItem("gmail_tokens", JSON.stringify(tokens));
  }

  // Retrieve stored tokens
  getStoredTokens(): GmailAuthTokens | null {
    if (this.tokens) return this.tokens;

    const stored = localStorage.getItem("gmail_tokens");
    if (stored) {
      this.tokens = JSON.parse(stored);
      return this.tokens;
    }
    return null;
  }

  // Check if user is authenticated
  isAuthenticated(): boolean {
    const tokens = this.getStoredTokens();
    if (!tokens) return false;

    // Check if token is expired
    if (tokens.expiry_date && tokens.expiry_date < Date.now()) {
      // TODO: Implement token refresh
      return false;
    }

    return true;
  }

  // Clear authentication
  logout(): void {
    this.tokens = null;
    localStorage.removeItem("gmail_tokens");
  }
}
