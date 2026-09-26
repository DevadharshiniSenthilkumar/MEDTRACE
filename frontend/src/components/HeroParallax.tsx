import { useEffect } from "react";
import { motion, useMotionValue, useSpring, useTransform, useScroll } from "framer-motion";
import { PillIcon, VialIcon, BlisterIcon } from "./icons";

const prefersReducedMotion =
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/**
 * Purely decorative. Renders behind the landing page's form (see
 * .hero-parallax z-index in pages.css) with pointer-events disabled at
 * every layer, so it can never intercept a click or cover the "Load
 * demo data" button / dropzone.
 */
export default function HeroParallax() {
  const mx = useMotionValue(0);
  const my = useMotionValue(0);
  const smx = useSpring(mx, { stiffness: 40, damping: 22, mass: 0.9 });
  const smy = useSpring(my, { stiffness: 40, damping: 22, mass: 0.9 });
  const { scrollY } = useScroll();

  useEffect(() => {
    if (prefersReducedMotion) return;
    function handleMove(e: PointerEvent) {
      mx.set((e.clientX / window.innerWidth - 0.5) * 2);
      my.set((e.clientY / window.innerHeight - 0.5) * 2);
    }
    window.addEventListener("pointermove", handleMove);
    return () => window.removeEventListener("pointermove", handleMove);
  }, [mx, my]);

  // Background layer: small mouse-parallax range, slow scroll range —
  // reads as "far away".
  const bgMouseX = useTransform(smx, [-1, 1], [-12, 12]);
  const bgMouseY = useTransform(smy, [-1, 1], [-9, 9]);
  const bgScrollY = useTransform(scrollY, [0, 500], [0, -26]);
  const bgY = useTransform([bgMouseY, bgScrollY], (v) => (v[0] as number) + (v[1] as number));

  // Midground layer: wider mouse-parallax range, faster scroll range —
  // reads as "closer".
  const mgMouseX = useTransform(smx, [-1, 1], [-32, 32]);
  const mgMouseY = useTransform(smy, [-1, 1], [-22, 22]);
  const mgScrollY = useTransform(scrollY, [0, 500], [0, -68]);
  const mgY = useTransform([mgMouseY, mgScrollY], (v) => (v[0] as number) + (v[1] as number));

  if (prefersReducedMotion) {
    return (
      <div className="hero-parallax" aria-hidden="true">
        <div className="hero-layer hero-layer-bg">
          <span className="hero-shape shape-a"><VialIcon size={120} /></span>
          <span className="hero-shape shape-b"><PillIcon size={90} /></span>
          <span className="hero-shape shape-e"><BlisterIcon size={64} /></span>
        </div>
        <div className="hero-layer hero-layer-mg">
          <span className="hero-shape shape-c"><PillIcon size={60} /></span>
          <span className="hero-shape shape-d"><VialIcon size={78} /></span>
        </div>
      </div>
    );
  }

  return (
    <div className="hero-parallax" aria-hidden="true">
      <motion.div className="hero-layer hero-layer-bg" style={{ x: bgMouseX, y: bgY }}>
        <span className="hero-shape shape-a drift-a"><VialIcon size={120} /></span>
        <span className="hero-shape shape-b drift-b"><PillIcon size={90} /></span>
        <span className="hero-shape shape-e drift-c"><BlisterIcon size={64} /></span>
      </motion.div>
      <motion.div className="hero-layer hero-layer-mg" style={{ x: mgMouseX, y: mgY }}>
        <span className="hero-shape shape-c drift-b"><PillIcon size={60} /></span>
        <span className="hero-shape shape-d drift-a"><VialIcon size={78} /></span>
      </motion.div>
    </div>
  );
}
