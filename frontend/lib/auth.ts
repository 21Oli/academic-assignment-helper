/** Auth helpers — token storage and guard utilities. */

export function saveToken(token: string) {
  if (typeof window !== "undefined") localStorage.setItem("access_token", token);
}

export function clearToken() {
  if (typeof window !== "undefined") localStorage.removeItem("access_token");
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

export function isLoggedIn(): boolean {
  return !!getToken();
}
