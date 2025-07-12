"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ChevronLeft, ChevronRight, Zap, Download } from "lucide-react";
import { PaginationInfo } from "@/lib/types";

interface CandidatePaginationProps {
  pagination: PaginationInfo;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  onLoadMore?: () => void;
  onExportAll?: () => void;
  loading?: boolean;
  showLoadMore?: boolean;
  showExport?: boolean;
}

export function CandidatePagination({
  pagination,
  onPageChange,
  onPageSizeChange,
  onLoadMore,
  onExportAll,
  loading = false,
  showLoadMore = true,
  showExport = true,
}: CandidatePaginationProps) {
  const {
    current_page,
    page_size,
    total_candidates,
    total_pages,
    has_next,
    has_previous,
    start_index,
    end_index,
  } = pagination;

  // Calculate display indices (1-based for user display)
  const displayStart = total_candidates > 0 ? start_index + 1 : 0;
  const displayEnd = total_candidates > 0 ? end_index + 1 : 0;

  return (
    <div className="space-y-4">
      {/* 🎯 MAIN RESULTS INFO */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 px-6 py-5 bg-gray-800/30 backdrop-blur border border-gray-700/50 rounded-xl">
        {/* Left Section: Results Info */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-4 sm:gap-8">
          {/* Results Counter */}
          <div className="flex items-center space-x-3">
            <Zap className="h-5 w-5 text-purple-400" />
            <span className="text-gray-300 font-medium">
              Showing {displayStart}-{displayEnd} of{" "}
              <span className="text-white font-semibold">
                {total_candidates}
              </span>{" "}
              candidates
            </span>
          </div>

          {/* Page Size Selector */}
          <div className="flex items-center space-x-3">
            <span className="text-gray-400 text-sm whitespace-nowrap">
              Show:
            </span>
            <Select
              value={page_size.toString()}
              onValueChange={(value) => onPageSizeChange(Number(value))}
              disabled={loading}
            >
              <SelectTrigger className="w-20 h-9 bg-gray-700/50 border-gray-600 text-white">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-gray-800 border-gray-600">
                <SelectItem value="10" className="text-white hover:bg-gray-700">
                  10
                </SelectItem>
                <SelectItem value="20" className="text-white hover:bg-gray-700">
                  20
                </SelectItem>
                <SelectItem value="50" className="text-white hover:bg-gray-700">
                  50
                </SelectItem>
                <SelectItem
                  value="100"
                  className="text-white hover:bg-gray-700"
                >
                  100
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Right Section: Navigation & Actions */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-4">
          {/* Page Navigation */}
          {total_pages > 1 && (
            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onPageChange(current_page - 1)}
                disabled={!has_previous || loading}
                className="bg-gray-700/50 border-gray-600 hover:bg-gray-600 text-white disabled:opacity-50 px-4 h-9"
              >
                <ChevronLeft className="h-4 w-4 mr-2" />
                Previous
              </Button>

              <div className="flex items-center space-x-2 px-4 py-2 bg-gray-700/40 rounded-lg border border-gray-600/50 min-w-[120px] justify-center">
                <span className="text-gray-400 text-sm">Page</span>
                <span className="text-white font-semibold text-base">
                  {current_page}
                </span>
                <span className="text-gray-400 text-sm">of</span>
                <span className="text-white font-semibold text-base">
                  {total_pages}
                </span>
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={() => onPageChange(current_page + 1)}
                disabled={!has_next || loading}
                className="bg-gray-700/50 border-gray-600 hover:bg-gray-600 text-white disabled:opacity-50 px-4 h-9"
              >
                Next
                <ChevronRight className="h-4 w-4 ml-2" />
              </Button>
            </div>
          )}

          {/* Export Button */}
          {showExport && onExportAll && (
            <Button
              variant="outline"
              size="sm"
              onClick={onExportAll}
              disabled={loading}
              className="bg-purple-600/20 border-purple-500/50 hover:bg-purple-600/30 text-purple-300 px-4 h-9"
            >
              <Download className="h-4 w-4 mr-2" />
              Export All
            </Button>
          )}
        </div>
      </div>

      {/* 🚀 LOAD MORE SECTION (AI-Style Progressive Loading) */}
      {showLoadMore && has_next && onLoadMore && (
        <div className="text-center">
          <Button
            onClick={onLoadMore}
            disabled={loading}
            className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white px-8 py-3 rounded-xl font-medium shadow-lg hover:shadow-xl transition-all duration-200"
          >
            <Zap className="h-4 w-4 mr-2" />
            {loading ? "Loading..." : `Load More Candidates`}
            {!loading && (
              <span className="ml-2 text-purple-200">
                ({total_candidates - displayEnd} remaining)
              </span>
            )}
          </Button>
        </div>
      )}
    </div>
  );
}
