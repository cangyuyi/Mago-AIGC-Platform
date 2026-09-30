"use client";
import { Card } from "@/components/ui/card";
import { Settings as SettingsIcon } from "lucide-react";

export default function SettingsPage() {
  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">设置</h1>
      <p className="text-sm text-muted-foreground mb-8">账号设置、API配置、偏好设置</p>
      <Card className="p-6 opacity-60">
        <SettingsIcon className="w-8 h-8 text-primary mb-3" />
        <h3 className="font-semibold mb-1">设置页面</h3>
        <p className="text-sm text-muted-foreground">🚧 开发中</p>
      </Card>
    </div>
  );
}
