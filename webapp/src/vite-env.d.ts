/// <reference types="vite/client" />

declare module '*.css' {
  const content: string;
  export default content;
}

declare module 'motion/react' {
  export { motion, AnimatePresence } from 'framer-motion';
}
