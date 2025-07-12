import { NextRequest, NextResponse } from "next/server";
import { google } from "googleapis";

const oauth2Client = new google.auth.OAuth2(
  process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID,
  process.env.GOOGLE_CLIENT_SECRET,
  process.env.NEXT_PUBLIC_GMAIL_REDIRECT_URI
);

export async function POST(request: NextRequest) {
  try {
    const { code } = await request.json();

    // Exchange code for tokens
    const { tokens } = await oauth2Client.getToken(code);

    return NextResponse.json({ tokens });
  } catch (error) {
    console.error("Gmail auth error:", error);
    return NextResponse.json(
      { error: "Failed to authenticate" },
      { status: 500 }
    );
  }
}
