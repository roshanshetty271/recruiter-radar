"use client";

import { useState, useEffect } from "react";
import { MapPin, Globe, Clock, Code, X } from "lucide-react";
import { Input } from "./ui/input";
import { Button } from "./ui/button";
import { Slider } from "./ui/slider";

export function AdvancedFilters({
  onFiltersChange,
}: {
  onFiltersChange: (count: number, filterData: any) => void;
}) {
  const [location, setLocation] = useState("");
  const [visaStatus, setVisaStatus] = useState<string[]>([]);
  const [experience, setExperience] = useState([0]);
  const [skills, setSkills] = useState<string[]>([]);
  const [newSkill, setNewSkill] = useState("");

  const visaOptions = [
    { value: "us-citizen", label: "🇺🇸 US Citizen", flag: "🇺🇸" },
    { value: "green-card", label: "🇺🇸 Green Card", flag: "🇺🇸" },
    { value: "h1b", label: "🇺🇸 H1B Visa", flag: "🇺🇸" },
    { value: "eu-citizen", label: "🇪🇺 EU Citizen", flag: "🇪🇺" },
  ];

  const popularSkills = [
    "React 🔥",
    "Python 🔥",
    "JavaScript 🔥",
    "TypeScript",
    "Node.js",
    "AWS",
    "Docker",
    "Kubernetes",
  ];

  const addSkill = (skill: string) => {
    if (skill && !skills.includes(skill) && skills.length < 10) {
      setSkills([...skills, skill]);
      setNewSkill("");
      updateFilterCount();
    }
  };

  const removeSkill = (skillToRemove: string) => {
    setSkills(skills.filter((skill) => skill !== skillToRemove));
    updateFilterCount();
  };

  const updateFilterCount = () => {
    let count = 0;
    if (location) count++;
    if (visaStatus.length > 0) count++;
    if (experience[0] > 0) count++;
    if (skills.length > 0) count++;

    // Create filter data object to pass to the API
    const filterData = {
      location: location || undefined,
      visa_status: visaStatus.length ? visaStatus.join(",") : undefined,
      min_experience: experience[0] > 0 ? experience[0] : undefined,
      skills: skills.length ? skills.join(",") : undefined,
    };

    // Pass both count and filter data
    onFiltersChange(count, filterData);
  };

  // Call updateFilterCount whenever any filter changes
  useEffect(() => {
    updateFilterCount();
  }, [location, visaStatus, experience, skills]);

  return (
    <div
      className="p-6 rounded-xl space-y-6 animate-in slide-in-from-top-4 duration-300"
      style={{
        background: "rgba(255,255,255,0.03)",
        backdropFilter: "blur(12px)",
        border: "1px solid rgba(255,255,255,0.1)",
      }}
    >
      <div className="grid md:grid-cols-2 gap-6">
        {/* Location */}
        <div className="space-y-3">
          <label className="flex items-center space-x-2 text-sm font-medium text-white">
            <MapPin className="w-4 h-4" />
            <span>Location</span>
          </label>
          <Input
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="San Francisco, Remote, etc."
            className="bg-white/5 border-white/10 text-white placeholder-gray-400"
          />
        </div>

        {/* Visa Status */}
        <div className="space-y-3">
          <label className="flex items-center space-x-2 text-sm font-medium text-white">
            <Globe className="w-4 h-4" />
            <span>Visa Status</span>
          </label>
          <div className="grid grid-cols-2 gap-2">
            {visaOptions.map((option) => (
              <label
                key={option.value}
                className="flex items-center space-x-2 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={visaStatus.includes(option.value)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setVisaStatus([...visaStatus, option.value]);
                    } else {
                      setVisaStatus(
                        visaStatus.filter((v) => v !== option.value)
                      );
                    }
                  }}
                  className="rounded border-white/20 bg-white/5"
                />
                <span className="text-sm text-gray-300">{option.label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Experience */}
        <div className="space-y-3">
          <label className="flex items-center space-x-2 text-sm font-medium text-white">
            <Clock className="w-4 h-4" />
            <span>Experience: {experience[0]} years</span>
          </label>
          <Slider
            value={experience}
            onValueChange={setExperience}
            max={20}
            step={1}
            className="w-full"
          />
        </div>

        {/* Skills */}
        <div className="space-y-3">
          <label className="flex items-center space-x-2 text-sm font-medium text-white">
            <Code className="w-4 h-4" />
            <span>Skills ({skills.length}/10)</span>
          </label>

          <div className="flex space-x-2">
            <Input
              value={newSkill}
              onChange={(e) => setNewSkill(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && addSkill(newSkill)}
              placeholder="Add skill..."
              className="bg-white/5 border-white/10 text-white placeholder-gray-400"
            />
            <Button
              onClick={() => addSkill(newSkill)}
              variant="outline"
              size="sm"
              className="border-white/20 text-white hover:bg-white/10"
            >
              Add
            </Button>
          </div>

          {/* Popular Skills */}
          <div className="flex flex-wrap gap-2">
            {popularSkills.map((skill) => (
              <button
                key={skill}
                onClick={() => addSkill(skill)}
                className="px-3 py-1 text-xs bg-white/10 hover:bg-white/20 rounded-full text-gray-300 hover:text-white transition-colors"
              >
                {skill}
              </button>
            ))}
          </div>

          {/* Selected Skills */}
          {skills.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {skills.map((skill) => (
                <div
                  key={skill}
                  className="flex items-center space-x-1 px-3 py-1 bg-purple-600/20 border border-purple-400/30 rounded-full text-sm text-purple-200"
                >
                  <span>{skill}</span>
                  <button
                    onClick={() => removeSkill(skill)}
                    className="hover:text-white"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
