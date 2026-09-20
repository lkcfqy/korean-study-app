'use client';

import {Component,type ReactNode} from 'react';

export default class PlanBoundary extends Component<{children:ReactNode},{failed:boolean}> {
 state={failed:false};
 static getDerivedStateFromError(){return {failed:true};}
 render(){
  if(this.state.failed)return <div role="alert" className="error-state"><p>学习安排暂时未能加载。可以关闭此面板继续当前对话，稍后刷新页面重试。</p></div>;
  return this.props.children;
 }
}
