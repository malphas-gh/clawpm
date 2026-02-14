/**
 * ClawPM Sync Hook
 *
 * Auto-logs work sessions to clawpm work_log.jsonl when
 * OpenClaw session lifecycle events occur.
 */

import type { HookHandler } from "openclaw/hooks";
import { appendFileSync } from "fs";
import { join } from "path";
import { homedir } from "os";

interface WorkLogEntry {
  ts: string;
  project: string;
  task: string | null;
  action: "start" | "progress" | "done" | "blocked" | "pause" | "research" | "note";
  agent: string;
  session_key: string;
  summary: string;
  next: string | null;
  files_changed?: string[];
  blockers: string | null;
}

const handler: HookHandler = async (event) => {
  // Only handle command events
  if (event.type !== "command") return;

  // Only handle new and stop commands
  if (event.action !== "new" && event.action !== "stop") return;

  // Default to ~/clawpm, allow env override for testing
  const portfolioRoot = process.env.CLAWPM_PORTFOLIO || join(homedir(), "clawpm");

  try {
    const sessionKey = event.sessionKey;
    const timestamp = event.timestamp.toISOString();

    // Extract agent ID from session key (format: agent:<agentId>:<rest>)
    const agentId = sessionKey.split(":")[1] || "main";

    // TODO: In a full implementation, we would:
    // 1. Access event.context.sessionEntry to get the session
    // 2. Read recent messages from the transcript
    // 3. Use LLM to extract project/task/summary from conversation
    // For now, log a basic entry that can be enriched later

    const entry: WorkLogEntry = {
      ts: timestamp,
      project: "_unknown", // Would be extracted from conversation
      task: null, // Would be extracted from conversation
      action: "pause",
      agent: agentId,
      session_key: sessionKey,
      summary: `Session ${event.action} via /${event.action}`,
      next: null,
      blockers: null,
    };

    // Append to work log
    const workLogPath = join(portfolioRoot, "work_log.jsonl");
    const line = JSON.stringify(entry) + "\n";

    appendFileSync(workLogPath, line, "utf-8");
    console.log(`[clawpm-sync] Logged ${event.action} event for ${agentId}`);

    // Optionally notify user
    event.messages.push(`📋 Work logged to clawpm`);
  } catch (err) {
    console.error(
      "[clawpm-sync] Failed to log:",
      err instanceof Error ? err.message : String(err)
    );
    // Don't throw - let other handlers run
  }
};

export default handler;
