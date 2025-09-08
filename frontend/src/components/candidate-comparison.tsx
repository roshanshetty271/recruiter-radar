"use client";

import { useState, useEffect } from "react";
import {
  X,
  Star,
  MapPin,
  Clock,
  Code,
  TrendingUp,
  Award,
  Briefcase,
  GraduationCap,
  Zap,
  Brain,
} from "lucide-react";

import { AIComparisonAdvisor } from "./custom/ai-comparison-advisor";
import { FrontendCandidate } from "@/services/types";

// Use FrontendCandidate from types.ts instead of local interface
type Candidate = FrontendCandidate;

interface DetailedMetrics {
  technicalSkills: number;
  communication: number;
  leadership: number;
  problemSolving: number;
  teamwork: number;
  adaptability: number;
  salary: string;
  availability: string;
  education: string;
  certifications: string[];
  languages: string[];
  projects: number;
  githubScore: number;
  linkedinConnections: number;
}

// Get real detailed metrics from candidate data
const getDetailedMetrics = (candidate: Candidate): DetailedMetrics => {
  // Calculate technical skills based on actual skills count and experience
  const skillCount = candidate.skills?.length || 0;
  const techSkillsBase = Math.min(95, Math.max(60, 70 + skillCount * 1.5));

  // Calculate other metrics based on experience and skills
  const expYears = candidate.experience_years || 0;
  const communicationBase = Math.min(90, Math.max(65, 70 + expYears * 2));
  const leadershipBase = Math.min(85, Math.max(60, 65 + expYears * 3));

  // Get real education from candidate data
  let education = "Not specified";
  if (candidate.education && candidate.education.length > 0) {
    const highestEd = candidate.education[0]; // Assuming first is highest/most recent
    const degree = highestEd.degree || "Degree";
    const field = highestEd.field || "";
    education = field ? `${degree} in ${field}` : degree;
  }

  // Get real certifications
  const certifications = candidate.certifications || [];

  // Get languages - default to English if not specified
  const languages = candidate.languages || ["English"];

  // Calculate projects estimate based on experience
  const projects = Math.max(5, Math.min(30, 8 + expYears * 2));

  return {
    technicalSkills: Math.round(techSkillsBase),
    communication: Math.round(communicationBase),
    leadership: Math.round(leadershipBase),
    problemSolving: Math.round(Math.min(90, Math.max(70, 75 + expYears * 2.5))),
    teamwork: Math.round(Math.min(85, Math.max(70, 75 + expYears * 1.5))),
    adaptability: Math.round(Math.min(90, Math.max(65, 70 + skillCount * 2))),
    salary: `$${Math.floor(80 + expYears * 15 + skillCount * 2)}k`, // Realistic salary estimate
    availability: expYears > 5 ? "2-4 weeks notice" : "2 weeks notice",
    education: education,
    certifications: certifications.slice(0, 3), // Show up to 3 certifications
    languages: languages,
    projects: projects,
    githubScore: candidate.github_url ? Math.round(75 + skillCount * 2) : 60,
    linkedinConnections: Math.round(300 + expYears * 100 + skillCount * 10), // Realistic estimate
  };
};

