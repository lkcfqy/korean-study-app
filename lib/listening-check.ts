import {z} from 'zod';

// These describe a practice attempt, not a certified proficiency score.
export const listeningCheckSchema=z.object({
 firstAnswers:z.tuple([z.number().int().min(0).max(2),z.number().int().min(0).max(2)]),
 heard:z.tuple([z.boolean(),z.boolean()]),
 hints:z.tuple([z.boolean(),z.boolean()]),
});
export type ListeningCheck=z.infer<typeof listeningCheckSchema>;
export function independentAnswers(check:ListeningCheck,answers:number[]){
 return answers.filter((answer,i)=>check.firstAnswers[i]===answer&&check.heard[i]&&!check.hints[i]).length;
}
