import type { ReactNode } from "react";

export function Modal({
  open,
  title,
  children,
  onClose,
}: {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  if (!open) return null;
  return (
    <div className="modal-root" role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <button type="button" className="modal-backdrop" aria-label="Close" onClick={onClose} />
      <div className="modal-card">
        <h2 id="modal-title">{title}</h2>
        {children}
      </div>
    </div>
  );
}

export function Drawer({
  open,
  title,
  children,
  onClose,
}: {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  if (!open) return null;
  return (
    <div className="drawer-root" role="dialog" aria-modal="true" aria-labelledby="drawer-title">
      <button type="button" className="modal-backdrop" aria-label="Close" onClick={onClose} />
      <aside className="drawer-panel">
        <h2 id="drawer-title">{title}</h2>
        {children}
      </aside>
    </div>
  );
}
