"use client";

import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Sparkles, Search, Users } from "lucide-react";
import { APITest } from "@/lib/api-test";
import { LocationHeatMap } from "@/components/custom/LocationHeatMap";

export default function Home() {
  return (
    <main className="min-h-screen p-8">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-7xl mx-auto space-y-8"
      >
        <div className="text-center space-y-4">
          <Badge variant="outline" className="glass">
            <Sparkles className="w-3 h-3 mr-1" />
            AI-Powered Recruiting
          </Badge>

          <h1 className="text-5xl font-bold gradient-text">RecruiterRadar</h1>

          <p className="text-muted-foreground text-lg">
            Find perfect candidates with AI
          </p>
        </div>

        <LocationHeatMap />

        <Card className="glass p-6 glow">
          <p>Welcome to the future of recruiting!</p>
          <div className="flex gap-4 mt-4">
            <Button>
              <Search className="w-4 h-4 mr-2" />
              Start Searching
            </Button>
            <Button variant="outline" className="glass">
              <Users className="w-4 h-4 mr-2" />
              View Candidates
            </Button>
          </div>
        </Card>

        <APITest />
      </motion.div>
    </main>
  );
}
