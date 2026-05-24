import { cn, rankColor } from "../lib/utils.js";

export default function RankBadge({ rank }) {
  return (
    <span
      className={cn(
        "inline-flex items-center justify-center w-7 h-7 rounded-full text-sm font-bold border",
        rank === 1
          ? "border-yellow-400/40 bg-yellow-400/10 text-yellow-400"
          : rank === 2
          ? "border-gray-400/40 bg-gray-400/10 text-gray-300"
          : rank === 3
          ? "border-amber-600/40 bg-amber-600/10 text-amber-600"
          : "border-surface-border bg-surface text-gray-500"
      )}
    >
      {rank}
    </span>
  );
}
