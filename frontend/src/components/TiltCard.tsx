import { useRef, useState, type ReactNode, type CSSProperties } from "react";
import { motion, useSpring, useMotionValue, useTransform } from "framer-motion";

interface TiltCardProps {
  children: ReactNode;
  className?: string;
  /** Set true for cards whose primary job is fast-scanning text/data —
   *  tilt is disabled so reading isn't destabilized. */
  flat?: boolean;
  style?: CSSProperties;
  onClick?: () => void;
}

const prefersReducedMotion =
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

export default function TiltCard({
  children,
  className = "",
  flat = false,
  style,
  onClick,
}: TiltCardProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [hovering, setHovering] = useState(false);

  const x = useMotionValue(0.5);
  const y = useMotionValue(0.5);
  const springCfg = { stiffness: 220, damping: 20, mass: 0.6 };
  const rotateX = useSpring(useTransform(y, [0, 1], [8, -8]), springCfg);
  const rotateY = useSpring(useTransform(x, [0, 1], [-8, 8]), springCfg);
  const lift = useSpring(hovering && !flat ? -6 : 0, springCfg);

  const disableTilt = flat || prefersReducedMotion;

  function handleMove(e: React.PointerEvent<HTMLDivElement>) {
    if (disableTilt || !ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    x.set((e.clientX - rect.left) / rect.width);
    y.set((e.clientY - rect.top) / rect.height);
  }

  function handleLeave() {
    setHovering(false);
    x.set(0.5);
    y.set(0.5);
  }

  return (
    <div className="tilt-card-wrap">
      <motion.div
        ref={ref}
        className={`tilt-card ${flat ? "flat" : ""} ${className}`}
        style={{
          ...style,
          rotateX: disableTilt ? 0 : rotateX,
          rotateY: disableTilt ? 0 : rotateY,
          y: lift,
        }}
        onPointerMove={handleMove}
        onPointerEnter={() => setHovering(true)}
        onPointerLeave={handleLeave}
        onClick={onClick}
      >
        <div className="tilt-card-inner">{children}</div>
      </motion.div>
    </div>
  );
}
