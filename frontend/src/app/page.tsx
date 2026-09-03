"use client";

import React from "react";
import { motion, useScroll, useSpring } from "framer-motion";
import { LandingNav } from "@/components/landing/LandingNav";
import { HeroSection } from "@/components/landing/HeroSection";
import { ProblemSection } from "@/components/landing/ProblemSection";
import { ProductStatementSection } from "@/components/landing/ProductStatementSection";
import { WorkflowSequenceSection } from "@/components/landing/WorkflowSequenceSection";
import { AIDecisionInspectionSection } from "@/components/landing/AIDecisionInspectionSection";
import { WhenNotToActSection } from "@/components/landing/WhenNotToActSection";
import { RecoveryIntelligenceMatrix } from "@/components/landing/RecoveryIntelligenceMatrix";
import { InteractiveSimulationDemo } from "@/components/landing/InteractiveSimulationDemo";
import { RevenueMetricsSection } from "@/components/landing/RevenueMetricsSection";
import { DashboardPreviewSection } from "@/components/landing/DashboardPreviewSection";
import { AuditTrailSection } from "@/components/landing/AuditTrailSection";
import { ArchitectureFlowSection } from "@/components/landing/ArchitectureFlowSection";
import { FailureHandlingSection } from "@/components/landing/FailureHandlingSection";
import { FinalCTASection, LandingFooter } from "@/components/landing/FinalCTASection";

const sectionScrollReveal = {
  initial: { opacity: 0, y: 35 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-70px" },
  transition: {
    type: "spring" as const,
    stiffness: 90,
    damping: 20,
    mass: 0.8,
  },
};

export default function MarketingLandingPage() {
  // Fixed right-side scroll progress tracking
  const { scrollYProgress } = useScroll();
  const scaleY = useSpring(scrollYProgress, {
    stiffness: 100,
    damping: 30,
    restDelta: 0.001,
  });

  return (
    <div className="min-h-screen bg-[#070706] text-[#F5F0E8] selection:bg-[#D79A43]/30 selection:text-[#F5F0E8] relative">
      {/* 10. Fixed Right-Side Subtle Gold Scroll Progress Indicator (2px) */}
      <div className="fixed top-0 right-0 bottom-0 w-[2px] bg-white/[0.04] z-50 pointer-events-none hidden sm:block">
        <motion.div
          style={{ scaleY, transformOrigin: "top" }}
          className="w-full h-full bg-gradient-to-b from-[#D79A43] to-[#20B89A] opacity-70"
        />
      </div>

      {/* Navigation */}
      <LandingNav />

      {/* Orchestrated Staggered Hero */}
      <HeroSection />

      {/* Scroll-Driven Progressive Storytelling Sections */}
      <main className="space-y-0">
        <motion.div {...sectionScrollReveal}>
          <ProblemSection />
        </motion.div>

        <motion.div {...sectionScrollReveal}>
          <ProductStatementSection />
        </motion.div>

        <motion.div {...sectionScrollReveal}>
          <WorkflowSequenceSection />
        </motion.div>

        <motion.div {...sectionScrollReveal}>
          <AIDecisionInspectionSection />
        </motion.div>

        <motion.div {...sectionScrollReveal}>
          <WhenNotToActSection />
        </motion.div>

        <motion.div {...sectionScrollReveal}>
          <RecoveryIntelligenceMatrix />
        </motion.div>

        <motion.div {...sectionScrollReveal}>
          <InteractiveSimulationDemo />
        </motion.div>

        <motion.div {...sectionScrollReveal}>
          <RevenueMetricsSection />
        </motion.div>

        <motion.div {...sectionScrollReveal}>
          <DashboardPreviewSection />
        </motion.div>

        <motion.div {...sectionScrollReveal}>
          <AuditTrailSection />
        </motion.div>

        <motion.div {...sectionScrollReveal}>
          <ArchitectureFlowSection />
        </motion.div>

        <motion.div {...sectionScrollReveal}>
          <FailureHandlingSection />
        </motion.div>

        <motion.div {...sectionScrollReveal}>
          <FinalCTASection />
        </motion.div>
      </main>

      {/* Footer */}
      <LandingFooter />
    </div>
  );
}
