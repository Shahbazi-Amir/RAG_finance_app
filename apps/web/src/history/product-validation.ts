/**
 * Consumer-side interpreter of the CHECKED-IN product.v1 JSON Schema.
 * No copied field registry or alternate product DTO.
 *
 * Supports the Draft 2020-12 vocabulary used by the consumed definitions:
 * $ref/$defs, object required/properties/additionalProperties, arrays,
 * numbers, strings/pattern/length/date-time, oneOf/anyOf/allOf/if/then/not.
 * This is NOT a general-purpose JSON Schema engine or authentication check.
 * Domain-level cross-object invariants are separately enforced in client.ts.
 */
import productContract from '../../../../packages/contracts/product.v1.schema.json' with { type: 'json' };

type Schema = Record<string,unknown>;
const registry=(productContract as unknown as {$defs:Record<string,Schema>}).$defs;
const own=(o:Record<string,unknown>,k:string)=>Object.prototype.hasOwnProperty.call(o,k);
const obj=(v:unknown):v is Record<string,unknown>=>
  v!==null&&typeof v==='object'&&!Array.isArray(v);
const node=(v:unknown):Schema=>obj(v)?v:{};
const array=(v:unknown):unknown[]=>Array.isArray(v)?v:[];

function matches(value:unknown,s:Schema,depth=0):boolean{
  if(depth>32)return false;
  const each=(v:unknown,part:unknown)=>matches(v,node(part),depth+1);
  if(typeof s.$ref==='string'){
    const ref=s.$ref;
    if(!ref.startsWith('#/$defs/')||!own(registry,ref.slice(8))||
       !each(value,registry[ref.slice(8)]))return false;
  }
  if(own(s,'const')&&value!==s.const)return false;
  if(Array.isArray(s.enum)&&!s.enum.some(x=>x===value))return false;
  if(typeof s.type==='string'){
    const type=s.type;
    if(!(type==='null'?value===null:
         type==='object'?obj(value):
         type==='array'?Array.isArray(value):
         type==='integer'?typeof value==='number'&&Number.isSafeInteger(value):
         type==='number'?typeof value==='number'&&Number.isFinite(value):
         typeof value===type))return false;
  }
  if(Array.isArray(s.oneOf)&&s.oneOf.filter(part=>each(value,part)).length!==1)return false;
  if(Array.isArray(s.anyOf)&&!s.anyOf.some(part=>each(value,part)))return false;
  if(Array.isArray(s.allOf)&&!s.allOf.every(part=>each(value,part)))return false;
  if(own(s,'not')&&each(value,s.not))return false;
  if(own(s,'if')&&each(value,s.if)&&own(s,'then')&&!each(value,s.then))return false;
  if(typeof value==='string'){
    const n=Array.from(value).length;
    if(typeof s.minLength==='number'&&n<s.minLength)return false;
    if(typeof s.maxLength==='number'&&n>s.maxLength)return false;
    if(typeof s.pattern==='string'&&!new RegExp(s.pattern,'u').test(value))return false;
    if(s.format==='date-time'&&
       (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(value)||
        !Number.isFinite(Date.parse(value))))return false;
  }
  if(typeof value==='number'){
    if(typeof s.minimum==='number'&&value<s.minimum)return false;
    if(typeof s.maximum==='number'&&value>s.maximum)return false;
  }
  if(Array.isArray(value)){
    if(typeof s.minItems==='number'&&value.length<s.minItems)return false;
    if(typeof s.maxItems==='number'&&value.length>s.maxItems)return false;
    if(s.uniqueItems===true&&new Set(value.map(x=>JSON.stringify(x))).size!==value.length)return false;
    if(own(s,'items')&&!value.every(v=>each(v,s.items)))return false;
  }
  if(obj(value)){
    if(Array.isArray(s.required)&&!s.required.every(k=>typeof k==='string'&&own(value,k)))return false;
    const properties=node(s.properties);
    if(s.additionalProperties===false&&Object.keys(value).some(k=>!own(properties,k)))return false;
    if(Object.entries(properties).some(([k,def])=>own(value,k)&&!each(value[k],def)))return false;
  }
  return true;
}
export function conformsToProductV1(value:unknown,kind:string):boolean{
  const definition=registry[kind];
  return !!definition&&obj(value)&&value.kind===kind&&
    value.contract_version==='product.v1'&&matches(value,definition);
}
