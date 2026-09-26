import { VialIcon } from "./icons";

export function LoadingView({ label = "Loading" }: { label?: string }) {
  return (
    <div className="state-view">
      <span className="spinner-caps" aria-hidden="true">
        <span />
        <span />
        <span />
      </span>
      <p>{label}…</p>
    </div>
  );
}

export function ErrorView({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="state-view">
      <h3>Couldn't load this</h3>
      <p>{message}</p>
      {onRetry && (
        <button className="btn btn-ghost" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

export function EmptyView({
  title,
  message,
}: {
  title: string;
  message: string;
}) {
  return (
    <div className="state-view">
      <VialIcon size={30} />
      <h3>{title}</h3>
      <p>{message}</p>
    </div>
  );
}