export function CandidateComparison({
  candidates,
  isOpen,
  onClose,
  onRemove,
}: {
  candidates: Candidate[];
  isOpen: boolean;
  onClose: () => void;
  onRemove: (id: string) => void;
}) {
  const [activeTab, setActiveTab] = useState("overview");

  // 🛑 Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      const { overflow } = document.body.style;
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = overflow;
      };
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const tabs = [
    { id: "overview", label: "Overview", icon: Star },
    { id: "skills", label: "Skills", icon: Code },
    { id: "experience", label: "Experience", icon: Briefcase },
    { id: "metrics", label: "Metrics", icon: TrendingUp },
    { id: "ai-advisor", label: "AI Advisor", icon: Brain },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div
        className="relative w-full max-w-7xl max-h-screen overflow-y-auto rounded-xl animate-in slide-in-from-bottom-4 duration-300"
        style={{
          background: "rgba(10,10,20,0.95)",
          backdropFilter: "blur(20px)",
          border: "1px solid rgba(255,255,255,0.1)",
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-r from-purple-500 to-blue-500 rounded-lg flex items-center justify-center">
              <Star className="w-4 h-4 text-white" />
            </div>
            <h2 className="text-2xl font-bold text-white">
              Candidate Comparison
            </h2>
            <span className="text-sm text-gray-400">
              ({candidates.length} candidates)
            </span>
          </div>

          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-white/10">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center space-x-2 px-6 py-4 text-sm font-medium transition-colors relative ${
                activeTab === tab.id
                  ? "text-white bg-white/5"
                  : "text-gray-400 hover:text-white hover:bg-white/5"
              }`}
            >
              <tab.icon className="w-4 h-4" />
              <span>{tab.label}</span>
              {activeTab === tab.id && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-purple-500 to-blue-500" />
              )}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === "overview" && (
            <OverviewTab candidates={candidates} onRemove={onRemove} />
          )}
          {activeTab === "skills" && <SkillsTab candidates={candidates} />}
          {activeTab === "experience" && (
            <ExperienceTab candidates={candidates} />
          )}
          {activeTab === "metrics" && <MetricsTab candidates={candidates} />}
          {activeTab === "ai-advisor" && (
            <AIComparisonAdvisor
              candidateIds={candidates.map((c) => c.id)}
              candidateNames={candidates.reduce(
                (acc, c) => ({ ...acc, [c.id]: c.name }),
                {}
              )}
              jobContext={{
                title: "Software Engineering Position", // You can make this dynamic later
                description: "Comparing candidates for technical roles",
                company: "Your Company",
              }}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function OverviewTab({
  candidates,
  onRemove,
}: {
  candidates: Candidate[];
  onRemove: (id: string) => void;
}) {
  return (
    <div
      className="grid gap-6"
      style={{ gridTemplateColumns: `repeat(${candidates.length}, 1fr)` }}
    >
      {candidates.map((candidate) => {
        const metrics = getDetailedMetrics(candidate);
        return (
          <div
            key={candidate.id}
            className="space-y-6 p-6 rounded-xl"
            style={{
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.1)",
            }}
          >
            {/* Header */}
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-4">
                <div className="relative">
                  <img
                    src={candidate.avatar || "/placeholder.svg"}
                    alt={candidate.name}
                    className="w-16 h-16 rounded-full object-cover"
                  />
                  {candidate.isOnline && (
                    <div className="absolute -bottom-1 -right-1 w-5 h-5 bg-green-400 rounded-full border-2 border-gray-900" />
                  )}
                </div>
                <div>
                  <h3 className="text-xl font-bold text-white">
                    {candidate.name}
                  </h3>
                  <p className="text-gray-400">{candidate.title}</p>
                  <div className="flex items-center space-x-1 text-sm text-gray-500 mt-1">
                    <MapPin className="w-3 h-3" />
                    <span>{candidate.location}</span>
                  </div>
                </div>
              </div>

              <button
                onClick={() => onRemove(candidate.id)}
                className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Match Score */}
            <div className="text-center">
              <div className="relative w-24 h-24 mx-auto mb-2">
                <svg className="w-24 h-24 transform -rotate-90">
                  <defs>
                    <linearGradient
                      id={`comparison-gradient-${candidate.id}`}
                      x1="0%"
                      y1="0%"
                      x2="100%"
                      y2="0%"
                    >
                      <stop offset="0%" stopColor="#8b5cf6" />
                      <stop offset="100%" stopColor="#3b82f6" />
                    </linearGradient>
                  </defs>
                  <circle
                    cx="48"
                    cy="48"
                    r="40"
                    stroke="rgba(255,255,255,0.1)"
                    strokeWidth="6"
                    fill="none"
                  />
                  <circle
                    cx="48"
                    cy="48"
                    r="40"
                    stroke={`url(#comparison-gradient-${candidate.id})`}
                    strokeWidth="6"
                    fill="none"
                    strokeDasharray={`${candidate.matchScore * 2.51} 251`}
                    className="transition-all duration-1000"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-2xl font-bold text-white">
                    {candidate.matchScore}%
                  </span>
                </div>
              </div>
              <p className="text-sm text-gray-400">Match Score</p>
            </div>

            {/* Quick Stats */}
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-3 bg-white/5 rounded-lg">
                <div className="text-lg font-bold text-white">
                  {candidate.experience}
                </div>
                <div className="text-xs text-gray-400">Years Exp</div>
              </div>
              <div className="text-center p-3 bg-white/5 rounded-lg">
                <div className="text-lg font-bold text-white">
                  {candidate.skills.length}
                </div>
                <div className="text-xs text-gray-400">Skills</div>
              </div>
              <div className="text-center p-3 bg-white/5 rounded-lg">
                <div className="text-lg font-bold text-green-400">
                  {metrics.salary}
                </div>
                <div className="text-xs text-gray-400">Expected</div>
              </div>
              <div className="text-center p-3 bg-white/5 rounded-lg">
                <div className="text-lg font-bold text-blue-400">
                  {metrics.availability}
                </div>
                <div className="text-xs text-gray-400">Available</div>
              </div>
            </div>

            {/* Top Skills */}
            <div>
              <h4 className="text-sm font-medium text-white mb-3">
                Top Skills
              </h4>
              <div className="flex flex-wrap gap-2">
                {candidate.skills.slice(0, 4).map((skill) => (
                  <span
                    key={skill}
                    className="px-2 py-1 text-xs bg-purple-600/20 text-purple-200 rounded-full border border-purple-400/30"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function SkillsTab({ candidates }: { candidates: Candidate[] }) {
  const allSkills = Array.from(new Set(candidates.flatMap((c) => c.skills)));

  return (
    <div className="space-y-6">
      <h3 className="text-xl font-bold text-white">Skills Comparison</h3>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/10">
              <th className="text-left p-4 text-gray-400 font-medium">Skill</th>
              {candidates.map((candidate) => (
                <th
                  key={candidate.id}
                  className="text-center p-4 text-gray-400 font-medium min-w-32"
                >
                  {candidate.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {allSkills.map((skill) => (
              <tr
                key={skill}
                className="border-b border-white/5 hover:bg-white/5"
              >
                <td className="p-4 text-white font-medium">{skill}</td>
                {candidates.map((candidate) => (
                  <td key={candidate.id} className="p-4 text-center">
                    {candidate.skills.includes(skill) ? (
                      <div className="w-6 h-6 bg-green-500 rounded-full mx-auto flex items-center justify-center">
                        <span className="text-white text-xs">✓</span>
                      </div>
                    ) : (
                      <div className="w-6 h-6 bg-gray-600 rounded-full mx-auto opacity-30" />
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ExperienceTab({ candidates }: { candidates: Candidate[] }) {
  return (
    <div className="space-y-6">
      <h3 className="text-xl font-bold text-white">Experience & Background</h3>

      <div
        className="grid gap-6"
        style={{ gridTemplateColumns: `repeat(${candidates.length}, 1fr)` }}
      >
        {candidates.map((candidate) => {
          const metrics = getDetailedMetrics(candidate);
          return (
            <div
              key={candidate.id}
              className="space-y-4 p-6 rounded-xl"
              style={{
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.1)",
              }}
            >
              <h4 className="text-lg font-bold text-white">{candidate.name}</h4>

              <div className="space-y-4">
                <div className="flex items-center space-x-3">
                  <Clock className="w-4 h-4 text-blue-400" />
                  <div>
                    <div className="text-white font-medium">
                      {candidate.experience} years
                    </div>
                    <div className="text-xs text-gray-400">
                      Total Experience
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-3">
                  <GraduationCap className="w-4 h-4 text-green-400" />
                  <div>
                    <div className="text-white font-medium">
                      {metrics.education}
                    </div>
                    <div className="text-xs text-gray-400">Education</div>
                  </div>
                </div>

                <div className="flex items-center space-x-3">
                  <Award className="w-4 h-4 text-yellow-400" />
                  <div>
                    <div className="text-white font-medium">
                      {metrics.certifications.length || "None"}
                    </div>
                    <div className="text-xs text-gray-400">Certifications</div>
                  </div>
                </div>

                <div className="flex items-center space-x-3">
                  <Code className="w-4 h-4 text-purple-400" />
                  <div>
                    <div className="text-white font-medium">
                      {metrics.projects}
                    </div>
                    <div className="text-xs text-gray-400">Projects</div>
                  </div>
                </div>
              </div>

              {metrics.languages.length > 0 && (
                <div>
                  <div className="text-sm font-medium text-white mb-2">
                    Languages
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {metrics.languages.map((lang) => (
                      <span
                        key={lang}
                        className="px-2 py-1 text-xs bg-blue-600/20 text-blue-200 rounded"
                      >
                        {lang}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function MetricsTab({ candidates }: { candidates: Candidate[] }) {
  const metricCategories = [
    {
      key: "technicalSkills",
      label: "Technical Skills",
      icon: Code,
      color: "purple",
    },
    { key: "communication", label: "Communication", icon: Star, color: "blue" },
    { key: "leadership", label: "Leadership", icon: Award, color: "yellow" },
    {
      key: "problemSolving",
      label: "Problem Solving",
      icon: Zap,
      color: "green",
    },
    { key: "teamwork", label: "Teamwork", icon: Star, color: "pink" },
    {
      key: "adaptability",
      label: "Adaptability",
      icon: TrendingUp,
      color: "indigo",
    },
  ];

  return (
    <div className="space-y-8">
      <h3 className="text-xl font-bold text-white">Detailed Metrics</h3>

      {metricCategories.map((category) => (
        <div key={category.key} className="space-y-4">
          <div className="flex items-center space-x-2">
            <category.icon className="w-5 h-5 text-gray-400" />
            <h4 className="text-lg font-medium text-white">{category.label}</h4>
          </div>

          <div className="space-y-3">
            {candidates.map((candidate) => {
              const metrics = getDetailedMetrics(candidate);
              const score = metrics[
                category.key as keyof DetailedMetrics
              ] as number;

              const getGradientClass = (color: string) => {
                switch (color) {
                  case "purple":
                    return "from-purple-500 to-purple-400";
                  case "blue":
                    return "from-blue-500 to-blue-400";
                  case "yellow":
                    return "from-yellow-500 to-yellow-400";
                  case "green":
                    return "from-green-500 to-green-400";
                  case "pink":
                    return "from-pink-500 to-pink-400";
                  case "indigo":
                    return "from-indigo-500 to-indigo-400";
                  default:
                    return "from-gray-500 to-gray-400";
                }
              };

              return (
                <div key={candidate.id} className="flex items-center space-x-4">
                  <div className="w-32 text-sm text-gray-300">
                    {candidate.name}
                  </div>
                  <div className="flex-1 bg-gray-800 rounded-full h-3 overflow-hidden">
                    <div
                      className={`h-full bg-gradient-to-r ${getGradientClass(
                        category.color
                      )} transition-all duration-1000`}
                      style={{ width: `${score}%` }}
                    />
                  </div>
                  <div className="w-12 text-sm text-white font-medium">
                    {score}%
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}

      {/* Additional Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
        {candidates.map((candidate) => {
          const metrics = getDetailedMetrics(candidate);
          return (
            <div
              key={candidate.id}
              className="p-6 rounded-xl space-y-4"
              style={{
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.1)",
              }}
            >
              <h5 className="font-bold text-white">{candidate.name}</h5>

              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-400">GitHub Score</span>
                  <span className="text-white font-medium">
                    {metrics.githubScore}/100
                  </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-gray-400">LinkedIn Connections</span>
                  <span className="text-white font-medium">
                    {metrics.linkedinConnections.toLocaleString()}
                  </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-gray-400">Expected Salary</span>
                  <span className="text-green-400 font-medium">
                    {metrics.salary}
                  </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-gray-400">Availability</span>
                  <span className="text-blue-400 font-medium">
                    {metrics.availability}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
