import { auth } from "@/auth"
import { SignJWT } from "jose"

export const dynamic = "force-dynamic"

export async function GET() {
  const session = await auth()
  if (!session?.user?.id) {
    return Response.json({ error: "Unauthorized" }, { status: 401, headers: { "Cache-Control": "no-store" } })
  }
  const secret = new TextEncoder().encode(process.env.BACKEND_JWT_SECRET!)
  const expiresIn = 300
  const token = await new SignJWT({ email: session.user.email ?? undefined })
    .setProtectedHeader({ alg: "HS256" })
    .setSubject(session.user.id)
    .setIssuer("lumen-frontend")
    .setAudience("lumen-backend")
    .setIssuedAt()
    .setExpirationTime(`${expiresIn}s`)
    .sign(secret)
  return Response.json({ token, expiresIn }, { headers: { "Cache-Control": "no-store" } })
}
