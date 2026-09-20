import LearningApp from './learning-app';
import {getChatGPTUser,chatGPTSignInPath} from './chatgpt-auth';
export const dynamic='force-dynamic';
export default async function Home(){const user=await getChatGPTUser();return <LearningApp signedIn={!!user} signInHref={chatGPTSignInPath('/')}/>;}
