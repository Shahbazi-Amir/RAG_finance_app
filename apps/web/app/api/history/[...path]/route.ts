import type { NextRequest } from 'next/server';
import { forwardHistoryProxy } from '../../../../src/history/proxy.ts';

/**
 * Only this Next route exposes the tested CI-only History proxy core.
 * No client-selected upstream/user, Auth bypass or public deployment mode.
 */
export const dynamic='force-dynamic';
export async function GET(request:NextRequest,ctx:{params:Promise<{path:string[]}>}):Promise<Response>{
  return forwardHistoryProxy(request,(await ctx.params).path);
}
export async function POST(request:NextRequest,ctx:{params:Promise<{path:string[]}>}):Promise<Response>{
  return forwardHistoryProxy(request,(await ctx.params).path);
}
