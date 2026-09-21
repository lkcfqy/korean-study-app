import { z } from "zod";
import contrastLessons from "../content/contrast-lessons.json" with { type: "json" };

// These describe a practice attempt, not a certified proficiency score.
export const choiceCheckSchema = z.object({
  mode: z.literal("choice").optional(),
  firstAnswers: z.tuple([
    z.number().int().min(0).max(2),
    z.number().int().min(0).max(2),
  ]),
  heard: z.tuple([z.boolean(), z.boolean()]),
  hints: z.tuple([z.boolean(), z.boolean()]),
});
export const recallCheckSchema = z.object({
  mode: z.literal("recall"),
  recalled: z.tuple([z.boolean(), z.boolean()]),
  heard: z.tuple([z.boolean(), z.boolean()]),
  hints: z.tuple([z.boolean(), z.boolean()]),
});
export const listeningCheckSchema = z.union([
  choiceCheckSchema,
  recallCheckSchema,
]);
export type ChoiceCheck = z.infer<typeof choiceCheckSchema>;
export type RecallCheck = z.infer<typeof recallCheckSchema>;
export type ListeningCheck = z.infer<typeof listeningCheckSchema>;
export const hasContrastQuestions = (id: string) =>
  contrastLessons.includes(id);
// For recall this is a SELF-RATING used for scheduling, never an objective score.
export function independentAnswers(check: ListeningCheck, answers: number[]) {
  return answers.filter(
    (answer, i) =>
      (check.mode === "recall"
        ? check.recalled[i]
        : check.firstAnswers[i] === answer) &&
      check.heard[i] &&
      !check.hints[i],
  ).length;
}
