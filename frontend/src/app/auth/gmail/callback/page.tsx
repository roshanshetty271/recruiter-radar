"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { GmailAuthService } from "@/services/gmailAuthService";
import { useToast } from "@/components/ui/use-toast";

export default function GmailCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get("code");
      const error = searchParams.get("error");
      const stateParam = searchParams.get("state");

      // Parse state parameter to get return context
      let returnContext = null;
      if (stateParam) {
        try {
          const decodedState = atob(stateParam);
          returnContext = JSON.parse(decodedState);
        } catch (error) {
          console.error("Failed to parse state parameter:", error);
        }
      }

      // Check if this is running in a popup window
      const isPopup = window.opener && window.opener !== window;

      if (error) {
        if (isPopup) {
          // Send error message to parent window
          window.opener.postMessage(
            {
              type: "GMAIL_AUTH_ERROR",
              error: "User denied access or an error occurred",
            },
            window.location.origin
          );
          window.close();
        } else {
          // Traditional redirect flow
          toast({
            title: "Gmail Connection Failed",
            description: "You denied access or an error occurred.",
            variant: "destructive",
          });

          // Redirect based on context or default to home
          const redirectPath =
            returnContext?.returnTo === "outreach" && returnContext?.candidateId
              ? `/?candidate=${returnContext.candidateId}&action=outreach&error=auth_failed`
              : "/";
          router.push(redirectPath);
        }
        return;
      }

      if (code) {
        try {
          // Exchange code for tokens
          const response = await fetch("/api/auth/gmail", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ code }),
          });

          if (!response.ok) throw new Error("Failed to authenticate");

          const { tokens } = await response.json();

          if (isPopup) {
            // Send success message to parent window
            window.opener.postMessage(
              {
                type: "GMAIL_AUTH_SUCCESS",
                tokens: tokens,
              },
              window.location.origin
            );
            window.close();
          } else {
            // Traditional redirect flow - store tokens
            GmailAuthService.getInstance().storeTokens(tokens);

            // Smart redirect based on context
            if (
              returnContext?.returnTo === "outreach" &&
              returnContext?.candidateId
            ) {
              // Redirect back to candidate with success flag
              const redirectPath = `/?candidate=${returnContext.candidateId}&action=outreach&gmail=connected`;
              router.push(redirectPath);
            } else {
              // Default success flow
              toast({
                title: "Gmail Connected!",
                description:
                  "You can now send emails directly from RecruiterRadar.",
              });
              router.push("/");
            }
          }
        } catch (error) {
          if (isPopup) {
            // Send error message to parent window
            window.opener.postMessage(
              {
                type: "GMAIL_AUTH_ERROR",
                error: "Failed to connect Gmail. Please try again.",
              },
              window.location.origin
            );
            window.close();
          } else {
            // Traditional redirect flow
            toast({
              title: "Connection Failed",
              description: "Failed to connect Gmail. Please try again.",
              variant: "destructive",
            });

            // Redirect based on context or default to home
            const redirectPath =
              returnContext?.returnTo === "outreach" &&
              returnContext?.candidateId
                ? `/?candidate=${returnContext.candidateId}&action=outreach&error=connection_failed`
                : "/";
            router.push(redirectPath);
          }
        }
      }
    };

    handleCallback();
  }, [searchParams, router, toast]);

  return (
    <div className="flex h-screen items-center justify-center bg-slate-900">
      <div className="text-center">
        <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-blue-500" />
        <p className="text-slate-300">Connecting Gmail...</p>
        <p className="text-sm text-slate-500 mt-2">
          Returning to your outreach...
        </p>
      </div>
    </div>
  );
}
