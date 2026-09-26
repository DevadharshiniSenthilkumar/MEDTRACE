import { ShieldIcon } from "./icons";

export default function ApprovalBanner({
  text = "Officer approval required — MedTrace recommends, it never authorizes or moves stock automatically.",
}: {
  text?: string;
}) {
  return (
    <div className="approval-banner">
      <ShieldIcon size={18} />
      <span>{text}</span>
    </div>
  );
}
