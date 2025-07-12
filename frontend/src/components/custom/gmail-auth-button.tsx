import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Mail, Check, Loader2 } from "lucide-react";
import { GmailAuthService } from "@/services/gmailAuthService";
import { useToast } from "@/components/ui/use-toast";

export function GmailAuthButton() {
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const { toast } = useToast();
  const authService = GmailAuthService.getInstance();

  // Check if already authenticated on mount
  useState(() => {
    setIsConnected(authService.isAuthenticated());
  });

  const handleConnect = () => {
    setIsLoading(true);
    const authUrl = authService.getAuthUrl();
    window.location.href = authUrl;
  };

  const handleDisconnect = () => {
    authService.logout();
    setIsConnected(false);
    toast({
      title: "Gmail Disconnected",
      description: "Your Gmail account has been disconnected.",
    });
  };

  if (isConnected) {
    return (
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-2 text-sm text-green-600">
          <Check className="w-4 h-4" />
          Gmail Connected
        </div>
        <Button variant="outline" size="sm" onClick={handleDisconnect}>
          Disconnect
        </Button>
      </div>
    );
  }

  return (
    <Button
      onClick={handleConnect}
      disabled={isLoading}
      className="bg-white hover:bg-gray-100 text-gray-700 border border-gray-300"
    >
      {isLoading ? (
        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
      ) : (
        <Mail className="w-4 h-4 mr-2" />
      )}
      Connect Gmail
    </Button>
  );
}
