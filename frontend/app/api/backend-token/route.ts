import { auth } from "@/auth"
import { SignJWT } from "jose"

export const dynamic = "force-dynamic"

export async function GET() {
  const session = await auth()
  if (!session?.user?.id) {
    return Response.json({ error: "Unauthorized" }, { status: 401, headers: { "Cache-Control": "no-store" } })
  }

  const secretKey = process.env.BACKEND_JWT_SECRET
  if (!secretKey) {
    console.error("[lumen] BACKEND_JWT_SECRET is not set in environment")
    return Response.json(
      { error: "BACKEND_JWT_SECRET is not set" },
      { status: 500, headers: { "Cache-Control": "no-store" } },
    )
  }

  const secret = new TextEncoder().encode(secretKey)
  const expiresIn = 300
  const now = Math.floor(Date.now() / 1000)
  const token = await new SignJWT({ email: session.user.email ?? undefined })
    .setProtectedHeader({ alg: "HS256" })
    .setSubject(session.user.id)
    .setIssuer("lumen-frontend")
    .setAudience("lumen-backend")
    .setIssuedAt(now - 60)
    .setExpirationTime(now + expiresIn)
    .sign(secret)

  return Response.json({ token, expiresIn }, { headers: { "Cache-Control": "no-store" } })
}
