import { useState } from "react";
import { motion } from "framer-motion";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Badge } from "@/components/ui/badge";
import { Briefcase, Building2, FileText, Sparkles } from "lucide-react";

interface OutreachFormProps {
  onSubmit: (data: {
    jobTitle: string;
    jobDescription: string;
    tone: string;
    companyContext: string;
    additionalInstructions: string;
  }) => void;
  isGenerating: boolean;
  rateLimitCooldown?: number;
}

export function OutreachForm({
  onSubmit,
  isGenerating,
  rateLimitCooldown = 0,
}: OutreachFormProps) {
  const [jobTitle, setJobTitle] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [tone, setTone] = useState("professional");
  const [companyContext, setCompanyContext] = useState("");
  const [additionalInstructions, setAdditionalInstructions] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      jobTitle,
      jobDescription,
      tone,
      companyContext,
      additionalInstructions,
    });
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: (i: number) => ({
      opacity: 1,
      y: 0,
      transition: { delay: i * 0.1 },
    }),
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Job Title */}
      <motion.div
        custom={0}
        variants={itemVariants}
        initial="hidden"
        animate="visible"
      >
        <Label className="flex items-center gap-2 mb-2">
          <Briefcase className="h-4 w-4" />
          Job Role Title *
        </Label>
        <Input
          value={jobTitle}
          onChange={(e) => setJobTitle(e.target.value)}
          placeholder="e.g., Senior React Developer"
          required
          className="transition-all focus:scale-[1.02]"
        />
      </motion.div>

      {/* Job Description */}
      <motion.div
        custom={1}
        variants={itemVariants}
        initial="hidden"
        animate="visible"
      >
        <Label className="flex items-center gap-2 mb-2">
          <FileText className="h-4 w-4" />
          Job Description
        </Label>
        <Textarea
          value={jobDescription}
          onChange={(e) => setJobDescription(e.target.value)}
          placeholder="Describe the role, responsibilities, and ideal candidate..."
          rows={4}
          className="transition-all focus:scale-[1.01]"
        />
      </motion.div>

      {/* Tone Selection */}
      <motion.div
        custom={2}
        variants={itemVariants}
        initial="hidden"
        animate="visible"
      >
        <Label className="flex items-center gap-2 mb-2">
          <Sparkles className="h-4 w-4" />
          Message Tone
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger>
                <Badge variant="secondary" className="ml-2">
                  Variations Coming Soon!
                </Badge>
              </TooltipTrigger>
              <TooltipContent>
                <p>
                  Multiple tone variations will be available in the next
                  release!
                </p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </Label>
        <RadioGroup value={tone} onValueChange={setTone}>
          <div className="flex gap-4">
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="professional" id="professional" />
              <Label htmlFor="professional">Professional</Label>
            </div>
            <div className="flex items-center space-x-2 opacity-50">
              <RadioGroupItem value="casual" id="casual" disabled />
              <Label htmlFor="casual">Casual</Label>
            </div>
            <div className="flex items-center space-x-2 opacity-50">
              <RadioGroupItem value="enthusiastic" id="enthusiastic" disabled />
              <Label htmlFor="enthusiastic">Enthusiastic</Label>
            </div>
          </div>
        </RadioGroup>
      </motion.div>

      {/* Company Context */}
      <motion.div
        custom={3}
        variants={itemVariants}
        initial="hidden"
        animate="visible"
      >
        <Label className="flex items-center gap-2 mb-2">
          <Building2 className="h-4 w-4" />
          Company Context
        </Label>
        <Textarea
          value={companyContext}
          onChange={(e) => setCompanyContext(e.target.value)}
          placeholder="Tell us about your company culture, mission, perks..."
          rows={3}
          className="transition-all focus:scale-[1.01]"
        />
      </motion.div>

      {/* Submit Button */}
      <motion.div
        custom={4}
        variants={itemVariants}
        initial="hidden"
        animate="visible"
      >
        <Button
          type="submit"
          disabled={isGenerating || !jobTitle || rateLimitCooldown > 0}
          className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 disabled:opacity-50"
        >
          {isGenerating ? (
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
            >
              <Sparkles className="h-4 w-4 mr-2" />
            </motion.div>
          ) : (
            <Sparkles className="h-4 w-4 mr-2" />
          )}
          {rateLimitCooldown > 0
            ? `Rate limited (${rateLimitCooldown}s)`
            : isGenerating
            ? "Generating AI Message..."
            : "Generate AI Outreach"}
        </Button>
      </motion.div>
    </form>
  );
}
