import { ArrowUpRight, CreditCard, Plus, Tags } from "lucide-react"

import { SidebarAppearance } from "@/components/Common/Appearance"
import { Logo } from "@/components/Common/Logo"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
} from "@/components/ui/sidebar"
import { type Item, Main } from "./Main"

const items: Item[] = [
  { icon: CreditCard, title: "Accounts", path: "/accounts" },
  { icon: ArrowUpRight, title: "Transactions", path: "/transactions" },
  { icon: Tags, title: "Categories", path: "/categories" },
  { icon: Plus, title: "New account", path: "/accounts/new" },
]

export function AppSidebar() {
  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="px-4 py-6 group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:items-center">
        <Logo variant="responsive" />
      </SidebarHeader>
      <SidebarContent>
        <Main items={items} />
      </SidebarContent>
      <SidebarFooter>
        <SidebarAppearance />
      </SidebarFooter>
    </Sidebar>
  )
}

export default AppSidebar
