import { useMemo } from "react";
import { useT } from "../../i18n/useT.js";

/**
 * @param {{ messages: Array<{ tick?: number; round?: number; player?: string; text?: string }> }} props
 */
export default function DemoChatLogPanel({ messages = [] }) {
  const t = useT();
  const rows = useMemo(
    () => (Array.isArray(messages) ? messages : []).filter((m) => m?.text),
    [messages]
  );

  if (!rows.length) {
    return (
      <div className="space-y-1 py-2">
        <p className="text-xs text-cs2-text-muted font-mono">
          {t("fullDemo.chatEmpty")}
        </p>
        <p className="text-[10px] text-cs2-text-muted leading-relaxed">
          {t("fullDemo.chatEmptyHint")}
        </p>
      </div>
    );
  }

  return (
    <div className="max-h-48 overflow-y-auto rounded-md border border-cs2-border bg-cs2-bg-input/60 p-2 space-y-1">
      {rows.map((m, i) => (
        <div key={`${m.tick}-${m.player}-${i}`} className="text-[11px] font-mono leading-relaxed">
          <span className="text-cs2-text-muted">
            {m.round != null ? `R${m.round}` : "—"}
            {m.tick != null ? ` @${m.tick}` : ""}
          </span>
          <span className="text-cs2-accent ml-1.5">{m.player || "?"}</span>
          <span className="text-cs2-text-primary ml-1.5">{m.text}</span>
        </div>
      ))}
    </div>
  );
}
