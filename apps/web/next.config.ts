import path from 'node:path';
import type { NextConfig } from 'next';
const config: NextConfig = {
  turbopack: { root: path.resolve(process.cwd(), '../..') },
  reactStrictMode: true,
  poweredByHeader: false
};
export default config;
