"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles,
  Trophy,
  TrendingUp,
  AlertTriangle,
  Eye,
  Zap,
  Target,
  Brain,
  Award,
  Clock,
  BarChart3,
  CheckCircle,
  XCircle,
  Loader2,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

import {
  ComparisonAnalysisResponse,
  ComparisonRequest,
  HiddenInsight,
  ComparisonMatrix,
  ComparisonWinner,
} from "@/services/types";
import { analyzeComparison } from "@/services/apiService";

// Cache map outside component scope
const analysisCache = new Map<string, ComparisonAnalysisResponse>();

interface AIComparisonAdvisorProps {
  candidateIds: string[];
  candidateNames: Record<string, string>;
  jobContext?: {
    title?: string;
    description?: string;
    company?: string;
  };
}

export function AIComparisonAdvisor({
  candidateIds,
  candidateNames,
  jobContext,
}: AIComparisonAdvisorProps) {
  const [analysis, setAnalysis] = useState<ComparisonAnalysisResponse | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasStarted, setHasStarted] = useState(false);

  const cacheKey = JSON.stringify({
    ids: [...candidateIds].sort(),
    ctx: jobContext,
  });

  const startAnalysis = async () => {
    if (candidateIds.length < 2) {
      setError("Need at least 2 candidates for comparison");
      return;
    }

    const cacheKey = JSON.stringify({
      ids: [...candidateIds].sort(),
      ctx: jobContext,
    });
    if (analysisCache.has(cacheKey)) {
      setAnalysis(analysisCache.get(cacheKey)!);
      setHasStarted(true);
      return;
    }

    setHasStarted(true);
    setIsLoading(true);
    setError(null);

    try {
      const request: ComparisonRequest = {
        candidate_ids: candidateIds,
        job_role_title: jobContext?.title,
        job_role_description: jobContext?.description,
        company_context: jobContext?.company,
      };

      const result = await analyzeComparison(request);
      analysisCache.set(cacheKey, result);
      setAnalysis(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setIsLoading(false);
    }
  };

  if (!hasStarted) {
    return (
      <AnalysisPrompt
        onStart={startAnalysis}
        candidateCount={candidateIds.length}
      />
    );
  }

  if (isLoading) {
    return <LoadingAnalysis candidateNames={candidateNames} />;
  }

  if (error) {
    return <ErrorState error={error} onRetry={startAnalysis} />;
  }

  if (!analysis) {
    return (
      <AnalysisPrompt
        onStart={startAnalysis}
        candidateCount={candidateIds.length}
      />
    );
  }

  return (
    <AnalysisResults analysis={analysis} candidateNames={candidateNames} />
  );
}

function AnalysisPrompt({
  onStart,
  candidateCount,
}: {
  onStart: () => void;
  candidateCount: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center py-12 space-y-6"
    >
      <motion.div
        animate={{
          scale: [1, 1.05, 1],
          rotate: [0, 5, -5, 0],
        }}
        transition={{
          duration: 2,
          repeat: Infinity,
          ease: "easeInOut",
        }}
        className="w-20 h-20 bg-gradient-to-br from-purple-500 to-blue-500 rounded-2xl flex items-center justify-center"
      >
        <Brain className="w-10 h-10 text-white" />
      </motion.div>

      <div className="text-center space-y-2">
        <h3 className="text-2xl font-bold text-white">🤖 AI Hiring Advisor</h3>
        <p className="text-gray-400 max-w-md">
          Get AI-powered insights, hidden discoveries, and hiring
          recommendations for your {candidateCount} candidates.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm text-gray-300">
        <div className="flex items-center space-x-2">
          <Trophy className="w-4 h-4 text-yellow-400" />
          <span>Winner recommendation</span>
        </div>
        <div className="flex items-center space-x-2">
          <Eye className="w-4 h-4 text-blue-400" />
          <span>Hidden insights</span>
        </div>
        <div className="flex items-center space-x-2">
          <BarChart3 className="w-4 h-4 text-green-400" />
          <span>Comparison matrix</span>
        </div>
        <div className="flex items-center space-x-2">
          <Clock className="w-4 h-4 text-purple-400" />
          <span>Save 2-3 hours</span>
        </div>
      </div>

      <Button
        onClick={onStart}
        className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white px-8 py-3 rounded-lg font-medium"
      >
        <Zap className="w-4 h-4 mr-2" />
        Analyze with AI
      </Button>
    </motion.div>
  );
}

