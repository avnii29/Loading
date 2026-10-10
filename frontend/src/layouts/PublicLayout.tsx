import type { ReactNode } from "react";
import { PublicNav } from "../components/nav/PublicNav";

export function PublicLayout({ children }: { children: ReactNode }) {
  return (
    <div className="public-page">
      <PublicNav />
      {children}
      <footer className="public-footer">
        <div className="wrap">
          <p>Anuvarthan · Pass It Forward.</p>
        </div>
      </footer>
    </div>
  );
}
