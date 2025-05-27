"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Filter, Sparkles } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Collapsible, CollapsibleContent } from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

interface SearchInterfaceProps {
  value: string;
  onChange: (value: string) => void;
  filters: {
    location: string;
    visaStatus: string;
    minExperience: number;
    skills: string[];
  };
  onFiltersChange: (filters: Partial<SearchInterfaceProps["filters"]>) => void;
  onSearch: () => void;
  isSearching: boolean;
  searchProgress: string;
  recentSearches: string[];
}

export function SearchInterface(props: SearchInterfaceProps) {
  const [showFilters, setShowFilters] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [skillInput, setSkillInput] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  // Get suggestions as user types
  useEffect(() => {
    if (props.value.length > 2) {
      api.getSearchSuggestions(props.value).then(setSuggestions);
      setShowSuggestions(true);
    } else {
      setShowSuggestions(false);
    }
  }, [props.value]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !props.isSearching) {
      props.onSearch();
      setShowSuggestions(false);
    }
  };

  const addSkill = () => {
    if (
      skillInput.trim() &&
      !props.filters.skills.includes(skillInput.trim())
    ) {
      props.onFiltersChange({
        skills: [...props.filters.skills, skillInput.trim()],
      });
      setSkillInput("");
    }
  };

  const removeSkill = (skill: string) => {
    props.onFiltersChange({
      skills: props.filters.skills.filter((s) => s !== skill),
    });
  };

  return (
    <div className="mb-8 space-y-4">
      {/* Main Search Bar */}
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="relative"
      >
        <div
          className={cn(
            "relative flex items-center glass rounded-lg transition-all duration-300",
            props.isSearching &&
              "ring-2 ring-blue-500 ring-offset-2 ring-offset-background"
          )}
        >
          <Search className="absolute left-4 w-5 h-5 text-muted-foreground" />

          <Input
            ref={inputRef}
            id="main-search"
            value={props.value}
            onChange={(e) => props.onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            placeholder="Search for your next star engineer..."
            className="pl-12 pr-32 py-6 text-lg bg-transparent border-0 focus-visible:ring-0"
            disabled={props.isSearching}
          />

          <div className="absolute right-2 flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => setShowFilters(!showFilters)}
            >
              <Filter
                className={cn("w-4 h-4", showFilters && "text-blue-500")}
              />
            </Button>

            <Button
              onClick={props.onSearch}
              disabled={props.isSearching || !props.value.trim()}
              className="h-8"
            >
              {props.isSearching ? (
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                >
                  <Sparkles className="w-4 h-4 mr-2" />
                </motion.div>
              ) : (
                <Search className="w-4 h-4 mr-2" />
              )}
              Search
            </Button>
          </div>
        </div>

        {/* Search Progress */}
        <AnimatePresence>
          {props.searchProgress && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="absolute -bottom-6 left-0 text-sm text-muted-foreground"
            >
              {props.searchProgress}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Suggestions Dropdown */}
        <AnimatePresence>
          {showSuggestions && suggestions.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="absolute top-full mt-2 w-full glass rounded-lg p-2 z-50"
            >
              {suggestions.map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => {
                    props.onChange(suggestion);
                    setShowSuggestions(false);
                  }}
                  className="w-full text-left px-4 py-2 hover:bg-white/5 rounded transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Filters Section */}
      <Collapsible open={showFilters} onOpenChange={setShowFilters}>
        <CollapsibleContent>
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass rounded-lg p-6 space-y-4"
          >
            <h3 className="text-sm font-medium mb-4">Refine your search</h3>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Location Filter */}
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">
                  Location
                </label>
                <Input
                  value={props.filters.location}
                  onChange={(e) =>
                    props.onFiltersChange({ location: e.target.value })
                  }
                  placeholder="e.g., San Francisco"
                  className="bg-background/50"
                />
              </div>

              {/* Visa Status Filter */}
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">
                  Visa Status
                </label>
                <Select
                  value={props.filters.visaStatus}
                  onValueChange={(value) =>
                    props.onFiltersChange({ visaStatus: value })
                  }
                >
                  <SelectTrigger className="bg-background/50">
                    <SelectValue placeholder="Any visa status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Any</SelectItem>
                    <SelectItem value="US Citizen">US Citizen</SelectItem>
                    <SelectItem value="Green Card">Green Card</SelectItem>
                    <SelectItem value="H1B">H1B</SelectItem>
                    <SelectItem value="F-1 OPT">F-1 OPT</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Experience Filter */}
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">
                  Min. Experience: {props.filters.minExperience}+ years
                </label>
                <Slider
                  value={[props.filters.minExperience]}
                  onValueChange={([value]) =>
                    props.onFiltersChange({ minExperience: value })
                  }
                  max={15}
                  step={1}
                  className="py-2"
                />
              </div>
            </div>

            {/* Skills Filter */}
            <div className="space-y-2">
              <label className="text-sm text-muted-foreground">
                Required Skills
              </label>
              <div className="flex gap-2">
                <Input
                  value={skillInput}
                  onChange={(e) => setSkillInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addSkill()}
                  placeholder="Add a skill..."
                  className="bg-background/50"
                />
                <Button onClick={addSkill} size="sm">
                  Add
                </Button>
              </div>
              <div className="flex flex-wrap gap-2 mt-2">
                {props.filters.skills.map((skill) => (
                  <Badge
                    key={skill}
                    variant="secondary"
                    className="cursor-pointer"
                    onClick={() => removeSkill(skill)}
                  >
                    {skill} ×
                  </Badge>
                ))}
              </div>
            </div>
          </motion.div>
        </CollapsibleContent>
      </Collapsible>

      {/* Keyboard Shortcut Hint */}
      <div className="flex items-center justify-center gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          Press{" "}
          <kbd className="px-1.5 py-0.5 bg-muted rounded text-[10px]">/</kbd> to
          focus search
        </span>
        <span className="flex items-center gap-1">
          Press{" "}
          <kbd className="px-1.5 py-0.5 bg-muted rounded text-[10px]">⌘K</kbd>{" "}
          for command palette
        </span>
      </div>
    </div>
  );
}
