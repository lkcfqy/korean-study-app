export function learningError(error:unknown,fallback:string):string{
 if(error instanceof Error){
  if(error.name==='TimeoutError'||error.name==='AbortError')return '网络响应较慢，请重试。';
  if(error.name==='TypeError')return '网络连接中断，请检查连接后重试。';
  if(error.name==='ZodError')return '收到的数据与当前课程不一致，请刷新页面后重试。';
  return error.message;
 }
 return fallback;
}
