import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Progress } from "@/components/ui/progress";
import {
  Mail,
  MapPin,
  Briefcase,
  Github,
  Linkedin,
  Zap,
  Calendar,
  MessageSquare,
  GitCompare,
  Star,
  Download,
  Share2,
  GraduationCap,
  Phone,
  Globe,
  Clock,
  Award,
  Users,
  Target,
  TrendingUp,
  AlertCircle,
  User,
} from "lucide-react";
import { useEffect, useState } from "react";
import { apiService } from "@/services/apiService";
import { Loader2, Sparkles, CheckCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

interface CandidateBasic {
  id: string;
  name: string;
  professional_summary?: string;
  skills: string[];
  experience_years: number;
  email?: string;
  location?: string;
  github_url?: string;
  linkedin_url?: string;
  raw_resume_text?: string;
  visa_status?: string;
}

interface Insights {
  fit_score: number;
  strengths: string[];
  interview_questions: string[];
}

interface WorkExperience {
  company: string;
  position: string;
  duration: string;
  description: string;
}

interface Education {
  institution: string;
  degree: string;
  year: string;
}

// Enhanced parsing functions that work with the actual data structure
function extractWorkExperience(rawText: string): WorkExperience[] {
  if (!rawText) return [];

  const experiences: WorkExperience[] = [];
  const experienceMatch = rawText.match(
    /EXPERIENCE\s*[-\s]*\n([\s\S]*?)(?=\n(?:SKILLS|EDUCATION|CERTIFICATIONS|$))/i
  );

  if (!experienceMatch) return [];

  const experienceText = experienceMatch[1];
  const jobBlocks = experienceText.split(/\n(?=[A-Z][a-zA-Z\s]+\s*\|)/);

  for (const block of jobBlocks) {
    if (block.trim().length < 20) continue;

    const lines = block
      .trim()
      .split("\n")
      .filter((line) => line.trim());
    if (lines.length < 2) continue;

    const headerLine = lines[0];
    const positionMatch = headerLine.match(
      /^([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(.+)$/
    );

    if (positionMatch) {
      const [, position, company, duration] = positionMatch;
      const description =
        lines.slice(1).join(" ").substring(0, 200) +
        (lines.slice(1).join(" ").length > 200 ? "..." : "");

      experiences.push({
        position: position.trim(),
        company: company.trim(),
        duration: duration.trim(),
        description: description.replace(/^[•\-\*]\s*/, "").trim(),
      });
    }
  }

  return experiences.slice(0, 4); // Limit to 4 most recent
}

function extractEducation(rawText: string): Education[] {
  if (!rawText) return [];

  const educationEntries: Education[] = [];
  const educationMatch = rawText.match(
    /EDUCATION\s*[-\s]*\n([\s\S]*?)(?=\n[A-Z]{2,}|$)/i
  );

  if (!educationMatch) return [];

  const educationText = educationMatch[1];
  const entries = educationText.split(/\n(?=[A-Z])/);

  for (const entry of entries) {
    if (entry.trim().length < 10) continue;

    const lines = entry
      .trim()
      .split("\n")
      .filter((line) => line.trim());
    if (lines.length < 2) continue;

    const degree = lines[0].trim();
    const institutionLine = lines[1];
    const yearMatch = institutionLine.match(/(\d{4})/);
    const institution = institutionLine.replace(/\s*\|\s*\d{4}.*$/, "").trim();

    educationEntries.push({
      degree,
      institution,
      year: yearMatch ? yearMatch[1] : "Year not specified",
    });
  }

  return educationEntries.slice(0, 3);
}

function extractProfessionalSummary(
  rawText: string,
  candidateName: string
): string {
  if (!rawText) return "";

  // Look for summary section
  const summaryMatch = rawText.match(
    /(?:SUMMARY|OBJECTIVE|ABOUT)[\s\-]*\n([\s\S]*?)(?=\n[A-Z]{2,})/i
  );
  if (summaryMatch && summaryMatch[1].trim().length > 20) {
    return summaryMatch[1].trim();
  }

  // Extract from first few lines after name
  const lines = rawText.split("\n").filter((line) => line.trim());
  const nameIndex = lines.findIndex((line) =>
    line.toUpperCase().includes(candidateName.toUpperCase().split(" ")[0])
  );

  if (nameIndex >= 0 && nameIndex < lines.length - 3) {
    // Skip contact info lines and get descriptive content
    for (
      let i = nameIndex + 1;
      i < Math.min(nameIndex + 5, lines.length);
      i++
    ) {
      const line = lines[i];
      if (
        line.length > 40 &&
        !line.includes("@") &&
        !line.includes("linkedin") &&
        !line.includes("github") &&
        !line.match(/\d{3}[-\.\s]\d{3}[-\.\s]\d{4}/)
      ) {
        return line.trim();
      }
    }
  }

  return "";
}

// Enhanced circular progress with better styling and context
const CircularProgress = ({
  value,
  label = "Fit Score",
  size = 120,
  className = "",
}: {
  value: number;
  label?: string;
  size?: number;
  className?: string;
}) => {
  const radius = (size - 8) / 2;
  const circumference = radius * 2 * Math.PI;
  const strokeDasharray = circumference;
  const strokeDashoffset = circumference - (value / 100) * circumference;

  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-green-500";
    if (score >= 60) return "text-yellow-500";
    if (score >= 40) return "text-orange-500";
    return "text-red-500";
  };

  const getScoreRing = (score: number) => {
    if (score >= 80) return "stroke-green-500";
    if (score >= 60) return "stroke-yellow-500";
    if (score >= 40) return "stroke-orange-500";
    return "stroke-red-500";
  };

  return (
    <div className={cn("flex flex-col items-center", className)}>
      <div className="relative">
        <svg width={size} height={size} className="transform -rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth="8"
            fill="transparent"
            className="text-muted-foreground/20"
          />
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth="8"
            fill="transparent"
            strokeDasharray={strokeDasharray}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className={getScoreRing(value)}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset }}
            transition={{ duration: 1, ease: "easeOut" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={cn("text-2xl font-bold", getScoreColor(value))}>
            {value}%
          </span>
        </div>
      </div>
      <p className="text-sm font-medium mt-2 text-center">{label}</p>
      <p className="text-xs text-muted-foreground text-center">
        {value >= 80
          ? "Excellent Match"
          : value >= 60
          ? "Good Match"
          : value >= 40
          ? "Potential Match"
          : "Limited Match"}
      </p>
    </div>
  );
};

const SkillsVisualization = ({ skills }: { skills: string[] }) => (
  <div className="space-y-3">
    <h4 className="font-semibold text-sm">Key Skills</h4>
    <div className="flex flex-wrap gap-2">
      {skills.slice(0, 12).map((skill, index) => (
        <motion.div
          key={skill}
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: index * 0.05 }}
        >
          <Badge
            variant="secondary"
            className="text-xs bg-blue-500/20 text-blue-300 hover:bg-blue-500/30 border-blue-500/30"
          >
            {skill}
          </Badge>
        </motion.div>
      ))}
      {skills.length > 12 && (
        <Badge variant="outline" className="text-xs">
          +{skills.length - 12} more
        </Badge>
      )}
    </div>
  </div>
);

