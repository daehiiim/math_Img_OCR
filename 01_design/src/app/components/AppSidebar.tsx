import { Link, useLocation } from "react-router";
import {
  LayoutDashboard,
  Upload,
  FileText,
  Cpu,
  BookOpen,
  ChevronRight,
} from "lucide-react";
import { cn } from "./ui/utils";

const navItems = [
  { path: "/", label: "대시보드", icon: LayoutDashboard },
  { path: "/new", label: "새 작업", icon: Upload },
];

const docItems = [
  { label: "API 명세", desc: "/docs (Swagger)" },
  { label: "파이프라인 흐름", desc: "Job → Region → Run → Export" },
  { label: "테스트", desc: "pytest -q tests/" },
];

export function AppSidebar() {
  const location = useLocation();

  return (
    <aside className="w-64 min-h-screen bg-card border-r border-border flex flex-col">
      {/* Logo */}
      <div className="p-5 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <Cpu className="w-4 h-4 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-[15px]">Math OCR</h1>
            
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3">
        <p className="text-[11px] text-muted-foreground px-3 mb-2 uppercase tracking-wider">
          메인
        </p>
        <ul className="space-y-0.5">
          {navItems.map((item) => {
            const isActive =
              item.path === "/"
                ? location.pathname === "/"
                : location.pathname.startsWith(item.path);
            return (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={cn(
                    "flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground"
                  )}
                >
                  <item.icon className="w-4 h-4" />
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>

        
        <ul className="space-y-0.5">
          {docItems.map((item) => (
            <li key={item.label}>
              
            </li>
          ))}
        </ul>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-border">
        
      </div>
    </aside>
  );
}
