import { client } from "./client/client.gen"

const DEFAULT_API_URL = "http://localhost:8000"

export function configureClient(): void {
  const baseUrl = import.meta.env.VITE_API_URL || DEFAULT_API_URL
  client.setConfig({
    baseUrl: baseUrl.replace(/\/$/, ""),
    throwOnError: true,
  })
}
