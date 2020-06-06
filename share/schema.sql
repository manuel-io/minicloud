CREATE TABLE minicloud_users (
id SERIAL UNIQUE PRIMARY KEY,
name TEXT UNIQUE NOT NULL,
email TEXT UNIQUE NOT NULL,
password TEXT NOT NULL,
admin BOOLEAN NOT NULL DEFAULT false,
disabled BOOLEAN NOT NULL DEFAULT false,
activation_key TEXT DEFAULT '0',
created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP NOT NULL,
last_login TIMESTAMP
);

CREATE TABLE minicloud_files (
id SERIAL UNIQUE PRIMARY KEY,
uid TEXT NOT NULL DEFAULT lpad(md5(random()::text), 16),
user_id INT NOT NULL REFERENCES minicloud_users(id) ON DELETE CASCADE,
category TEXT NOT NULL DEFAULT 'Default',
title TEXT NOT NULL,
description TEXT,
data_size INT NOT NULL,
data_mime TEXT NOT NULL,
thumbnail_mime TEXT,
thumbnail bytea,
created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP NOT NULL,
UNIQUE (user_id, title, category),
UNIQUE (user_id, uid)
) WITH OIDS;

CREATE INDEX minicloud_files_uid_idx ON minicloud_files (user_id, uid);
CREATE INDEX minicloud_files_category_idx ON minicloud_files (lower(category));

CREATE TABLE minicloud_shared (
id SERIAL UNIQUE PRIMARY KEY,
uid TEXT NOT NULL DEFAULT lpad(md5(random()::text), 16),
user_id INT NOT NULL REFERENCES minicloud_users(id) ON DELETE CASCADE,
file_id INT NOT NULL REFERENCES minicloud_files(id) ON DELETE CASCADE,
file_uid TEXT NOT NULL,
shared_id INT REFERENCES minicloud_users(id),
shared_type INT NOT NULL,
UNIQUE (file_id, shared_type, shared_id),
UNIQUE (user_id, uid)
);

CREATE INDEX minicloud_shared_uid_idx ON minicloud_shared (user_id, uid);

CREATE TABLE minicloud_tasks (
id SERIAL UNIQUE PRIMARY KEY,
user_id INT NOT NULL REFERENCES minicloud_users(id) ON DELETE CASCADE,
status TEXT NOT NULL DEFAULT 'pending',
uid TEXT NOT NULL DEFAULT lpad(md5(random()::text), 16),
entry TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, 
description TEXT NOT NULL,
category TEXT NOT NULL DEFAULT 'Default',
due TIMESTAMP,
done TIMESTAMP,
process TIMESTAMP,
annotation TEXT,
modified TIMESTAMP,
UNIQUE (user_id, description, category),
UNIQUE (user_id, uid)
);

CREATE INDEX minicloud_tasks_uid_idx ON minicloud_tasks (user_id, uid);

CREATE TABLE minicloud_diashow (
id SERIAL UNIQUE PRIMARY KEY,
user_id INT NOT NULL REFERENCES minicloud_users(id) ON DELETE CASCADE,
uid TEXT NOT NULL DEFAULT lpad(md5(random()::text), 16),
uuid TEXT NOT NULL UNIQUE DEFAULT lpad(md5(random()::text), 16),
type TEXT NOT NULL,
category TEXT NOT NULL,
title TEXT NOT NULL,
description TEXT NOT NULL,
created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP NOT NULL,
UNIQUE (user_id, title, category),
UNIQUE (user_id, uid)
);

CREATE INDEX minicloud_diashow_uid_idx ON minicloud_diashow (user_id, uid);
CREATE INDEX minicloud_diashow_uuid_idx ON minicloud_diashow (uuid);
CREATE INDEX minicloud_diashow_category_idx ON minicloud_diashow (lower(category));

CREATE TABLE minicloud_multimedia (
id SERIAL UNIQUE PRIMARY KEY,
uuid TEXT NOT NULL UNIQUE DEFAULT lpad(md5(random()::text), 16),
type TEXT NOT NULL,
category TEXT NOT NULL,
title TEXT NOT NULL,
description TEXT,
path TEXT NOT NULL UNIQUE,
mime TEXT NOT NULL,
size INT NOT NULL,
director TEXT NOT NULL DEFAULT 'Generic',
actors TEXT[],
year INT NOT NULL,
created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP NOT NULL,
UNIQUE (title, mime),
UNIQUE (path, mime)
);

CREATE INDEX minicloud_diashows_multimedia_category_idx ON minicloud_multimedia (lower(category));
CREATE INDEX minicloud_diashows_multimedia_type_idx ON minicloud_multimedia (lower(type));

CREATE OR REPLACE FUNCTION minicloud_modified_task()
RETURNS TRIGGER AS $$
BEGIN
  NEW.modified = now();
  RETURN NEW;
END;
$$ language 'plpgsql';

CREATE OR REPLACE FUNCTION minicloud_updated_at_task()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER minicloud_modified_tasks_trigger BEFORE
INSERT OR UPDATE ON minicloud_tasks
FOR EACH ROW EXECUTE PROCEDURE minicloud_modified_task();

CREATE TRIGGER minicloud_modified_users_trigger BEFORE
INSERT OR UPDATE ON minicloud_users
FOR EACH ROW EXECUTE PROCEDURE minicloud_updated_at_task();

CREATE TRIGGER minicloud_modified_files_trigger BEFORE
INSERT OR UPDATE ON minicloud_files
FOR EACH ROW EXECUTE PROCEDURE minicloud_updated_at_task();

CREATE TRIGGER minicloud_modified_diashow_trigger BEFORE
INSERT OR UPDATE ON minicloud_diashow
FOR EACH ROW EXECUTE PROCEDURE minicloud_updated_at_task();

CREATE TRIGGER minicloud_modified_multimedia_trigger BEFORE
INSERT OR UPDATE ON minicloud_multimedia
FOR EACH ROW EXECUTE PROCEDURE minicloud_updated_at_task();

COMMIT;
