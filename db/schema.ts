import {integer,sqliteTable,text,primaryKey} from 'drizzle-orm/sqlite-core';
export const lessonProgress=sqliteTable('lesson_progress',{
 userId:text('user_id').notNull(),lessonId:text('lesson_id').notNull(),
 cursor:integer('cursor').notNull().default(0),readMask:integer('read_mask').notNull().default(0),
 completedAt:integer('completed_at'),nextReviewAt:integer('next_review_at'),
 reviewStep:integer('review_step').notNull().default(0),updatedAt:integer('updated_at').notNull(),
 draft:text('draft').notNull().default(''),draftRevision:integer('draft_revision').notNull().default(0),
},t=>[primaryKey({columns:[t.userId,t.lessonId]})]);
