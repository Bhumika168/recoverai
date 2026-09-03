"use client";

import React, { useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { Navbar } from "@/components/Navbar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [refreshKey, setRefreshKey] = useState(0);

  const handleDataRefresh = () => {
    setRefreshKey((prev) => prev + 1);
  };

  return (
    <div className="flex min-h-screen bg-background text-ivory">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Navbar onDataRefresh={handleDataRefresh} />
        <main key={refreshKey} className="flex-1 p-8 overflow-y-auto max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
