import { defineConfig } from "@hey-api/openapi-ts"

export default defineConfig({
  input: "./openapi.json",
  output: "./src/client",
  plugins: [
    {
      name: "@hey-api/sdk",
      asClass: true,
      operationId: true,
      classNameBuilder: "{{name}}Service",
      methodNameBuilder: (operation) => {
        const descriptor = operation as {
          id?: string
          name?: string
          service?: string
          operation?: {
            id?: string
            tags?: string[]
          }
        }
        const rawName =
          descriptor.operation?.id || descriptor.id || descriptor.name
        const service = descriptor.service || descriptor.operation?.tags?.[0]

        let name = rawName || "call"

        if (service) {
          const capitalizedService =
            service.charAt(0).toUpperCase() + service.slice(1)

          if (name.toLowerCase().startsWith(service.toLowerCase())) {
            name = name.slice(service.length)
          } else if (name.startsWith(capitalizedService)) {
            name = name.slice(capitalizedService.length)
          }
        }

        return name.charAt(0).toLowerCase() + name.slice(1)
      },
    },
    {
      name: "@hey-api/schemas",
      type: "json",
    },
  ],
})