function LoadingAnalysis({
  candidateNames,
}: {
  candidateNames: Record<string, string>;
}) {
  const [currentStep, setCurrentStep] = useState(0);

  const steps = [
    "🔍 Analyzing candidate profiles...",
    "🧠 Discovering hidden insights...",
    "📊 Building comparison matrix...",
    "🏆 Determining best candidate...",
    "✨ Finalizing recommendations...",
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentStep((prev) => (prev + 1) % steps.length);
    }, 1500);
    return () => clearInterval(interval);
  }, [steps.length]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col items-center justify-center py-12 space-y-6"
    >
      <motion.div
        animate={{
          rotate: 360,
          scale: [1, 1.1, 1],
        }}
        transition={{
          rotate: { duration: 2, repeat: Infinity, ease: "linear" },
          scale: { duration: 1, repeat: Infinity, ease: "easeInOut" },
        }}
        className="w-16 h-16 bg-gradient-to-br from-purple-500 to-blue-500 rounded-full flex items-center justify-center"
      >
        <Sparkles className="w-8 h-8 text-white" />
      </motion.div>

      <div className="text-center space-y-4">
        <h3 className="text-xl font-bold text-white">
          AI is analyzing your candidates...
        </h3>

        <AnimatePresence mode="wait">
          <motion.p
            key={currentStep}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="text-gray-400"
          >
            {steps[currentStep]}
          </motion.p>
        </AnimatePresence>

        <div className="flex flex-wrap justify-center gap-2 max-w-md">
          {Object.values(candidateNames).map((name, index) => (
            <motion.div
              key={name}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{
                opacity: 1,
                scale: 1,
                backgroundColor:
                  currentStep > index
                    ? "rgba(139, 92, 246, 0.2)"
                    : "rgba(255, 255, 255, 0.05)",
              }}
              transition={{ delay: index * 0.2 }}
              className="px-3 py-1 rounded-full border border-white/10 text-sm text-gray-300"
            >
              {name}
            </motion.div>
          ))}
        </div>
      </div>

      <Progress value={(currentStep + 1) * 20} className="w-64" />
    </motion.div>
  );
}

function ErrorState({
  error,
  onRetry,
}: {
  error: string;
  onRetry: () => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex flex-col items-center justify-center py-12 space-y-4"
    >
      <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center">
        <XCircle className="w-8 h-8 text-red-400" />
      </div>

      <div className="text-center space-y-2">
        <h3 className="text-xl font-bold text-white">Analysis Failed</h3>
        <p className="text-gray-400 max-w-md">{error}</p>
      </div>

      <Button
        onClick={onRetry}
        variant="outline"
        className="border-gray-600 text-white hover:bg-white/10"
      >
        <Zap className="w-4 h-4 mr-2" />
        Try Again
      </Button>
    </motion.div>
  );
}

function AnalysisResults({
  analysis,
  candidateNames,
}: {
  analysis: ComparisonAnalysisResponse;
  candidateNames: Record<string, string>;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      {/* Success Header */}
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="text-center py-4"
      >
        <div className="flex items-center justify-center space-x-2 mb-2">
          <CheckCircle className="w-6 h-6 text-green-400" />
          <span className="text-lg font-semibold text-white">
            Analysis completed in {analysis.processing_time_ms.toFixed(0)}ms
          </span>
        </div>
        <p className="text-gray-400">
          AI confidence: {(analysis.ai_confidence * 100).toFixed(0)}%
        </p>
      </motion.div>

      {/* Winner Recommendation */}
      <WinnerCard winner={analysis.winner} candidateNames={candidateNames} />

      {/* Hidden Insights */}
      {analysis.hidden_insights.length > 0 && (
        <HiddenInsightsCard
          insights={analysis.hidden_insights}
          candidateNames={candidateNames}
        />
      )}

      {/* Comparison Matrix */}
      <ComparisonMatrixCard
        matrix={analysis.comparison_matrix}
        candidateNames={candidateNames}
      />

      {/* Individual Insights */}
      <IndividualInsightsCard
        candidates={analysis.candidates}
        candidateNames={candidateNames}
      />
    </motion.div>
  );
}

function WinnerCard({
  winner,
  candidateNames,
}: {
  winner: ComparisonWinner;
  candidateNames: Record<string, string>;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.3 }}
    >
      <Alert className="border-green-500 bg-green-50/5 border">
        <Trophy className="w-5 h-5 text-yellow-400" />
        <AlertTitle className="text-green-400 font-bold">
          🏆 Recommended:{" "}
          {candidateNames[winner.candidate_id] || winner.candidate_name}
        </AlertTitle>
        <AlertDescription className="mt-2 space-y-3">
          <p className="text-gray-300">{winner.reasoning}</p>

          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <h4 className="font-medium text-green-400 mb-2">
                Key Advantages:
              </h4>
              <ul className="space-y-1">
                {winner.key_advantages.map((advantage, index) => (
                  <li
                    key={index}
                    className="flex items-start space-x-2 text-sm"
                  >
                    <CheckCircle className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
                    <span className="text-gray-300">{advantage}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h4 className="font-medium text-yellow-400 mb-2">Consider:</h4>
              <ul className="space-y-1">
                {winner.potential_risks.map((risk, index) => (
                  <li
                    key={index}
                    className="flex items-start space-x-2 text-sm"
                  >
                    <AlertTriangle className="w-4 h-4 text-yellow-400 mt-0.5 flex-shrink-0" />
                    <span className="text-gray-300">{risk}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-white/10">
            <span className="text-sm text-gray-400">AI Confidence</span>
            <div className="flex items-center space-x-2">
              <Progress value={winner.confidence} className="w-24" />
              <span className="text-sm font-medium text-white">
                {winner.confidence}%
              </span>
            </div>
          </div>
        </AlertDescription>
      </Alert>
    </motion.div>
  );
}

function HiddenInsightsCard({
  insights,
  candidateNames,
}: {
  insights: HiddenInsight[];
  candidateNames: Record<string, string>;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.4 }}
    >
      <Card className="bg-white/5 border-white/10">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2 text-white">
            <Eye className="w-5 h-5 text-blue-400" />
            <span>🔍 Hidden Insights</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {insights.map((insight, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 + index * 0.1 }}
              className="p-4 rounded-lg bg-white/5 border border-white/10"
            >
              <div className="flex items-start justify-between mb-2">
                <h4 className="font-medium text-white">{insight.title}</h4>
                <Badge
                  variant={
                    insight.impact_level === "high"
                      ? "destructive"
                      : insight.impact_level === "medium"
                      ? "default"
                      : "secondary"
                  }
                  className="text-xs"
                >
                  {insight.impact_level} impact
                </Badge>
              </div>
              <p className="text-sm text-gray-300">{insight.description}</p>
              <p className="text-xs text-gray-500 mt-2">
                About:{" "}
                {candidateNames[insight.candidate_id] || insight.candidate_id}
              </p>
            </motion.div>
          ))}
        </CardContent>
      </Card>
    </motion.div>
  );
}

