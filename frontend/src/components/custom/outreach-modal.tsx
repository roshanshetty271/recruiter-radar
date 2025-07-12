import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/components/ui/use-toast";
import {
  Copy,
  CheckCircle2,
  User,
  Clock,
  FileText,
  Sparkles,
  TrendingUp,
  X,
  Mail,
  Send,
  Loader2,
} from "lucide-react";
import confetti from "canvas-confetti";

import { OutreachModalContainer } from "./outreach-modal-container";
import { OutreachForm } from "./outreach-form";
import { GenerationProgress } from "./generation-progress";
import { GmailAuthButton } from "./gmail-auth-button";
import { GmailConnectionModal } from "./gmail-connection-modal";
import { apiService } from "@/services/apiService";
import { GmailAuthService } from "@/services/gmailAuthService";
import { GmailService } from "@/services/gmailService";
import type { FrontendCandidate } from "@/lib/types";
import type { OutreachResponse } from "@/services/types";

interface OutreachModalProps {
  isOpen: boolean;
  onClose: () => void;
  candidate: FrontendCandidate | null;
  onSuccess?: () => void;
}

export function OutreachModal({
  isOpen,
  onClose,
  candidate,
  onSuccess,
}: OutreachModalProps) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [generationStage, setGenerationStage] = useState("");
  const [generatedMessage, setGeneratedMessage] =
    useState<OutreachResponse | null>(null);
  const [copied, setCopied] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  const [isGmailConnected, setIsGmailConnected] = useState(false);
  const [jobFormData, setJobFormData] = useState<any>(null); // Store form data for subject line
  const [showGmailConnectionModal, setShowGmailConnectionModal] =
    useState(false);
  const { toast } = useToast();

  const gmailAuth = GmailAuthService.getInstance();
  const gmailService = GmailService.getInstance();

  // Check Gmail connection status
  useEffect(() => {
    setIsGmailConnected(gmailAuth.isAuthenticated());
  }, [isOpen]);

  // Check for pending outreach after OAuth redirect
  useEffect(() => {
    if (isOpen && typeof window !== "undefined") {
      const pendingData = sessionStorage.getItem("pendingOutreach");
      if (pendingData) {
        try {
          const parsed = JSON.parse(pendingData);
          const isRecent = Date.now() - parsed.timestamp < 10 * 60 * 1000; // 10 minutes

          if (
            isRecent &&
            candidate?.id === parsed.candidateId &&
            gmailAuth.isAuthenticated()
          ) {
            // Restore state and auto-send
            setGeneratedMessage(parsed.generatedMessage);
            setJobFormData(parsed.jobFormData);

            // Clear pending data
            sessionStorage.removeItem("pendingOutreach");

            // Auto-send the email
            setTimeout(() => {
              handleGmailConnectionSuccess();
            }, 1000);

            toast({
              title: "Welcome Back!",
              description:
                "Gmail connected successfully. Sending your message...",
            });
          }
        } catch (error) {
          console.error("Failed to parse pending outreach data:", error);
          sessionStorage.removeItem("pendingOutreach");
        }
      }
    }
  }, [isOpen, candidate?.id]);

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setIsGenerating(false);
      setGenerationProgress(0);
      setGenerationStage("");
      setGeneratedMessage(null);
      setCopied(false);
      setEmailSent(false);
      setJobFormData(null);
    }
  }, [isOpen]);

  // Simulate progress during generation
  useEffect(() => {
    if (isGenerating && generationProgress < 90) {
      const timer = setTimeout(() => {
        setGenerationProgress((prev) => prev + Math.random() * 15);

        // Update stage based on progress
        if (generationProgress < 30) {
          setGenerationStage("Analyzing candidate profile...");
        } else if (generationProgress < 60) {
          setGenerationStage("Crafting personalized message...");
        } else {
          setGenerationStage("Optimizing tone and style...");
        }
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [isGenerating, generationProgress]);

  useEffect(() => {
    if (candidate) {
      console.log("Candidate email:", candidate.email); // DEBUG
      console.log("Gmail connected:", isGmailConnected); // DEBUG
      console.log("Email sent:", emailSent); // DEBUG
    }
  }, [candidate, isGmailConnected, emailSent]);

  const handleGenerateOutreach = async (formData: {
    jobTitle: string;
    jobDescription: string;
    tone: string;
    companyContext: string;
    additionalInstructions: string;
  }) => {
    if (!candidate) return;

    setIsGenerating(true);
    setGenerationProgress(10);
    setJobFormData(formData); // Store for email subject

    try {
      // Step 1: Generate the message
      setGenerationStage("Analyzing candidate profile...");
      const response = await apiService.generateOutreach(candidate.id, {
        job_role_title: formData.jobTitle,
        job_role_description: formData.jobDescription,
        tone: formData.tone,
        company_context: formData.companyContext,
        additional_instructions: formData.additionalInstructions,
      });

      setGenerationProgress(100);
      setGenerationStage("Message ready!");
      setGeneratedMessage(response);

      // Step 2: Check if we need to PROMPT for Gmail connection.
      // We no longer auto-send here. The user must click "Send" to dispatch the email.
      const currentGmailStatus = gmailAuth.isAuthenticated();
      setIsGmailConnected(currentGmailStatus);

      if (!currentGmailStatus && candidate.email) {
        // If not connected, we need to show the connection modal.
        // The post-OAuth auto-send is handled by a separate useEffect.
        if (typeof window !== "undefined") {
          sessionStorage.setItem(
            "pendingOutreach",
            JSON.stringify({
              candidateId: candidate.id,
              candidateName: candidate.name,
              candidateEmail: candidate.email,
              generatedMessage: response,
              jobFormData: formData,
              timestamp: Date.now(),
            })
          );
        }
        setShowGmailConnectionModal(true);
      }
      // If already connected, do nothing. The UI will render the "Send" button.
    } catch (apiError) {
      console.error("Outreach generation API call failed:", apiError);
      setGenerationProgress(100);
      setGenerationStage("Generation failed");
      toast({
        title: "Generation Failed",
        description:
          "Could not generate the outreach message. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSendViaGmail = async () => {
    if (!candidate) return;
    if (!generatedMessage || !candidate.email || !jobFormData) return;

    setIsSending(true);

    try {
      // Compose email
      const emailData = {
        to: candidate.email,
        subject: `Exciting ${jobFormData.jobTitle} Opportunity - ${
          jobFormData.companyContext?.split(".")[0] || "Your Next Career Move"
        }`,
        body: generatedMessage.draft_message,
        candidateName: candidate.name,
        candidateId: candidate.id,
      };

      await gmailService.sendEmail(emailData);

      // Success!
      setEmailSent(true);

      // Epic celebration
      confetti({
        particleCount: 200,
        spread: 100,
        origin: { y: 0.6 },
        colors: ["#4285f4", "#db4437", "#f4b400", "#0f9d58"], // Google colors
      });

      toast({
        title: "🎉 Outreach Delivered",
        description: `Your email to ${candidate.name} is on its way. Check your "Sent" folder for a copy.`,
        duration: 5000,
      });

      // Track in session metrics
      if (onSuccess) onSuccess();

      // The modal no longer auto-closes. The user can generate another or close manually.
    } catch (error) {
      console.error("Failed to send email:", error);

      // More specific error handling
      let errorTitle = "Failed to Send Email";
      let errorDescription = "Please try again";

      if (error instanceof Error) {
        if (error.message.includes("popup blocked")) {
          errorTitle = "Popup Blocked";
          errorDescription =
            "Please allow popups and try connecting Gmail again.";
        } else if (error.message.includes("Authentication")) {
          errorTitle = "Gmail Connection Lost";
          errorDescription =
            "Please reconnect your Gmail account and try again.";
        } else if (
          error.message.includes("quota") ||
          error.message.includes("rate")
        ) {
          errorTitle = "Gmail Rate Limit";
          errorDescription =
            "Please wait a moment before sending another email.";
        } else {
          errorDescription = error.message;
        }
      }

      toast({
        title: errorTitle,
        description: errorDescription,
        variant: "destructive",
        duration: 7000,
      });
    } finally {
      setIsSending(false);
    }
  };

  const handleCopy = async () => {
    if (!generatedMessage) return;

    try {
      await navigator.clipboard.writeText(generatedMessage.draft_message);
      setCopied(true);

      // Success feedback
      confetti({
        particleCount: 30,
        angle: 90,
        spread: 45,
        origin: { x: 0.5, y: 0.8 },
      });

      toast({
        title: "Copied to clipboard!",
        description: "Message is ready to send",
      });

      setTimeout(() => setCopied(false), 3000);
    } catch (error) {
      toast({
        title: "Copy failed",
        description: "Please try selecting and copying manually",
        variant: "destructive",
      });
    }
  };

  // Gmail connection modal handlers
  const handleGmailConnectionSuccess = async () => {
    setShowGmailConnectionModal(false);
    setIsGmailConnected(true);

    // Auto-send after successful connection
    if (candidate && generatedMessage && jobFormData) {
      setIsSending(true);

      try {
        const emailData = {
          to: candidate.email!,
          subject: `Exciting ${jobFormData.jobTitle} Opportunity - ${
            jobFormData.companyContext?.split(".")[0] || "Your Next Career Move"
          }`,
          body: generatedMessage.draft_message,
          candidateName: candidate.name,
          candidateId: candidate.id,
        };

        await gmailService.sendEmail(emailData);

        setEmailSent(true);

        // Epic celebration
        confetti({
          particleCount: 200,
          spread: 100,
          origin: { y: 0.6 },
          colors: ["#4285f4", "#db4437", "#f4b400", "#0f9d58"],
        });

        toast({
          title: "🎉 Outreach Delivered",
          description: `Your email to ${candidate.name} is on its way. Check your "Sent" folder for a copy.`,
          duration: 5000,
        });

        if (onSuccess) onSuccess();

        // The modal no longer auto-closes. The user can generate another or close manually.
      } catch (error) {
        console.error("Failed to send email after connection:", error);
        toast({
          title: "Connection Successful, Send Failed",
          description:
            "Gmail connected but send failed. Try the Send button below.",
          variant: "destructive",
        });
      } finally {
        setIsSending(false);
      }
    }
  };

  const handleGmailConnectionCancel = () => {
    setShowGmailConnectionModal(false);
    toast({
      title: "Connection Cancelled",
      description:
        "Your message is ready. You can copy it or connect Gmail later.",
    });
  };

  if (!candidate) return null;

  return (
    <OutreachModalContainer isOpen={isOpen}>
      <Dialog open={isOpen} onOpenChange={onClose}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden p-0 flex flex-col">
          {/* Header */}
          <DialogHeader className="px-6 pt-6 flex-shrink-0">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="p-2 bg-gradient-to-br from-blue-500 to-purple-500 rounded-lg"
                >
                  <Sparkles className="h-5 w-5 text-white" />
                </motion.div>
                <div>
                  <DialogTitle className="text-2xl font-bold">
                    AI Outreach Generator
                  </DialogTitle>
                  <p className="text-sm text-gray-600 flex items-center gap-2 mt-1">
                    <User className="h-3 w-3" />
                    {candidate.name} • {candidate.title}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <GmailAuthButton />
              </div>
            </div>
          </DialogHeader>

          <Separator className="my-6 flex-shrink-0" />

          {/* Content */}
          <div className="px-6 pb-8 flex-grow overflow-y-auto">
            {!generatedMessage ? (
              <>
                {isGenerating ? (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="py-12"
                  >
                    <GenerationProgress
                      progress={generationProgress}
                      stage={generationStage}
                    />
                  </motion.div>
                ) : (
                  <OutreachForm
                    onSubmit={handleGenerateOutreach}
                    isGenerating={isGenerating}
                  />
                )}
              </>
            ) : (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
              >
                {/* Tabs for future variations */}
                <Tabs defaultValue="professional" className="w-full">
                  <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="professional">Professional</TabsTrigger>
                    <TabsTrigger value="casual" disabled>
                      Casual
                      <Badge variant="secondary" className="ml-2 text-xs">
                        Soon
                      </Badge>
                    </TabsTrigger>
                    <TabsTrigger value="enthusiastic" disabled>
                      Enthusiastic
                      <Badge variant="secondary" className="ml-2 text-xs">
                        Soon
                      </Badge>
                    </TabsTrigger>
                  </TabsList>

                  <TabsContent value="professional" className="space-y-4 mt-6">
                    {/* Metrics */}
                    <div className="grid grid-cols-4 gap-4 mb-4">
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: 0.1 }}
                        className="bg-slate-800/50 p-3 rounded-lg text-center border border-slate-700"
                      >
                        <Clock className="h-4 w-4 mx-auto mb-1 text-slate-400" />
                        <p className="text-sm font-semibold text-slate-100">
                          {`${(
                            generatedMessage.generation_time_ms / 1000
                          ).toFixed(2)}s`}
                        </p>
                        <p className="text-xs text-slate-400">
                          Generation Time
                        </p>
                      </motion.div>

                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: 0.2 }}
                        className="bg-slate-800/50 p-3 rounded-lg text-center border border-slate-700"
                      >
                        <FileText className="h-4 w-4 mx-auto mb-1 text-slate-400" />
                        <p className="text-sm font-semibold text-slate-100">
                          {generatedMessage.word_count}
                        </p>
                        <p className="text-xs text-slate-400">Words</p>
                      </motion.div>

                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: 0.3 }}
                        className="bg-slate-800/50 p-3 rounded-lg text-center border border-slate-700"
                      >
                        <TrendingUp className="h-4 w-4 mx-auto mb-1 text-slate-400" />
                        <p className="text-sm font-semibold text-slate-100">
                          95%
                        </p>
                        <p className="text-xs text-slate-400">
                          Personalization
                        </p>
                      </motion.div>

                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: 0.4 }}
                        className="bg-slate-800/50 p-3 rounded-lg text-center border border-slate-700"
                      >
                        <Sparkles className="h-4 w-4 mx-auto mb-1 text-slate-400" />
                        <p className="text-sm font-semibold capitalize text-slate-100">
                          {generatedMessage.tone_used}
                        </p>
                        <p className="text-xs text-slate-400">Tone</p>
                      </motion.div>
                    </div>

                    {/* Message */}
                    <div className="relative">
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.5 }}
                        className="bg-slate-900/70 border border-slate-800 p-6 rounded-lg min-h-[200px]"
                      >
                        <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-slate-200">
                          {generatedMessage?.draft_message ||
                            (generatedMessage as any)?.message ||
                            (generatedMessage as any)?.content ||
                            (generatedMessage as any)?.text ||
                            JSON.stringify(generatedMessage, null, 2)}
                        </pre>
                      </motion.div>

                      {/* Copy Button */}
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: 0.6 }}
                        className="absolute top-4 right-4"
                      >
                        <Button
                          size="sm"
                          variant={copied ? "default" : "secondary"}
                          onClick={handleCopy}
                          className={
                            copied ? "bg-green-500 hover:bg-green-600" : ""
                          }
                        >
                          {copied ? (
                            <>
                              <CheckCircle2 className="h-4 w-4 mr-2" />
                              Copied!
                            </>
                          ) : (
                            <>
                              <Copy className="h-4 w-4 mr-2" />
                              Copy
                            </>
                          )}
                        </Button>
                      </motion.div>
                    </div>

                    {/* Personalization Elements */}
                    {generatedMessage.personalization_elements && (
                      <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.7 }}
                        className="space-y-3"
                      >
                        <p className="text-sm font-medium text-slate-300">
                          Personalization Elements Used:
                        </p>
                        <div className="flex flex-wrap gap-2">
                          {generatedMessage.personalization_elements.map(
                            (element, i) => (
                              <motion.div
                                key={i}
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                transition={{ delay: 0.8 + i * 0.1 }}
                              >
                                <Badge
                                  variant="outline"
                                  className="border-blue-400/50 bg-blue-900/20 text-blue-300"
                                >
                                  {element}
                                </Badge>
                              </motion.div>
                            )
                          )}
                        </div>
                      </motion.div>
                    )}

                    {/* Actions - Enhanced with Gmail Send */}
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: 0.9 }}
                      className="flex gap-3 pt-4"
                    >
                      <Button
                        onClick={() => {
                          setGeneratedMessage(null);
                          setGenerationProgress(0);
                          setEmailSent(false);
                        }}
                        variant="outline"
                        className="flex-1"
                      >
                        Generate Another
                      </Button>

                      {/* Gmail Send Button */}
                      {candidate.email && isGmailConnected && !emailSent ? (
                        <Button
                          onClick={handleSendViaGmail}
                          disabled={isSending}
                          className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                        >
                          {isSending ? (
                            <>
                              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                              Sending...
                            </>
                          ) : (
                            <>
                              <Mail className="h-4 w-4 mr-2" />
                              Send via Gmail
                            </>
                          )}
                        </Button>
                      ) : emailSent ? (
                        <Button
                          disabled
                          className="flex-1 bg-green-500 hover:bg-green-600"
                        >
                          <CheckCircle2 className="h-4 w-4 mr-2" />
                          Email Sent!
                        </Button>
                      ) : !candidate.email ? (
                        <Button disabled variant="outline" className="flex-1">
                          No Email Available
                        </Button>
                      ) : (
                        <Button
                          onClick={onClose}
                          className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600"
                        >
                          Done
                        </Button>
                      )}
                    </motion.div>

                    {/* Gmail Connection Prompt */}
                    {!isGmailConnected && candidate.email && (
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg"
                      >
                        <p className="text-sm text-blue-800 mb-2">
                          Connect Gmail to send emails directly from
                          RecruiterRadar
                        </p>
                        <GmailAuthButton />
                      </motion.div>
                    )}
                  </TabsContent>
                </Tabs>
              </motion.div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Gmail Connection Modal */}
      {candidate && jobFormData && (
        <GmailConnectionModal
          isOpen={showGmailConnectionModal}
          onClose={() => setShowGmailConnectionModal(false)}
          onSuccess={handleGmailConnectionSuccess}
          onCancel={handleGmailConnectionCancel}
          candidate={candidate}
          jobTitle={jobFormData.jobTitle}
        />
      )}
    </OutreachModalContainer>
  );
}
