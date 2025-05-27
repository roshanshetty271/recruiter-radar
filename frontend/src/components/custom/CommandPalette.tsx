"use client";

import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { Search, Clock, Settings, FileText, HelpCircle } from "lucide-react";

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  recentSearches: string[];
  onSearch: (query: string) => void;
}

export function CommandPalette(props: CommandPaletteProps) {
  return (
    <CommandDialog open={props.open} onOpenChange={props.onOpenChange}>
      <CommandInput placeholder="Type a command or search..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>

        <CommandGroup heading="Quick Actions">
          <CommandItem
            onSelect={() => {
              document.getElementById("main-search")?.focus();
              props.onOpenChange(false);
            }}
          >
            <Search className="mr-2 h-4 w-4" />
            <span>New Search</span>
            <kbd className="ml-auto text-xs">⌘S</kbd>
          </CommandItem>

          <CommandItem>
            <FileText className="mr-2 h-4 w-4" />
            <span>Export Results</span>
            <kbd className="ml-auto text-xs">⌘E</kbd>
          </CommandItem>

          <CommandItem>
            <Settings className="mr-2 h-4 w-4" />
            <span>Settings</span>
          </CommandItem>

          <CommandItem>
            <HelpCircle className="mr-2 h-4 w-4" />
            <span>Help & Shortcuts</span>
            <kbd className="ml-auto text-xs">?</kbd>
          </CommandItem>
        </CommandGroup>

        {props.recentSearches.length > 0 && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Recent Searches">
              {props.recentSearches.map((search) => (
                <CommandItem
                  key={search}
                  onSelect={() => props.onSearch(search)}
                >
                  <Clock className="mr-2 h-4 w-4" />
                  <span>{search}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        )}
      </CommandList>
    </CommandDialog>
  );
}
