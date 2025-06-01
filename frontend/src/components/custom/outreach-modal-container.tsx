import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";

interface ModalContainerProps {
  isOpen: boolean;
  children: React.ReactNode;
}

export function OutreachModalContainer({
  isOpen,
  children,
}: ModalContainerProps) {
  const [particles, setParticles] = useState<
    Array<{ id: number; x: number; y: number }>
  >([]);

  // Generate entrance particles
  useEffect(() => {
    if (isOpen) {
      const newParticles = Array.from({ length: 20 }, (_, i) => ({
        id: i,
        x: Math.random() * window.innerWidth,
        y: Math.random() * window.innerHeight,
      }));
      setParticles(newParticles);
    }
  }, [isOpen]);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop with blur */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
          />

          {/* Particle effects */}
          {particles.map((particle) => (
            <motion.div
              key={particle.id}
              className="fixed w-2 h-2 bg-gradient-to-r from-blue-400 to-purple-400 rounded-full z-50"
              initial={{
                x: particle.x,
                y: particle.y,
                scale: 0,
                opacity: 0,
              }}
              animate={{
                x: window.innerWidth / 2,
                y: window.innerHeight / 2,
                scale: [0, 1.5, 0],
                opacity: [0, 1, 0],
              }}
              transition={{
                duration: 1,
                delay: particle.id * 0.02,
              }}
            />
          ))}

          {/* 3D Modal */}
          <motion.div
            className="fixed inset-0 flex items-center justify-center z-50 perspective-1000"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              initial={{
                scale: 0.7,
                rotateX: -45,
                rotateY: 45,
                opacity: 0,
              }}
              animate={{
                scale: 1,
                rotateX: 0,
                rotateY: 0,
                opacity: 1,
              }}
              exit={{
                scale: 0.7,
                rotateX: 45,
                rotateY: -45,
                opacity: 0,
              }}
              transition={{
                type: "spring",
                damping: 20,
                stiffness: 300,
              }}
              style={{
                transformStyle: "preserve-3d",
              }}
              className="w-full max-w-4xl"
            >
              {children}
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
