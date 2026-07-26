-- Add ownership to legacy PostgreSQL course/task rows.
--
-- Review and run this migration manually. The NULL checks below intentionally
-- stop the migration until every existing row has an explicit owner.

ALTER TABLE courses
    ADD COLUMN IF NOT EXISTS user_id BIGINT REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS user_id BIGINT REFERENCES users(id) ON DELETE CASCADE;

-- Set the owner explicitly before continuing, for example:
-- UPDATE courses SET user_id = <owner_user_id> WHERE user_id IS NULL;
-- UPDATE tasks AS t
-- SET user_id = c.user_id
-- FROM courses AS c
-- WHERE c.id = t.course_id AND t.user_id IS NULL;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM courses WHERE user_id IS NULL)
       OR EXISTS (SELECT 1 FROM tasks WHERE user_id IS NULL)
       OR EXISTS (
           SELECT 1
           FROM tasks AS t
           JOIN courses AS c ON c.id = t.course_id
           WHERE t.user_id <> c.user_id
       ) THEN
        RAISE EXCEPTION
            'Set matching user_id on all legacy courses/tasks before enforcing user scope';
    END IF;
END $$;

ALTER TABLE courses
    ALTER COLUMN user_id SET NOT NULL;

ALTER TABLE tasks
    ALTER COLUMN user_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_courses_user_id
    ON courses(user_id);

CREATE INDEX IF NOT EXISTS idx_tasks_user_course
    ON tasks(user_id, course_id);
