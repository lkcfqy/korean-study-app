CREATE TABLE `lesson_progress` (
	`user_id` text NOT NULL,
	`lesson_id` text NOT NULL,
	`cursor` integer DEFAULT 0 NOT NULL,
	`read_mask` integer DEFAULT 0 NOT NULL,
	`completed_at` integer,
	`next_review_at` integer,
	`review_step` integer DEFAULT 0 NOT NULL,
	`updated_at` integer NOT NULL,
	`draft` text DEFAULT '' NOT NULL,
	`draft_revision` integer DEFAULT 0 NOT NULL,
	PRIMARY KEY(`user_id`, `lesson_id`)
);
