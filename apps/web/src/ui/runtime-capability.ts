import canonical from '../../../../packages/contracts/ui.runtime_capabilities.v1.schema.json' with {type:'json'};
/** App-only UI capability policy. This is NOT producer readiness or a
 * browser authority token. The signed BFF must independently reject Send
 * before body read or durable reservation in app-only mode.
 *
 * Only an explicitly trusted private NO_DISPATCH_ONLY profile or a pinned
 * CI-only intercepted browser fixture can expose the Send button. Neither
 * mode permits an Answer, Qdrant, model or Gateway dispatch.
 */
export type RuntimeCapability=ReadOnlyCapability;
export type ReadOnlyCapability=Readonly<{
  kind:'ui_runtime_capabilities';
  contract_version:'ui.runtime_capabilities.v1';
  send_mode:'DISABLED'|'NO_DISPATCH_ONLY';
  engine_available:false;
  generation_available:false;
}>;

const disabled:ReadOnlyCapability={
  kind:'ui_runtime_capabilities',contract_version:'ui.runtime_capabilities.v1',
  send_mode:'DISABLED',engine_available:false,generation_available:false
};
export function blockedCapability():ReadOnlyCapability{return disabled;}
export function selectRuntimeCapability(input:{
  appOnly:boolean;
  approvedNoDispatch:boolean;
  ciFixture:boolean;
}):ReadOnlyCapability{
  return input.appOnly||!(input.approvedNoDispatch||input.ciFixture)
    ?disabled:{...disabled,send_mode:'NO_DISPATCH_ONLY'};
}
export function decodeRuntimeCapability(value:unknown):ReadOnlyCapability|null{
  if(value===null||typeof value!=='object'||Array.isArray(value))return null;
  const o=value as Record<string,unknown>;
  const properties=canonical.properties;
  if(Object.keys(o).sort().join('|')!==
       Object.keys(properties).sort().join('|')||
     o.kind!==properties.kind.const||
     o.contract_version!==properties.contract_version.const||
     typeof o.send_mode!=='string'||!properties.send_mode.enum.includes(o.send_mode)||
     o.engine_available!==properties.engine_available.const||
     o.generation_available!==properties.generation_available.const)return null;
  return o as ReadOnlyCapability;
}

/** A declared, unsupported deployment profile cannot silently authorize Send.
 * Absent profile retains the existing CI-private-history compatibility mode;
 * every explicit mode other than NO_DISPATCH_ONLY is send-disabled.
 */
export function appOnlySendBlocked(profile:string|undefined):boolean{
  return profile!==undefined&&profile!=='NO_DISPATCH_ONLY';
}
