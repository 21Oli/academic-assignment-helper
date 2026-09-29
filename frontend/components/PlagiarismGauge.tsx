"use client";

interface Props {
  score: number; // 0–1
}

function getColor(score: number) {
  if (score < 0.3) return { bar: "bg-emerald-500", text: "text-emerald-700", label: "Low" };
  if (score < 0.6) return { bar: "bg-amber-400",   text: "text-amber-700",   label: "Medium" };
  return              { bar: "bg-red-500",          text: "text-red-700",     label: "High" };
}

export default function PlagiarismGauge({ score }: Props) {
  const pct = Math.round(score * 100);
  const { bar, text, label } = getColor(score);

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm font-medium">
        <span className={text}>Similarity Score — {label}</span>
        <span className={`font-bold ${text}`}>{pct}%</span>
      </div>
      <div className="h-3 w-full overflow-hidden rounded-full bg-slate-200">
        <div
          className={`h-full rounded-full transition-all duration-700 ${bar}`}
          style={{ width: `${pct}%` }}
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
    </div>
  );
}
