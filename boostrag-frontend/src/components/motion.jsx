import { motion, useReducedMotion } from "framer-motion";
import { tokens } from "../theme/tokens";

export function Swell({ children, className = "" }) {
  const still = useReducedMotion();
  return (
    <motion.span className={`inline-block ${className}`}
      whileHover={still ? undefined : { scale: tokens.motion.swellScale }}
      transition={{ type: "spring", stiffness: 400, damping: 22 }}>
      {children}
    </motion.span>
  );
}

export function Reveal({ children, className = "" }) {
  const still = useReducedMotion();
  return (
    <motion.div className={className}
      initial={still ? false : { opacity: 0, y: tokens.motion.revealRise }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: tokens.motion.revealMs / 1000 }}>
      {children}
    </motion.div>
  );
}
