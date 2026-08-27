import { useEffect, useState } from "react";
import API from "../api/api";
import { Loader2 } from "lucide-react";
import { useT } from "../i18n/useT.js";
import DemoChatLogPanel from "./recordingQueue/DemoChatLogPanel.jsx";

/**
 * @param {{
 *   open: boolean;
 *   onClose: () => void;
 *   demoId: number | null;
 *   playerName: string;
 *   matchMeta: object | null;
 *   demoPath?: string;
 *   demoFilename?: string;
 *   targetSteamId?: string | null;
 *   onConfirm: (payload: object) => void;
 * }} props
 */
export default function FullDemoEnqueueModal({
  open,
  onClose,
  demoId,
  playerName,
  matchMeta,
  demoPath = "",
  demoFilename = "",
  targetSteamId = null,
  onConfirm,
}) {
  const t = useT();
  const [showChat, setShowChat] = useState(false);
  const [voiceBoost, setVoiceBoost] = useState(1.5);
  const [listenAll, setListenAll] = useState(true);
  const [deathFollowMode, setDeathFollowMode] = useState("off");
  const [loadingChat, setLoadingChat] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);

  useEffect(() => {
    if (!open) return;
    setShowChat(false);
    setVoiceBoost(1.5);
    setListenAll(true);
    setDeathFollowMode("off");
    setChatMessages([]);
    if (!demoId) return;
    let cancelled = false;
    (async () => {
      setLoadingChat(true);
      try {
        const { data } = await API.get(`/demos/${demoId}/chat-log`);
        if (!cancelled) setChatMessages(data?.messages || []);
      } catch {
        if (!cancelled) setChatMessages([]);
      } finally {
        if (!cancelled) setLoadingChat(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open, demoId]);

  if (!open) return null;

  const handleConfirm = () => {
    const uid = `full_demo_${playerName}_${Date.now()}`;
    const roster = (matchMeta?.all_players || []).find(
      (p) => String(p?.name || "").trim() === String(playerName || "").trim()
    );
    onConfirm({
      demoPath,
      demoFilename,
      targetPlayer: playerName,
      targetSteamId: targetSteamId || roster?.steamid64 || null,
      matchMeta,
      demoChatLog: chatMessages,
      pacing_override: {
        show_ingame_chat: showChat,
        voice_comm_boost: Number(voiceBoost) || 1.0,
        listen_all_voice: listenAll,
        death_follow_mode: deathFollowMode,
      },
      clipData: {
        category: "full_demo",
        compilation_kind: "full_demo",
        workbench_clip_kind: "full_demo",
        recording_request_type: "full_demo",
        clip_id: uid,
        client_clip_uid: uid,
        map_name: matchMeta?.map_name || "unknown",
        tick_rate: 64,
        start_tick: Number(matchMeta?.match_start_tick) || 0,
        end_tick: Number(matchMeta?.demo_max_tick) || 0,
        target_spec_slot: roster?.spec_slot ?? null,
        fixed_segment_pacing: true,
      },
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-lg rounded-xl border border-cs2-border bg-cs2-bg-sidebar shadow-2xl">
        <div className="border-b border-cs2-border px-5 py-4">
          <h3 className="text-sm font-bold text-cs2-text-primary">{t("fullDemo.modalTitle")}</h3>
          <p className="mt-1 text-xs text-cs2-text-secondary">{t("fullDemo.modalDesc", { player: playerName })}</p>
        </div>
        <div className="px-5 py-4 space-y-4">
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              className="mt-0.5"
              checked={showChat}
              onChange={(e) => setShowChat(e.target.checked)}
            />
            <span>
              <span className="block text-xs font-semibold text-cs2-text-primary">{t("fullDemo.showChat")}</span>
              <span className="block text-[11px] text-cs2-text-muted">{t("fullDemo.showChatDesc")}</span>
            </span>
          </label>
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              className="mt-0.5"
              checked={listenAll}
              onChange={(e) => setListenAll(e.target.checked)}
            />
            <span>
              <span className="block text-xs font-semibold text-cs2-text-primary">{t("fullDemo.listenAllVoice")}</span>
              <span className="block text-[11px] text-cs2-text-muted">{t("fullDemo.listenAllVoiceDesc")}</span>
            </span>
          </label>
          <div>
            <p className="text-xs font-semibold text-cs2-text-primary mb-2">{t("fullDemo.deathFollowTitle")}</p>
            <p className="text-[11px] text-cs2-text-muted mb-2">{t("fullDemo.deathFollowDesc")}</p>
            <div className="space-y-2">
              {[
                { value: "off", label: t("fullDemo.deathFollowOff") },
                { value: "killer", label: t("fullDemo.deathFollowKiller") },
                { value: "teammate", label: t("fullDemo.deathFollowTeammate") },
              ].map((opt) => (
                <label key={opt.value} className="flex items-center gap-2 cursor-pointer text-xs text-cs2-text-primary">
                  <input
                    type="radio"
                    name="deathFollowMode"
                    value={opt.value}
                    checked={deathFollowMode === opt.value}
                    onChange={() => setDeathFollowMode(opt.value)}
                  />
                  {opt.label}
                </label>
              ))}
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between text-xs font-semibold text-cs2-text-primary mb-1">
              <span>{t("fullDemo.voiceBoost")}</span>
              <span className="font-mono text-cs2-accent">{Number(voiceBoost).toFixed(1)}×</span>
            </div>
            <input
              type="range"
              min={1}
              max={2}
              step={0.1}
              value={voiceBoost}
              onChange={(e) => setVoiceBoost(Number(e.target.value))}
              className="w-full"
            />
            <p className="text-[11px] text-cs2-text-muted mt-1">{t("fullDemo.voiceBoostDesc")}</p>
          </div>
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold text-cs2-text-primary mb-2">
              {t("fullDemo.chatLogTitle")}
              {loadingChat && <Loader2 className="h-3 w-3 animate-spin text-cs2-text-muted" />}
              {!loadingChat && (
                <span className="font-mono text-cs2-text-muted">{chatMessages.length}</span>
              )}
            </div>
            <DemoChatLogPanel messages={chatMessages} />
          </div>
        </div>
        <div className="flex justify-end gap-2 border-t border-cs2-border px-5 py-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-cs2-border px-4 py-2 text-xs font-semibold text-cs2-text-secondary hover:text-cs2-text-primary"
          >
            {t("common.cancel")}
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            className="rounded-lg bg-cs2-accent px-4 py-2 text-xs font-bold text-black hover:opacity-90"
          >
            {t("fullDemo.addToQueue")}
          </button>
        </div>
      </div>
    </div>
  );
}
