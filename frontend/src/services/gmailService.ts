import { GmailAuthService } from "./gmailAuthService";

export interface EmailMessage {
  to: string;
  subject: string;
  body: string;
  candidateName?: string;
  candidateId?: string;
}

export class GmailService {
  private static instance: GmailService;
  private authService: GmailAuthService;

  private constructor() {
    this.authService = GmailAuthService.getInstance();
  }

  static getInstance(): GmailService {
    if (!GmailService.instance) {
      GmailService.instance = new GmailService();
    }
    return GmailService.instance;
  }

  // Create email in MIME format
  private createMimeMessage(email: EmailMessage): string {
    const messageParts = [
      'Content-Type: text/plain; charset="UTF-8"',
      "MIME-Version: 1.0",
      `To: ${email.to}`,
      `Subject: ${email.subject}`,
      "",
      email.body,
    ];

    const message = messageParts.join("\n");

    // ---- UTF-8 safe Base64url encoding ----
    // btoa() only works reliably on Latin-1 strings. Convert Unicode → UTF-8 → binary string first.
    const utf8ToBinary = (str: string) =>
      encodeURIComponent(str).replace(/%([0-9A-F]{2})/g, (_, p1) =>
        String.fromCharCode(parseInt(p1, 16))
      );

    const base64 = btoa(utf8ToBinary(message));

    // Convert to URL-safe variant required by Gmail API
    return base64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  // Send email via Gmail API
  async sendEmail(email: EmailMessage): Promise<any> {
    const tokens = this.authService.getStoredTokens();
    if (!tokens) {
      throw new Error("Not authenticated with Gmail");
    }

    const messageRaw = this.createMimeMessage(email);

    const response = await fetch(
      "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${tokens.access_token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ raw: messageRaw }),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error?.message || "Failed to send email");
    }

    return response.json();
  }
}
