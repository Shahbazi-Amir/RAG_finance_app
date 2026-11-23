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
