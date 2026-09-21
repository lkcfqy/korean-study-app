import assert from 'node:assert/strict';
import {test} from 'node:test';
import {AudioPlayback} from '../lib/audio-playback.ts';

function fixture(timeout=20){
 const states=[],players=[],finished=[];
 const controller=new AudioPlayback(state=>states.push(state),path=>{
  let resolve,reject;
  const player={path,ended:false,readyState:0,playbackRate:1,preservesPitch:false,pauses:0,
   play:()=>new Promise((yes,no)=>{resolve=yes;reject=no;}),pause(){this.pauses++;},
   resolve(){resolve();},reject(){reject(new Error('Media failed'));}};
  players.push(player);return player;
 },timeout);
 return {controller,states,players,finished};
}
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));

test('normal completion counts listening exactly once and preserves slowed pitch',async()=>{
 const f=fixture();const playing=f.controller.play('/one.mp3',.8,value=>f.finished.push(value));const p=f.players[0];
 assert.equal(f.states.at(-1).phase,'loading');assert.equal(p.playbackRate,.8);assert.equal(p.preservesPitch,true);
 p.resolve();await playing;assert.equal(f.states.at(-1).phase,'playing');
 const ended=p.onended;ended();ended();assert.deepEqual(f.finished,[true]);assert.equal(f.states.at(-1).phase,'idle');
});
test('a newer word cancels an older pending play and ignores its late events',async()=>{
 const f=fixture();const a=f.controller.play('/old.mp3',1,value=>f.finished.push(['old',value]));const old=f.players[0];const stale=old.onended;
 const b=f.controller.play('/new.mp3',1,value=>f.finished.push(['new',value]));const current=f.players[1];
 old.resolve();await a;stale();assert.equal(f.states.at(-1).phase,'loading');assert.deepEqual(f.finished,[['old',false]]);
 current.resolve();await b;current.onended();assert.deepEqual(f.finished,[['old',false],['new',true]]);
});
test('media error and rejected play promise cannot report completion twice',async()=>{
 const f=fixture();const result=f.controller.play('/missing.mp3',1,value=>f.finished.push(value));const p=f.players[0];
 p.onerror();p.reject();await result;assert.deepEqual(f.finished,[false]);assert.deepEqual(f.states.at(-1),{phase:'error',reason:'load'});
});
test('a stalled initial request times out and allows immediate retry',async()=>{
 const f=fixture();void f.controller.play('/stalled.mp3',1,value=>f.finished.push(value));const first=f.players[0];
 await delay(35);assert.deepEqual(f.finished,[false]);assert.equal(first.pauses,1);assert.equal(f.states.at(-1).reason,'timeout');
 const retry=f.controller.play('/retry.mp3',1,value=>f.finished.push(value));f.players[1].resolve();await retry;f.players[1].onended();assert.deepEqual(f.finished,[false,true]);
});
test('a buffering interruption is bounded and never counts as heard',async()=>{
 const f=fixture();const result=f.controller.play('/buffer.mp3',1,value=>f.finished.push(value));const p=f.players[0];p.resolve();await result;
 p.onwaiting();await delay(35);assert.deepEqual(f.finished,[false]);assert.equal(f.states.at(-1).reason,'timeout');
});
test('recovery from buffering cancels the deadline without capping audio length',async()=>{
 const f=fixture();const result=f.controller.play('/long.mp3',1,value=>f.finished.push(value));const p=f.players[0];p.resolve();await result;
 p.onwaiting();p.onplaying();await delay(35);assert.deepEqual(f.finished,[]);assert.equal(f.states.at(-1).phase,'playing');
 f.controller.setRate(.8);assert.equal(p.playbackRate,.8);p.onended();assert.deepEqual(f.finished,[true]);
});
test('navigation stops playback and releases media handlers',async()=>{
 const f=fixture();const result=f.controller.play('/one.mp3',1,value=>f.finished.push(value));const p=f.players[0];p.resolve();await result;
 f.controller.stop();f.controller.stop();assert.deepEqual(f.finished,[false]);assert.equal(p.onended,null);assert.equal(p.onerror,null);assert.equal(p.onwaiting,null);
});
