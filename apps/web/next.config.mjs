/** @type {import('next').NextConfig} */
const apiGateway = process.env.API_GATEWAY_URL || "http://localhost:8080";
const agentService = process.env.AGENT_URL || "http://localhost:8000";

const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  async rewrites() {
    return [
      // Agent-owned APIs must be listed before the generic /api proxy.
      { source: "/api/agent/knowledge/:path*", destination: `${agentService}/api/v1/knowledge/:path*` },
      { source: "/api/agent/trends/:path*", destination: `${agentService}/api/v1/trends/:path*` },
      { source: "/api/agent/viral-videos/:path*", destination: `${agentService}/api/v1/viral-videos/:path*` },
      { source: "/api/agent/topic-recommendations/:path*", destination: `${agentService}/api/v1/topic-recommendations/:path*` },
      { source: "/api/agent/:path*", destination: `${agentService}/api/v1/agent/:path*` },
      { source: "/api/:path*", destination: `${apiGateway}/api/:path*` },
    ];
  },
};

export default nextConfig;
