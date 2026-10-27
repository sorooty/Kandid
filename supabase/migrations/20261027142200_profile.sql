CREATE TYPE "public"."search_type" AS ENUM('work_study', 'internship', 'student_job');--> statement-breakpoint
CREATE TABLE "profile" (
	"user_id" uuid PRIMARY KEY NOT NULL,
	"first_name" text NOT NULL,
	"search_type" "search_type" DEFAULT 'work_study' NOT NULL,
	"school" text,
	"start_date" date,
	"work_study_rhythm" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "profile_first_name_length" CHECK (char_length("profile"."first_name") between 1 and 50),
	CONSTRAINT "profile_school_length" CHECK (char_length("profile"."school") <= 120),
	CONSTRAINT "profile_work_study_rhythm_length" CHECK (char_length("profile"."work_study_rhythm") <= 80)
);
--> statement-breakpoint
ALTER TABLE "profile" ENABLE ROW LEVEL SECURITY;--> statement-breakpoint
ALTER TABLE "profile" ADD CONSTRAINT "profile_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
CREATE POLICY "profile_select_own" ON "profile" AS PERMISSIVE FOR SELECT TO "authenticated" USING ("profile"."user_id" = (select auth.uid()));--> statement-breakpoint
CREATE POLICY "profile_insert_own" ON "profile" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ("profile"."user_id" = (select auth.uid()));--> statement-breakpoint
CREATE POLICY "profile_update_own" ON "profile" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ("profile"."user_id" = (select auth.uid())) WITH CHECK ("profile"."user_id" = (select auth.uid()));