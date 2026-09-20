export function reviewSourceDays(day:number):number[][]{
 const recent=day%5?[day-1]:Array.from({length:Math.min(4,day-1)},(_,i)=>day-Math.min(4,day-1)+i);
 return [recent,[day-7],[day-30]];
}