const LoadingState = () => (
  <div className="flex items-center justify-center h-32">
    <div className="flex items-center gap-3">
      <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
      <span className="text-sm text-muted-foreground">
        Analyzing candidate profile...
      </span>
    </div>
  </div>
);

const ErrorState = ({ onRetry }: { onRetry: () => void }) => (
  <div className="flex flex-col items-center justify-center h-32 space-y-3">
    <AlertCircle className="w-8 h-8 text-red-500" />
    <div className="text-center">
      <p className="text-sm font-medium">Unable to load insights</p>
      <p className="text-xs text-muted-foreground">
        The AI analysis service is currently unavailable
      </p>
    </div>
    <Button variant="outline" size="sm" onClick={onRetry}>
      Try Again
    </Button>
  </div>
);

export function ViewProfileModal({
  open,
  onClose,
  candidate,
}: {
  open: boolean;
  onClose: () => void;
  candidate: CandidateBasic;
}) {
  const [insights, setInsights] = useState<Insights | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [fullCandidate, setFullCandidate] = useState<CandidateBasic | null>(
    null
  );

  const fetchCandidateData = async () => {
    if (!open) return;

    setLoading(true);
    setError(false);

    try {
      // Fetch complete candidate details first
      console.log("🔍 Fetching complete candidate details for:", candidate.id);
      const candidateDetails = await apiService.getCandidateDetails(
        candidate.id
      );
      setFullCandidate(candidateDetails);
      console.log("✅ Loaded full candidate details:", candidateDetails);

      // Then fetch insights
      console.log("🧠 Fetching AI insights for:", candidate.id);
      const insightsData = await apiService.getCandidateInsights(candidate.id);
      setInsights(insightsData);
      console.log("✅ Loaded AI insights:", insightsData);
    } catch (error) {
      console.error("❌ Failed to fetch candidate data:", error);
      setError(true);

      // Fallback: use basic candidate data and generate mock insights
      setFullCandidate(candidate);
      setInsights({
        fit_score: Math.floor(Math.random() * 30) + 65, // 65-95% range for better UX
        strengths: [
          `Strong expertise in ${
            candidate.skills[0] || "software development"
          }`,
          `${candidate.experience_years}+ years of professional experience`,
          `Proficient in ${candidate.skills.slice(0, 3).join(", ")}`,
        ],
        interview_questions: [
          `Can you describe a project where you used ${
            candidate.skills[0] || "your primary skill"
          }?`,
          `How do you stay updated with the latest ${
            candidate.skills[1] || "technology"
          } trends?`,
          `Tell me about a challenging technical problem you solved recently.`,
          `How do you approach code reviews and team collaboration?`,
          `What's your experience with agile development methodologies?`,
        ],
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      fetchCandidateData();
    } else {
      setInsights(null);
      setFullCandidate(null);
      setError(false);
    }
  }, [open, candidate.id]);

  // Keyboard shortcuts
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (!open) return;
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  // Use fullCandidate data if available, otherwise fall back to basic candidate
  const displayCandidate = fullCandidate || candidate;

  // Parse resume data using the complete candidate information
  const workExperience = extractWorkExperience(
    displayCandidate.raw_resume_text || ""
  );
  const education = extractEducation(displayCandidate.raw_resume_text || "");
  const professionalSummary = extractProfessionalSummary(
    displayCandidate.raw_resume_text || "",
    displayCandidate.name
  );

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-[95vw] max-h-[95vh] overflow-hidden p-0">
        <DialogTitle className="sr-only">
          {displayCandidate.name} profile overview
        </DialogTitle>

        {error ? (
          <ErrorState onRetry={fetchCandidateData} />
        ) : loading ? (
          <LoadingState />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 h-[95vh]">
            {/* Left Panel - Candidate Profile */}
            <div className="lg:col-span-2 border-r border-border overflow-y-auto">
              <div className="p-6 space-y-6">
                {/* Header Section */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-start gap-4 pb-6 border-b border-border"
                >
                  <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl font-bold shadow-lg">
                    {displayCandidate.name
                      .split(" ")
                      .map((n) => n[0])
                      .join("")
                      .toUpperCase()}
                  </div>
                  <div className="flex-1">
                    <h2 className="text-3xl font-bold text-foreground mb-1">
                      {displayCandidate.name}
                    </h2>
                    <div className="flex items-center gap-2 mb-3">
                      <Clock className="w-4 h-4 text-muted-foreground" />
                      <span className="text-muted-foreground">
                        {displayCandidate.experience_years} years of experience
                      </span>
                      {displayCandidate.visa_status && (
                        <>
                          <Separator orientation="vertical" className="h-4" />
                          <Globe className="w-4 h-4 text-muted-foreground" />
                          <span className="text-muted-foreground">
                            {displayCandidate.visa_status}
                          </span>
                        </>
                      )}
                    </div>

                    {/* Contact Information */}
                    <div className="space-y-2 mb-4">
                      <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                        {displayCandidate.email && (
                          <a
                            href={`mailto:${displayCandidate.email}`}
                            className="flex items-center gap-1 hover:text-primary transition-colors"
                          >
                            <Mail className="w-4 h-4" />
                            {displayCandidate.email}
                          </a>
                        )}
                        {displayCandidate.location && (
                          <span className="flex items-center gap-1">
                            <MapPin className="w-4 h-4" />
                            {displayCandidate.location}
                          </span>
                        )}
                      </div>

                      {/* Additional extracted contact info */}
                      {displayCandidate.raw_resume_text &&
                        (() => {
                          const phoneMatch =
                            displayCandidate.raw_resume_text?.match(
                              /(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})/
                            );
                          return (
                            phoneMatch && (
                              <div className="flex items-center gap-1 text-sm text-muted-foreground">
                                <Phone className="w-4 h-4" />
                                <a
                                  href={`tel:${phoneMatch[1]}`}
                                  className="hover:text-primary transition-colors"
                                >
                                  {phoneMatch[1]}
                                </a>
                              </div>
                            )
                          );
                        })()}
                    </div>

                    {/* Social Links */}
                    <div className="flex gap-2">
                      {displayCandidate.linkedin_url && (
                        <Button variant="outline" size="sm" asChild>
                          <a
                            href={displayCandidate.linkedin_url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <Linkedin className="w-4 h-4 mr-1" />
                            LinkedIn
                          </a>
                        </Button>
                      )}
                      {displayCandidate.github_url && (
                        <Button variant="outline" size="sm" asChild>
                          <a
                            href={displayCandidate.github_url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <Github className="w-4 h-4 mr-1" />
                            GitHub
                          </a>
                        </Button>
                      )}
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => window.print()}
                    >
                      <Download className="w-4 h-4 mr-1" />
                      Export
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        navigator.clipboard.writeText(
                          `${window.location.origin}/candidate/${displayCandidate.id}`
                        );
                      }}
                    >
                      <Share2 className="w-4 h-4 mr-1" />
                      Share
                    </Button>
                  </div>
                </motion.div>

                {/* Quick Stats */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.05 }}
                  className="grid grid-cols-2 md:grid-cols-4 gap-4"
                >
                  <Card className="p-3 text-center">
                    <div className="text-lg font-bold text-blue-400">
                      {displayCandidate.experience_years}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Years Experience
                    </div>
                  </Card>
                  <Card className="p-3 text-center">
                    <div className="text-lg font-bold text-green-400">
                      {displayCandidate.skills.length}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Skills Listed
                    </div>
                  </Card>
                  <Card className="p-3 text-center">
                    <div className="text-lg font-bold text-purple-400">
                      {workExperience.length ||
                        (displayCandidate.raw_resume_text ? "Multiple" : "N/A")}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Positions
                    </div>
                  </Card>
                  <Card className="p-3 text-center">
                    <div className="text-lg font-bold text-orange-400">
                      {displayCandidate.visa_status || "Not Specified"}
                    </div>
                    <div className="text-xs text-muted-foreground">Status</div>
                  </Card>
                </motion.div>

                {/* Professional Summary */}
                {professionalSummary && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                  >
                    <h3 className="text-xl font-semibold mb-3 flex items-center gap-2">
                      <User className="w-5 h-5 text-blue-500" />
                      Professional Summary
                    </h3>
                    <Card className="p-4 bg-gradient-to-r from-blue-500/10 to-purple-500/10 border-blue-500/20 backdrop-blur-sm">
                      <p className="text-sm text-foreground/90 leading-relaxed">
                        {professionalSummary}
                      </p>
                    </Card>
                  </motion.div>
                )}

                {/* Skills Section */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                >
                  <h3 className="text-xl font-semibold mb-3 flex items-center gap-2">
                    <Zap className="w-5 h-5 text-yellow-500" />
                    Technical Skills
                  </h3>
                  <SkillsVisualization skills={displayCandidate.skills} />
                </motion.div>

                {/* Work Experience */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                >
                  <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
                    <Briefcase className="w-5 h-5 text-green-500" />
                    Work Experience
                  </h3>
                  {workExperience.length > 0 ? (
                    <div className="space-y-4">
                      {workExperience.map((exp, idx) => (
                        <motion.div
                          key={idx}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: 0.4 + idx * 0.1 }}
                          className="relative"
                        >
                          <Card className="p-4 hover:shadow-md transition-shadow">
                            <div className="flex items-start justify-between mb-2">
                              <div>
                                <h4 className="font-semibold text-base text-foreground">
                                  {exp.position}
                                </h4>
                                <p className="text-sm font-medium text-blue-600">
                                  {exp.company}
                                </p>
                              </div>
                              <Badge variant="outline" className="text-xs">
                                {exp.duration}
                              </Badge>
                            </div>
                            <p className="text-sm text-muted-foreground leading-relaxed">
                              {exp.description}
                            </p>
                          </Card>
                        </motion.div>
                      ))}
                    </div>
                  ) : (
                    <Card className="p-4">
                      <div className="space-y-3">
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 rounded-full bg-green-500"></div>
                          <span className="text-sm text-foreground/90">
                            {displayCandidate.experience_years} years of
                            professional experience
                          </span>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          Detailed work history available in resume text
                        </div>
                        {/* Show a preview of raw resume if available */}
                        {displayCandidate.raw_resume_text && (
                          <details className="text-xs">
                            <summary className="cursor-pointer text-blue-400 hover:text-blue-300">
                              View raw resume extract
                            </summary>
                            <div className="mt-2 p-3 bg-secondary/20 rounded border border-border/50 max-h-32 overflow-y-auto">
                              <pre className="whitespace-pre-wrap text-muted-foreground text-xs leading-relaxed">
                                {displayCandidate.raw_resume_text.substring(
                                  0,
                                  300
                                )}
                                {displayCandidate.raw_resume_text.length >
                                  300 && "..."}
                              </pre>
                            </div>
                          </details>
                        )}
                      </div>
                    </Card>
                  )}
                </motion.div>

                {/* Education */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5 }}
                >
                  <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
                    <GraduationCap className="w-5 h-5 text-purple-500" />
                    Education
                  </h3>
                  {education.length > 0 ? (
                    <div className="space-y-3">
                      {education.map((edu, idx) => (
                        <motion.div
                          key={idx}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: 0.6 + idx * 0.1 }}
                        >
                          <Card className="p-4">
                            <h4 className="font-semibold text-sm text-foreground">
                              {edu.degree}
                            </h4>
                            <p className="text-sm text-blue-600">
                              {edu.institution}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {edu.year}
                            </p>
                          </Card>
                        </motion.div>
                      ))}
                    </div>
                  ) : (
                    <Card className="p-4">
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                          <span className="text-sm text-foreground/90">
                            Education details available in resume
                          </span>
                        </div>
                        {displayCandidate.raw_resume_text &&
                          (() => {
                            const educationMatch =
                              displayCandidate.raw_resume_text?.match(
                                /(?:EDUCATION|ACADEMIC|UNIVERSITY|COLLEGE|DEGREE)([\s\S]*?)(?=\n(?:EXPERIENCE|SKILLS|CERTIFICATIONS|$))/i
                              );
                            return (
                              educationMatch && (
                                <details className="text-xs">
                                  <summary className="cursor-pointer text-purple-400 hover:text-purple-300">
                                    View education section
                                  </summary>
                                  <div className="mt-2 p-3 bg-secondary/20 rounded border border-border/50">
                                    <pre className="whitespace-pre-wrap text-muted-foreground text-xs leading-relaxed">
                                      {educationMatch[1]
                                        .trim()
                                        .substring(0, 200)}
                                      {educationMatch[1].trim().length > 200 &&
                                        "..."}
                                    </pre>
                                  </div>
                                </details>
                              )
                            );
                          })()}
                      </div>
                    </Card>
                  )}
                </motion.div>
              </div>
            </div>

            {/* Right Panel - AI Insights */}
            <div className="bg-gradient-to-b from-card via-card to-secondary/50 border-l border-border">
              <div className="p-6 border-b border-border/50">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-purple-400" />
                  AI Insights
                </h3>
                <p className="text-xs text-muted-foreground/80 mt-1">
                  For Software Engineer Role
                </p>
              </div>

              <ScrollArea className="h-[calc(95vh-80px)]">
                <div className="p-6 space-y-6">
                  <AnimatePresence mode="wait">
                    {loading ? (
                      <LoadingState />
                    ) : error ? (
                      <ErrorState onRetry={fetchCandidateData} />
                    ) : insights ? (
                      <>
                        {/* Fit Score */}
                        <motion.div
                          initial={{ opacity: 0, scale: 0.9 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={{ delay: 0.2 }}
                          className="text-center"
                        >
                          <CircularProgress
                            value={insights.fit_score}
                            label="Match Score"
                            className="mb-4"
                          />
                          <p className="text-xs text-muted-foreground">
                            Based on skills, experience, and role requirements
                          </p>
                        </motion.div>

                        {/* Strengths */}
                        <motion.div
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: 0.3 }}
                        >
                          <h4 className="font-semibold text-sm mb-3 flex items-center gap-2">
                            <CheckCircle className="w-4 h-4 text-green-500" />
                            Key Strengths
                          </h4>
                          <div className="space-y-2">
                            {insights.strengths.map((strength, idx) => (
                              <motion.div
                                key={idx}
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: 0.4 + idx * 0.1 }}
                                className="flex items-start gap-2 text-xs"
                              >
                                <div className="w-1.5 h-1.5 rounded-full bg-green-500 mt-2 flex-shrink-0" />
                                <span className="text-muted-foreground leading-relaxed">
                                  {strength}
                                </span>
                              </motion.div>
                            ))}
                          </div>
                        </motion.div>

                        {/* Interview Questions */}
                        <motion.div
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: 0.5 }}
                        >
                          <h4 className="font-semibold text-sm mb-3 flex items-center gap-2">
                            <MessageSquare className="w-4 h-4 text-blue-500" />
                            Interview Questions
                          </h4>
                          <div className="space-y-3">
                            {insights.interview_questions.map(
                              (question, idx) => (
                                <motion.div
                                  key={idx}
                                  initial={{ opacity: 0, y: 10 }}
                                  animate={{ opacity: 1, y: 0 }}
                                  transition={{ delay: 0.6 + idx * 0.1 }}
                                  className="p-3 bg-secondary/30 border border-border/50 rounded-lg hover:bg-secondary/40 transition-all duration-200 hover:border-border"
                                >
                                  <p className="text-xs text-foreground/90 leading-relaxed">
                                    {question}
                                  </p>
                                </motion.div>
                              )
                            )}
                          </div>
                        </motion.div>

                        {/* Action Buttons */}
                        <motion.div
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: 0.8 }}
                          className="space-y-3 pt-4 border-t border-border"
                        >
                          <Button className="w-full" size="sm">
                            <Users className="w-4 h-4 mr-2" />
                            Schedule Interview
                          </Button>
                          <Button
                            variant="outline"
                            className="w-full"
                            size="sm"
                          >
                            <MessageSquare className="w-4 h-4 mr-2" />
                            Generate Outreach
                          </Button>
                          <Button
                            variant="outline"
                            className="w-full"
                            size="sm"
                          >
                            <GitCompare className="w-4 h-4 mr-2" />
                            Compare Candidates
                          </Button>
                        </motion.div>
                      </>
                    ) : null}
                  </AnimatePresence>
                </div>
              </ScrollArea>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