function ComparisonMatrixCard({
  matrix,
  candidateNames,
}: {
  matrix: ComparisonMatrix;
  candidateNames: Record<string, string>;
}) {
  const metrics = [
    {
      key: "technical_match",
      label: "Technical Match",
      color: "text-blue-400",
    },
    { key: "culture_fit", label: "Culture Fit", color: "text-green-400" },
    {
      key: "retention_risk",
      label: "Retention Risk",
      color: "text-red-400",
      invert: true,
    },
    {
      key: "growth_potential",
      label: "Growth Potential",
      color: "text-purple-400",
    },
  ];

  const displayScore = (score: number) => {
    const rounded = parseFloat(score.toFixed(1));
    return Number.isInteger(rounded) ? rounded : rounded.toFixed(1);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.5 }}
    >
      <Card className="bg-white/5 border-white/10">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2 text-white">
            <BarChart3 className="w-5 h-5 text-green-400" />
            <span>📊 Comparison Matrix</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {metrics.map((metric, index) => (
            <motion.div
              key={metric.key}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.6 + index * 0.1 }}
              className="space-y-2"
            >
              <h4 className={`font-medium ${metric.color}`}>{metric.label}</h4>
              <div className="space-y-2">
                {Object.entries(
                  matrix[metric.key as keyof ComparisonMatrix]
                ).map(([candidateId, score]) => (
                  <div
                    key={candidateId}
                    className="flex items-center space-x-3"
                  >
                    <span className="text-sm text-gray-300 w-32 truncate">
                      {candidateNames[candidateId] || candidateId}
                    </span>
                    <div className="flex-1">
                      <Progress
                        value={metric.invert ? 100 - score : score}
                        className="h-2"
                      />
                    </div>
                    <span className="text-sm font-medium text-white w-12 text-right">
                      {displayScore(score)}%
                    </span>
                  </div>
                ))}
              </div>
            </motion.div>
          ))}
        </CardContent>
      </Card>
    </motion.div>
  );
}

function IndividualInsightsCard({
  candidates,
  candidateNames,
}: {
  candidates: any[];
  candidateNames: Record<string, string>;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.7 }}
    >
      <Card className="bg-white/5 border-white/10">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2 text-white">
            <Target className="w-5 h-5 text-purple-400" />
            <span>🎯 Individual Analysis</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {candidates.map((candidate, index) => (
            <motion.div
              key={candidate.candidate_id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.8 + index * 0.1 }}
              className="p-4 rounded-lg bg-white/5 border border-white/10"
            >
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-medium text-white">
                  {candidateNames[candidate.candidate_id] ||
                    candidate.candidate_id}
                </h4>
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-400">Fit Score:</span>
                  <span className="font-bold text-white">
                    {candidate.fit_score}%
                  </span>
                </div>
              </div>

              <div className="space-y-2">
                <div>
                  <span className="text-sm font-medium text-green-400">
                    Strengths:
                  </span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {candidate.strengths.map(
                      (strength: string, idx: number) => (
                        <Badge
                          key={idx}
                          variant="secondary"
                          className="text-xs"
                        >
                          {strength}
                        </Badge>
                      )
                    )}
                  </div>
                </div>

                <div>
                  <span className="text-sm font-medium text-blue-400">
                    Sample Interview Questions:
                  </span>
                  <ul className="text-sm text-gray-300 mt-1 space-y-1">
                    {candidate.interview_questions
                      .slice(0, 2)
                      .map((question: string, idx: number) => (
                        <li key={idx} className="flex items-start space-x-2">
                          <span className="text-blue-400 mt-1">•</span>
                          <span>{question}</span>
                        </li>
                      ))}
                  </ul>
                </div>
              </div>
            </motion.div>
          ))}
        </CardContent>
      </Card>
    </motion.div>
  );
}
