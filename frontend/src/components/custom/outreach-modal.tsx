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
} from "lucide-react";
import confetti from "canvas-confetti";

import { OutreachModalContainer } from "./outreach-modal-container";
import { OutreachForm } from "./outreach-form";
import { GenerationProgress } from "./generation-progress";
import { api } from "@/lib/api";
import type { OutreachResponse } from "@/lib/types";
import type { FrontendCandidate } from "@/services/types";

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
  const [lastGenerationTime, setLastGenerationTime] = useState<number>(0);
  const [rateLimitCooldown, setRateLimitCooldown] = useState<number>(0);
  const { toast } = useToast();

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setIsGenerating(false);
      setGenerationProgress(0);
      setGenerationStage("");
      setGeneratedMessage(null);
      setCopied(false);
    }
  }, [isOpen]);

  // 🛡️ Rate limiting countdown
  useEffect(() => {
    if (rateLimitCooldown > 0) {
      const timer = setTimeout(() => {
        setRateLimitCooldown((prev) => prev - 1);
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [rateLimitCooldown]);

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

  const handleGenerateOutreach = async (formData: {
    jobTitle: string;
    jobDescription: string;
    tone: string;
    companyContext: string;
    additionalInstructions: string;
  }) => {
    if (!candidate) return;

    // 🛡️ Rate limiting - prevent spam (30 seconds between generations)
    const now = Date.now();
    const timeSinceLastGeneration = now - lastGenerationTime;
    const cooldownPeriod = 30000; // 30 seconds

    if (timeSinceLastGeneration < cooldownPeriod) {
      const remainingSeconds = Math.ceil(
        (cooldownPeriod - timeSinceLastGeneration) / 1000
      );
      setRateLimitCooldown(remainingSeconds);

      toast({
        title: "⏳ Please wait",
        description: `Rate limit active. Try again in ${remainingSeconds} seconds to prevent token burn.`,
        variant: "destructive",
      });
      return;
    }

    setLastGenerationTime(now);
    setIsGenerating(true);
    setGenerationProgress(10);

    try {
      const response = await api.generateOutreachDraft(candidate.id, {
        job_role_title: formData.jobTitle,
        job_role_description: formData.jobDescription,
        tone: formData.tone,
        company_context: formData.companyContext,
        additional_instructions: formData.additionalInstructions,
      });

      setGenerationProgress(100);
      setGenerationStage("Message ready!");

      // Delay to show 100% progress
      setTimeout(() => {
        setGeneratedMessage(response);
        setIsGenerating(false);

        // Trigger celebration
        confetti({
          particleCount: 100,
          spread: 70,
          origin: { y: 0.6 },
        });

        // Update session metrics
        if (onSuccess) onSuccess();
      }, 500);
    } catch (error) {
      console.error("Failed to generate outreach:", error);
      toast({
        title: "Generation Failed",
        description:
          error instanceof Error ? error.message : "Please try again",
        variant: "destructive",
      });
      setIsGenerating(false);
      setGenerationProgress(0);
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

  if (!candidate) return null;

  return (
    <OutreachModalContainer isOpen={isOpen}>
      <Dialog open={isOpen} onOpenChange={onClose}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden p-0">
          {/* Header */}
          <DialogHeader className="px-6 pt-6">
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
              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
                className="rounded-full"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </DialogHeader>

          <Separator className="my-6" />

          {/* Content */}
          <div className="px-6 pb-6 max-h-[calc(90vh-120px)] overflow-y-auto">
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
                    rateLimitCooldown={rateLimitCooldown}
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
                    <div className="grid grid-cols-4 gap-4">
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: 0.1 }}
                        className="bg-gray-50 p-3 rounded-lg text-center"
                      >
                        <Clock className="h-4 w-4 mx-auto mb-1 text-gray-600" />
                        <p className="text-sm font-semibold">
                          {(generatedMessage.generation_time_ms / 1000).toFixed(
                            1
                          )}
                          s
                        </p>
                        <p className="text-xs text-gray-500">Generation Time</p>
                      </motion.div>

                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: 0.2 }}
                        className="bg-gray-50 p-3 rounded-lg text-center"
                      >
                        <FileText className="h-4 w-4 mx-auto mb-1 text-gray-600" />
                        <p className="text-sm font-semibold">
                          {generatedMessage.word_count}
                        </p>
                        <p className="text-xs text-gray-500">Words</p>
                      </motion.div>

                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: 0.3 }}
                        className="bg-gray-50 p-3 rounded-lg text-center"
                      >
                        <TrendingUp className="h-4 w-4 mx-auto mb-1 text-gray-600" />
                        <p className="text-sm font-semibold">95%</p>
                        <p className="text-xs text-gray-500">Personalization</p>
                      </motion.div>

                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: 0.4 }}
                        className="bg-gray-50 p-3 rounded-lg text-center"
                      >
                        <Sparkles className="h-4 w-4 mx-auto mb-1 text-gray-600" />
                        <p className="text-sm font-semibold capitalize">
                          {generatedMessage.tone_used}
                        </p>
                        <p className="text-xs text-gray-500">Tone</p>
                      </motion.div>
                    </div>

                    {/* Message */}
                    <div className="relative">
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.5 }}
                        className="bg-gray-50 p-6 rounded-lg"
                      >
                        <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">
                          {generatedMessage.draft_message}
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
                        className="space-y-2"
                      >
                        <p className="text-sm font-medium text-gray-700">
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
                                <Badge variant="secondary">
                                  {typeof element === "string"
                                    ? element
                                    : element.value}
                                </Badge>
                              </motion.div>
                            )
                          )}
                        </div>
                      </motion.div>
                    )}

                    {/* Actions */}
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
                        }}
                        variant="outline"
                        className="flex-1"
                      >
                        Generate Another
                      </Button>
                      <Button
                        onClick={onClose}
                        className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600"
                      >
                        Done
                      </Button>
                    </motion.div>
                  </TabsContent>
                </Tabs>
              </motion.div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </OutreachModalContainer>
  );
}
