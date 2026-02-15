import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  // Standalone output for Docker deployment (copies only needed files)
  output: 'standalone',
  // Vercel Pattern 2.1: Optimize package imports for lucide-react to avoid barrel imports
  experimental: {
    optimizePackageImports: ['lucide-react'],
  },
}

export default nextConfig
