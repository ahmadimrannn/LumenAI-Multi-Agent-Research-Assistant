import type { Session } from "@/lib/types"

export interface SessionGroup {
  label: "Today" | "Yesterday" | "Previous 7 days" | "Older"
  sessions: Session[]
}

export function groupSessions(sessions: Session[]): SessionGroup[] {
  const now = new Date()
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const startOfYesterday = startOfToday - 86400000
  const startOf7DaysAgo = startOfToday - 7 * 86400000

  const today: Session[] = []
  const yesterday: Session[] = []
  const previous7Days: Session[] = []
  const older: Session[] = []

  for (const session of sessions) {
    const time = new Date(session.updatedAt).getTime()
    if (isNaN(time)) {
      older.push(session)
    } else if (time >= startOfToday) {
      today.push(session)
    } else if (time >= startOfYesterday) {
      yesterday.push(session)
    } else if (time >= startOf7DaysAgo) {
      previous7Days.push(session)
    } else {
      older.push(session)
    }
  }

  const groups: SessionGroup[] = []
  if (today.length > 0) groups.push({ label: "Today", sessions: today })
  if (yesterday.length > 0) groups.push({ label: "Yesterday", sessions: yesterday })
  if (previous7Days.length > 0) groups.push({ label: "Previous 7 days", sessions: previous7Days })
  if (older.length > 0) groups.push({ label: "Older", sessions: older })

  return groups
}
