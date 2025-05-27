"use client";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Candidate } from "@/lib/api";

interface OutreachModalProps {
  candidate: Candidate | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onGenerated: () => void;
}

export function OutreachModal({
  candidate,
  open,
  onOpenChange,
  onGenerated,
}: OutreachModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Generate Outreach Message</DialogTitle>
          <DialogDescription>
            {candidate
              ? `Draft a personalized message for ${candidate.name}`
              : "No candidate selected."}
          </DialogDescription>
        </DialogHeader>
        {candidate && (
          <div className="mb-4">
            <div className="font-bold">{candidate.name}</div>
            <div className="text-sm text-muted-foreground mb-2">
              {candidate.match_context}
            </div>
            <div className="flex flex-wrap gap-1">
              {candidate.skills?.map((skill) => (
                <span
                  key={skill}
                  className="bg-muted px-2 py-0.5 rounded text-xs"
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>
        )}
        <DialogFooter>
          <Button onClick={onGenerated} disabled={!candidate}>
            Generate Outreach
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
