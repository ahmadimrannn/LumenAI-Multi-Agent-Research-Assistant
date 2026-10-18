"use client"
import { useSession, signOut } from "next-auth/react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
} from "@/components/ui/sidebar"
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar"

function getInitials(name?: string | null, email?: string | null): string {
  if (name && name.trim()) {
    const parts = name.trim().split(/\s+/).filter(Boolean)
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
    }
    return parts[0].slice(0, 2).toUpperCase()
  }
  if (email && email.trim()) {
    return email.trim()[0].toUpperCase()
  }
  return "U"
}

export function SidebarProfile() {
  const { data: session } = useSession()
  if (!session?.user) return null

  const { name, email, image } = session.user
  const initials = getInitials(name, email)

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger
            render={
              <SidebarMenuButton
                size="lg"
                className="w-full flex items-center gap-3 px-2 py-1.5 text-left h-auto data-open:bg-sidebar-accent"
              />
            }
          >
            <Avatar className="size-8 rounded-full shrink-0">
              {image ? (
                <AvatarImage
                  src={image}
                  referrerPolicy="no-referrer"
                  alt={name ?? "User avatar"}
                />
              ) : null}
              <AvatarFallback className="text-xs font-medium">{initials}</AvatarFallback>
            </Avatar>
            <div className="flex flex-col min-w-0 flex-1 leading-tight">
              <span className="truncate text-sm font-medium text-sidebar-foreground">
                {name || "User"}
              </span>
              <span className="truncate text-xs text-muted-foreground">
                {email}
              </span>
            </div>
          </DropdownMenuTrigger>
          <DropdownMenuContent side="top" align="start" className="w-56">
            <DropdownMenuItem onClick={() => signOut({ redirectTo: "/" })}>
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarMenuItem>
    </SidebarMenu>
  )
}
