import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/ui/use-toast";
import {
  Mail,
  Shield,
  Check,
  Loader2,
  AlertCircle,
  Link,
  X,
} from "lucide-react";
import { GmailAuthService } from "@/services/gmailAuthService";
import type { FrontendCandidate } from "@/lib/types";

interface GmailConnectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  onCancel: () => void;
  candidate: FrontendCandidate;
  jobTitle: string;
}

export function GmailConnectionModal({
  isOpen,
  onClose,
  onSuccess,
  onCancel,
  candidate,
  jobTitle,
}: GmailConnectionModalProps) {
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectionStep, setConnectionStep] = useState<
    "prompt" | "connecting" | "success" | "error"
  >("prompt");
  const [errorMessage, setErrorMessage] = useState("");
  const { toast } = useToast();

  const gmailAuth = GmailAuthService.getInstance();

  const handleConnect = async () => {
    setIsConnecting(true);
    setConnectionStep("connecting");

    // For Option B: Full-page redirect
    // Create state with candidate context for return navigation
    const oauthState = JSON.stringify({
      candidateId: candidate.id,
      candidateName: candidate.name,
      returnTo: "outreach",
      timestamp: Date.now(),
    });

    const authUrl = gmailAuth.getAuthUrl(btoa(oauthState)); // Base64 encode the state
    window.location.href = authUrl;
  };

  const handleCancel = () => {
    setIsConnecting(false);
    setConnectionStep("prompt");
    onCancel();
  };

  const handleRetry = () => {
    setConnectionStep("prompt");
    setErrorMessage("");
    setIsConnecting(false);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <Dialog open={isOpen} onOpenChange={onClose}>
          <DialogContent className="max-w-md p-0 overflow-hidden bg-slate-900 border-slate-800">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.2 }}
            >
              {/* Header */}
              <DialogHeader className="px-6 pt-6 pb-4">
                <div className="flex items-center gap-3">
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="p-2 bg-gradient-to-br from-blue-500 to-purple-500 rounded-lg"
                  >
                    <Link className="h-5 w-5 text-white" />
                  </motion.div>
                  <div>
                    <DialogTitle className="text-xl font-bold text-slate-100">
                      Connect Gmail to Send
                    </DialogTitle>
                    <p className="text-sm text-slate-400 mt-1">
                      Send your personalized message to {candidate.name}
                    </p>
                  </div>
                </div>
              </DialogHeader>

              {/* Content */}
              <div className="px-6 pb-6">
                {connectionStep === "prompt" && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="space-y-4"
                  >
                    {/* Job Context */}
                    <div className="bg-gradient-to-r from-blue-900/50 to-purple-900/50 border border-blue-800/50 rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Mail className="h-4 w-4 text-blue-400" />
                        <span className="font-medium text-blue-200">
                          Ready to Send:
                        </span>
                      </div>
                      <p className="text-sm text-blue-100">
                        <strong>{jobTitle}</strong> opportunity for{" "}
                        {candidate.name}
                      </p>
                      <p className="text-xs text-blue-300 mt-1">
                        To: {candidate.email}
                      </p>
                    </div>

                    {/* Security Info */}
                    <div className="space-y-3">
                      <p className="text-sm text-slate-300">
                        To send this email, we need to connect your Gmail
                        account securely:
                      </p>

                      <div className="space-y-2">
                        <div className="flex items-center gap-2 text-sm text-slate-400">
                          <Shield className="h-4 w-4 text-green-400" />
                          <span>Secure OAuth 2.0 authentication</span>
                        </div>
                        <div className="flex items-center gap-2 text-sm text-slate-400">
                          <Shield className="h-4 w-4 text-green-400" />
                          <span>We never store your password</span>
                        </div>
                        <div className="flex items-center gap-2 text-sm text-slate-400">
                          <Shield className="h-4 w-4 text-green-400" />
                          <span>Revoke access anytime in Google settings</span>
                        </div>
                      </div>

                      <Badge
                        variant="secondary"
                        className="text-xs bg-slate-800 text-slate-300 border-slate-700"
                      >
                        Only "Send Email" permission requested
                      </Badge>
                    </div>

                    {/* Redirect Notice */}
                    <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-3">
                      <p className="text-xs text-slate-400">
                        You'll be redirected to Google for secure
                        authentication, then back to complete sending.
                      </p>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-3 pt-2">
                      <Button
                        onClick={handleCancel}
                        variant="outline"
                        className="flex-1 border-slate-700 text-slate-300 hover:bg-slate-800"
                      >
                        Cancel
                      </Button>
                      <Button
                        onClick={handleConnect}
                        disabled={isConnecting}
                        className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                      >
                        <Mail className="h-4 w-4 mr-2" />
                        Connect Gmail
                      </Button>
                    </div>
                  </motion.div>
                )}

                {connectionStep === "connecting" && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="text-center py-8"
                  >
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{
                        repeat: Infinity,
                        duration: 1,
                        ease: "linear",
                      }}
                    >
                      <Loader2 className="h-8 w-8 mx-auto text-blue-500 mb-4" />
                    </motion.div>
                    <h3 className="font-semibold mb-2 text-slate-100">
                      Connecting to Gmail...
                    </h3>
                    <p className="text-sm text-slate-400">
                      Redirecting to Google for authentication...
                    </p>
                  </motion.div>
                )}

                {connectionStep === "success" && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="text-center py-8"
                  >
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: 0.2 }}
                    >
                      <Check className="h-8 w-8 mx-auto text-green-400 mb-4" />
                    </motion.div>
                    <h3 className="font-semibold mb-2 text-green-400">
                      Gmail Connected!
                    </h3>
                    <p className="text-sm text-slate-400">
                      Sending your message to {candidate.name}...
                    </p>
                  </motion.div>
                )}

                {connectionStep === "error" && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="space-y-4"
                  >
                    <div className="text-center py-4">
                      <AlertCircle className="h-8 w-8 mx-auto text-red-400 mb-4" />
                      <h3 className="font-semibold mb-2 text-red-400">
                        Connection Failed
                      </h3>
                      <p className="text-sm text-slate-400">{errorMessage}</p>
                    </div>

                    <div className="flex gap-3">
                      <Button
                        onClick={handleCancel}
                        variant="outline"
                        className="flex-1 border-slate-700 text-slate-300 hover:bg-slate-800"
                      >
                        Cancel
                      </Button>
                      <Button
                        onClick={handleRetry}
                        className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                      >
                        Try Again
                      </Button>
                    </div>
                  </motion.div>
                )}
              </div>
            </motion.div>
          </DialogContent>
        </Dialog>
      )}
    </AnimatePresence>
  );
}
