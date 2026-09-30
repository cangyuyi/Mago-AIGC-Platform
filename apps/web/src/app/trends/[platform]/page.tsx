"use client";
import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import TrendsPage from "../page";

export default function PlatformTrendsPage() {
  const params = useParams();
  const router = useRouter();
  const platform = params.platform as string;

  useEffect(() => {
    router.replace(`/trends?platform=${platform}`);
  }, [platform, router]);

  return <TrendsPage />;
}
