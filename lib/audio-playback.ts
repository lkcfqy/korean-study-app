export type PlaybackState = {phase:'idle'|'loading'|'playing'|'error'; reason?:'load'|'play'|'timeout'};
type Player = Pick<HTMLAudioElement,'play'|'pause'|'playbackRate'|'preservesPitch'|'ended'|'readyState'|'onended'|'onerror'|'onplaying'|'onwaiting'|'onstalled'>;

/** One active sound, one completion callback, and a bounded buffering wait. */
export class AudioPlayback {
 private active:{path:string;player:Player;finish:(completed:boolean,reason?:PlaybackState['reason'])=>void}|null=null;
 private notify:(state:PlaybackState)=>void;
 private factory:(path:string)=>Player;
 private timeoutMs:number;
 constructor(notify:(state:PlaybackState)=>void,factory:(path:string)=>Player=path=>new Audio(path),timeoutMs=20000){
  this.notify=notify;this.factory=factory;this.timeoutMs=timeoutMs;
 }
 get activePath(){return this.active?.path??null;}
 stop(){
  if(this.active)this.active.finish(false);
  else this.notify({phase:'idle'});
 }
 setRate(rate:number){if(this.active)this.active.player.playbackRate=rate;}
 async play(path:string,rate:number,onFinished?:(completed:boolean)=>void){
  this.stop();
  let player:Player;
  try{player=this.factory(path);}catch{this.notify({phase:'error',reason:'play'});onFinished?.(false);return;}
  let settled=false;
  let deadline:ReturnType<typeof setTimeout>|undefined;
  const clearDeadline=()=>{if(deadline!==undefined)clearTimeout(deadline);deadline=undefined;};
  const finish=(completed:boolean,reason?:PlaybackState['reason'])=>{
   if(settled)return;settled=true;clearDeadline();
   player.onended=player.onerror=player.onplaying=player.onwaiting=player.onstalled=null;
   if(!completed)player.pause();
   if(this.active?.player===player){this.active=null;this.notify(reason?{phase:'error',reason}:{phase:'idle'});}
   onFinished?.(completed);
  };
  const buffering=()=>{
   if(settled)return;
   this.notify({phase:'loading'});
   if(deadline===undefined)deadline=setTimeout(()=>finish(false,'timeout'),this.timeoutMs);
  };
  const playing=()=>{if(!settled){clearDeadline();this.notify({phase:'playing'});}};
  this.active={path,player,finish};
  player.playbackRate=rate;player.preservesPitch=true;
  player.onended=()=>finish(true);
  player.onerror=()=>finish(false,'load');
  player.onplaying=playing;player.onwaiting=buffering;
  player.onstalled=()=>{if(player.readyState<3)buffering();};
  buffering();
  try{await player.play();if(!player.ended)playing();}
  catch{finish(false,'play');}
 }
}
