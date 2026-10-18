"use client"
import { Plus } from "lucide-react"
import { useChatStore, NEW_CHAT_KEY } from "@/store/chat-store"
import { groupSessions } from "@/lib/group-sessions"
import { LumenMark } from "@/components/lumen-mark"
import { SidebarProfile } from "@/components/sidebar-profile"
import {
  Sidebar,
  SidebarHeader,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
} from "@/components/ui/sidebar"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

export function AppSidebar() {
  const sessions = useChatStore((s) => s.sessions)
  const activeSessionId = useChatStore((s) => s.activeSessionId)
  const setActiveSession = useChatStore((s) => s.setActiveSession)
  const activeStreams = useChatStore((s) => s.activeStreams)
  const isStreaming = activeStreams > 0

  const groups = groupSessions(sessions)

  const handleNewChat = () => {
    if (isStreaming) return
    useChatStore.setState((s) => ({
      activeSessionId: null,
      turnsBySession: { ...s.turnsBySession, [NEW_CHAT_KEY]: [] },
    }))
  }

  const handleSelectSession = (id: string) => {
    if (isStreaming) return
    setActiveSession(id)
  }

  const newChatButton = (
    <Button
      type="button"
      variant="outline"
      onClick={handleNewChat}
      disabled={isStreaming}
      aria-disabled={isStreaming}
      className={cn(
        "w-full justify-start gap-2 h-9 text-sm font-sans",
        isStreaming && "opacity-50 cursor-not-allowed",
      )}
    >
      <Plus className="size-4 shrink-0" />
      <span>New chat</span>
    </Button>
  )

  return (
    <Sidebar className="border-r border-sidebar-border bg-sidebar select-none">
      <SidebarHeader className="p-3 space-y-3">
        <div className="flex items-center gap-2 px-1">
          <LumenMark className="size-4 text-primary shrink-0" />
          <span className="font-heading text-base font-medium tracking-tighter text-sidebar-foreground">
            Lumen
          </span>
        </div>

        {isStreaming ? (
          <Tooltip>
            <TooltipTrigger render={<div>{newChatButton}</div>} />
            <TooltipContent side="right">
              Wait for the answer or press Stop.
            </TooltipContent>
          </Tooltip>
        ) : (
          newChatButton
        )}
      </SidebarHeader>

      <SidebarContent className="p-2">
        <ScrollArea className="h-full">
          {sessions.length === 0 ? (
            <div className="px-3 py-6 text-xs text-muted-foreground">
              No conversations yet.
            </div>
          ) : (
            <div className="space-y-4">
              {groups.map((group) => (
                <SidebarGroup key={group.label} className="p-0">
                  <SidebarGroupLabel className="px-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground/80 h-7">
                    {group.label}
                  </SidebarGroupLabel>
                  <SidebarGroupContent>
                    <SidebarMenu className="gap-0.5">
                      {group.sessions.map((session) => {
                        const isActive = session.id === activeSessionId
                        const rowContent = (
                          <SidebarMenuButton
                            isActive={isActive}
                            onClick={() => handleSelectSession(session.id)}
                            disabled={isStreaming}
                            aria-disabled={isStreaming}
                            className={cn(
                              "relative w-full justify-start text-left text-sm h-8 px-2.5 rounded-md transition-colors",
                              isActive
                                ? "bg-sidebar-accent font-medium text-sidebar-foreground"
                                : "text-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground",
                              isStreaming && "opacity-50 cursor-not-allowed",
                            )}
                          >
                            {isActive && (
                              <span className="absolute left-0 top-1.5 bottom-1.5 w-[2px] bg-primary rounded-full" />
                            )}
                            <span className="truncate w-full">{session.title}</span>
                          </SidebarMenuButton>
                        )

                        return (
                          <SidebarMenuItem key={session.id}>
                            {isStreaming ? (
                              <Tooltip>
                                <TooltipTrigger render={<div>{rowContent}</div>} />
                                <TooltipContent side="right">
                                  Wait for the answer or press Stop.
                                </TooltipContent>
                              </Tooltip>
                            ) : (
                              rowContent
                            )}
                          </SidebarMenuItem>
                        )
                      })}
                    </SidebarMenu>
                  </SidebarGroupContent>
                </SidebarGroup>
              ))}
            </div>
          )}
        </ScrollArea>
      </SidebarContent>

      <SidebarFooter className="p-2 border-t border-sidebar-border">
        <SidebarProfile />
      </SidebarFooter>
    </Sidebar>
  )
}
