"use client";

import React from "react";
import { ChevronLeftIcon, ChevronRightIcon, DownloadIcon } from "lucide-react";
import { Button } from "./button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./select";
import { Input } from "./input";
import { Badge } from "./badge";
import { PaginationInfo } from "@/services/types";

interface PaginationComponentProps {
  pagination: PaginationInfo;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  onLoadMore?: () => void;
  onExportAll?: () => void;
  loading?: boolean;
  showLoadMore?: boolean;
  showExport?: boolean;
}

export function PaginationComponent({
  pagination,
  onPageChange,
  onPageSizeChange,
  onLoadMore,
  onExportAll,
  loading = false,
  showLoadMore = true,
  showExport = true,
}: PaginationComponentProps) {
  const [jumpToPage, setJumpToPage] = React.useState("");

  const handleJumpToPage = () => {
    const page = parseInt(jumpToPage);
    if (page >= 1 && page <= pagination.total_pages) {
      onPageChange(page);
      setJumpToPage("");
    }
  };

  const getVisiblePages = () => {
    const current = pagination.current_page;
    const total = pagination.total_pages;
    const delta = 2;

    const range = [];
    const rangeWithDots = [];

    // Always include first page
    range.push(1);

    // Add pages around current page
    for (
      let i = Math.max(2, current - delta);
      i <= Math.min(total - 1, current + delta);
      i++
    ) {
      range.push(i);
    }

    // Always include last page if more than 1 page
    if (total > 1) {
      range.push(total);
    }

    // Add dots where needed
    let prev = 1;
    for (const page of range) {
      if (page - prev > 1) {
        rangeWithDots.push("...");
      }
      rangeWithDots.push(page);
      prev = page;
    }

    return rangeWithDots;
  };

  if (pagination.total_candidates === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      {/* Main Pagination Bar */}
      <div className="flex items-center justify-between bg-white/5 backdrop-blur-md rounded-xl p-4 border border-white/10">
        {/* Left: Results Info */}
        <div className="flex items-center space-x-4">
          <div className="text-sm text-gray-300">
            Showing{" "}
            <span className="font-semibold text-white">
              {pagination.start_index + 1}
            </span>
            {" - "}
            <span className="font-semibold text-white">
              {pagination.end_index + 1}
            </span>
            {" of "}
            <span className="font-semibold text-blue-400">
              {pagination.total_candidates}
            </span>
            {" candidates"}
          </div>

          {/* Page Size Selector */}
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-400">Show:</span>
            <Select
              value={pagination.page_size.toString()}
              onValueChange={(value) => onPageSizeChange(parseInt(value))}
            >
              <SelectTrigger className="w-20 h-8 bg-white/10 border-white/20">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="10">10</SelectItem>
                <SelectItem value="20">20</SelectItem>
                <SelectItem value="50">50</SelectItem>
                <SelectItem value="100">100</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Center: Page Navigation */}
        <div className="flex items-center space-x-2">
          {/* Previous Button */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(pagination.current_page - 1)}
            disabled={!pagination.has_previous || loading}
            className="bg-white/10 border-white/20 hover:bg-white/20"
          >
            <ChevronLeftIcon className="w-4 h-4" />
            Previous
          </Button>

          {/* Page Numbers */}
          <div className="flex items-center space-x-1">
            {getVisiblePages().map((page, index) => {
              if (page === "...") {
                return (
                  <span key={index} className="px-2 text-gray-400">
                    ...
                  </span>
                );
              }

              const pageNum = page as number;
              const isCurrentPage = pageNum === pagination.current_page;

              return (
                <Button
                  key={pageNum}
                  variant={isCurrentPage ? "default" : "outline"}
                  size="sm"
                  onClick={() => onPageChange(pageNum)}
                  disabled={loading}
                  className={
                    isCurrentPage
                      ? "bg-blue-600 text-white hover:bg-blue-700"
                      : "bg-white/10 border-white/20 hover:bg-white/20"
                  }
                >
                  {pageNum}
                </Button>
              );
            })}
          </div>

          {/* Next Button */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(pagination.current_page + 1)}
            disabled={!pagination.has_next || loading}
            className="bg-white/10 border-white/20 hover:bg-white/20"
          >
            Next
            <ChevronRightIcon className="w-4 h-4" />
          </Button>
        </div>

        {/* Right: Additional Actions */}
        <div className="flex items-center space-x-3">
          {/* Jump to Page */}
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-400">Go to:</span>
            <div className="flex items-center space-x-1">
              <Input
                type="number"
                min="1"
                max={pagination.total_pages}
                value={jumpToPage}
                onChange={(e) => setJumpToPage(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && handleJumpToPage()}
                placeholder="Page"
                className="w-16 h-8 bg-white/10 border-white/20 text-center"
              />
              <Button
                size="sm"
                onClick={handleJumpToPage}
                disabled={!jumpToPage || loading}
                className="h-8 px-2"
              >
                Go
              </Button>
            </div>
          </div>

          {/* Export Button */}
          {showExport && onExportAll && (
            <Button
              variant="outline"
              size="sm"
              onClick={onExportAll}
              disabled={loading}
              className="bg-white/10 border-white/20 hover:bg-white/20"
            >
              <DownloadIcon className="w-4 h-4 mr-2" />
              Export All
            </Button>
          )}
        </div>
      </div>

      {/* Load More Section (Recruiter-Friendly) */}
      {showLoadMore && pagination.has_next && onLoadMore && (
        <div className="flex flex-col items-center space-y-3 py-4">
          <Button
            onClick={onLoadMore}
            disabled={loading}
            size="lg"
            className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white px-8 py-3 rounded-xl"
          >
            {loading
              ? "Loading..."
              : `Load More Candidates (${
                  pagination.total_candidates - pagination.end_index - 1
                } remaining)`}
          </Button>

          <div className="text-sm text-gray-400 text-center">
            You've seen {pagination.end_index + 1} of{" "}
            {pagination.total_candidates} candidates
            <br />
            <Badge variant="outline" className="mt-1">
              Page {pagination.current_page} of {pagination.total_pages}
            </Badge>
          </div>
        </div>
      )}

      {/* Pagination Summary */}
      <div className="text-center text-xs text-gray-500">
        {pagination.total_pages > 1 && (
          <>
            <span>
              Page {pagination.current_page} of {pagination.total_pages}
            </span>
            {" • "}
          </>
        )}
        <span>{pagination.total_candidates} total candidates found</span>
      </div>
    </div>
  );
}
