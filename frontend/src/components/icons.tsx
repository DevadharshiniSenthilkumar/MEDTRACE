// Lightweight inline icon set — pill/vial/blister motifs plus a few
// utility glyphs, so the app has no external icon-font dependency.

export function PillIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <rect x="3" y="9" width="18" height="8" rx="4" stroke="currentColor" strokeWidth="1.8" />
      <line x1="12" y1="9" x2="12" y2="17" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

export function VialIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M9 3h6M10 3v5.5L5.5 15a3 3 0 0 0 2.6 4.5h7.8a3 3 0 0 0 2.6-4.5L14 8.5V3" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <line x1="7.5" y1="14.5" x2="16.5" y2="14.5" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

export function BlisterIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <circle cx="7" cy="7" r="3" stroke="currentColor" strokeWidth="1.8" />
      <circle cx="17" cy="7" r="3" stroke="currentColor" strokeWidth="1.8" />
      <circle cx="7" cy="17" r="3" stroke="currentColor" strokeWidth="1.8" />
      <circle cx="17" cy="17" r="3" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

export function DashboardIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <rect x="3" y="3" width="8" height="8" rx="2" stroke="currentColor" strokeWidth="1.8" />
      <rect x="13" y="3" width="8" height="5" rx="2" stroke="currentColor" strokeWidth="1.8" />
      <rect x="13" y="10" width="8" height="11" rx="2" stroke="currentColor" strokeWidth="1.8" />
      <rect x="3" y="13" width="8" height="8" rx="2" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

export function QueueIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <line x1="4" y1="6" x2="20" y2="6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <line x1="4" y1="12" x2="20" y2="12" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <line x1="4" y1="18" x2="14" y2="18" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

export function FacilityIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M4 21V8l8-5 8 5v13" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <line x1="12" y1="11" x2="12" y2="15" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <line x1="10" y1="13" x2="14" y2="13" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

export function MapIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2-6-2Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <line x1="9" y1="4" x2="9" y2="18" stroke="currentColor" strokeWidth="1.8" />
      <line x1="15" y1="6" x2="15" y2="20" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

export function RootCauseIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="6" r="2.4" stroke="currentColor" strokeWidth="1.8" />
      <path d="M12 8.4V13M12 13l-5 5M12 13l5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

export function HistoryIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="8.5" stroke="currentColor" strokeWidth="1.8" />
      <path d="M12 7.5V12l3 2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function ShieldIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M12 3.5 5 6.2v5.4c0 4.6 3 7.9 7 9 4-1.1 7-4.4 7-9V6.2L12 3.5Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M9 12.3l2 2 4-4.3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function UploadIcon({ size = 18 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M12 15V4M8 8l4-4 4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}
