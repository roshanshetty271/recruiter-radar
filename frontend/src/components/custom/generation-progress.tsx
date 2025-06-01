import { motion } from "framer-motion";
import { Progress } from "@/components/ui/progress";
import { Brain, Sparkles, Zap } from "lucide-react";

interface GenerationProgressProps {
  progress: number;
  stage: string;
}

export function GenerationProgress({
  progress,
  stage,
}: GenerationProgressProps) {
  const stages = [
    { icon: Brain, text: "Analyzing candidate profile..." },
    { icon: Sparkles, text: "Crafting personalized message..." },
    { icon: Zap, text: "Optimizing tone and style..." },
  ];

  const currentStageIndex = Math.floor((progress / 100) * stages.length);
  const CurrentIcon = stages[currentStageIndex]?.icon || Brain;

  return (
    <div className="space-y-4">
      {/* Neural Network Animation */}
      <div className="relative h-32 flex items-center justify-center">
        <motion.div
          className="absolute inset-0 flex items-center justify-center"
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{ repeat: Infinity, duration: 2 }}
        >
          <div className="relative">
            <CurrentIcon className="h-16 w-16 text-blue-500" />
            {/* Orbiting particles */}
            {[...Array(6)].map((_, i) => (
              <motion.div
                key={i}
                className="absolute w-2 h-2 bg-blue-400 rounded-full"
                style={{
                  top: "50%",
                  left: "50%",
                }}
                animate={{
                  x: [0, Math.cos((i * Math.PI) / 3) * 40, 0],
                  y: [0, Math.sin((i * Math.PI) / 3) * 40, 0],
                }}
                transition={{
                  repeat: Infinity,
                  duration: 3,
                  delay: i * 0.2,
                }}
              />
            ))}
          </div>
        </motion.div>
      </div>

      {/* Progress Bar */}
      <div className="relative">
        <Progress value={progress} className="h-3" />

        {/* Glowing effect on progress */}
        <motion.div
          className="absolute top-0 h-full bg-gradient-to-r from-transparent via-white/20 to-transparent"
          style={{ width: `${progress}%` }}
          animate={{
            x: ["-100%", "100%"],
          }}
          transition={{
            repeat: Infinity,
            duration: 1.5,
            ease: "linear",
          }}
        />
      </div>

      {/* Stage Text */}
      <motion.p
        key={stage}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center text-sm text-gray-600"
      >
        {stage}
      </motion.p>
    </div>
  );
}
