/** Ephemeral owner boundary for separately issued authenticated responses.
 * Never accepts an owner from a URL, query, localStorage or untrusted request.
 * Browser response owners come exclusively from strictly validated BFF pages.
 * Any mismatch requires a new signed session; never silently rebind.
 */
export class OwnerFence {
  #owner:string|null=null;
  #revision=0;
  observe(owner:string):boolean {
    if(typeof owner!=='string'||!owner)return false;
    if(this.#owner===null){this.#owner=owner;return true;}
    return this.#owner===owner;
  }
  invalidate():void{this.#owner=null;this.#revision++;}
  capture():number{return this.#revision;}
  current(revision:number):boolean{return this.#revision===revision;}
}


/** An in-flight POST receipt or transport error is UI-observable only if
 * BOTH the signed owner generation and read-only owner revalidation epoch
 * have remained stable since dispatch. This never authorizes any POST. */
export function sameOwnerPrivacyEpoch(
  fence:OwnerFence,ownerRevision:number,privacyAtStart:number,privacyNow:number
):boolean {
  return Number.isSafeInteger(privacyAtStart)&&privacyAtStart>=0&&
    Number.isSafeInteger(privacyNow)&&privacyNow>=0&&
    privacyAtStart===privacyNow&&fence.current(ownerRevision);
}
