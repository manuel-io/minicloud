CREATE TABLE minicloud_users (
id BiGSERIAL UNIQUE PRIMARY KEY,
uuid VARCHAR(32) NOT NULL UNIQUE DEFAULT lpad(md5(random()::text), 32),
name TEXT UNIQUE NOT NULL,
email TEXT UNIQUE NOT NULL,
password TEXT NOT NULL,
admin BOOLEAN NOT NULL DEFAULT false,
disabled BOOLEAN NOT NULL DEFAULT false,
media TEXT,
activation_key VARCHAR(32),
created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
);

CREATE INDEX minicloud_users_uuid_idx ON minicloud_users (uuid);
CREATE INDEX minicloud_users_name_idx ON minicloud_users (name);

CREATE TABLE minicloud_uploads (
id BIGSERIAL UNIQUE PRIMARY KEY,
uid VARCHAR(16) NOT NULL DEFAULT lpad(md5(random()::text), 16),
user_id BIGINT NOT NULL REFERENCES minicloud_users(id) ON DELETE CASCADE,
reference BIGINT REFERENCES minicloud_uploads(id),
backref BIGINT REFERENCES minicloud_uploads(id),
lo OID,
type INT NOT NULL,
title TEXT NOT NULL,
size BIGINT NOT NULL,
mime TEXT NOT NULL,
created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
UNIQUE (user_id, title, reference),
UNIQUE (user_id, uid)
);

CREATE INDEX minicloud_uploads_uid_idx ON minicloud_uploads (uid);
CREATE INDEX minicloud_uploads_user_id_idx ON minicloud_uploads (user_id);
CREATE INDEX minicloud_uploads_reference_idx ON minicloud_uploads (reference);
CREATE INDEX minicloud_uploads_uid_reference_idx ON minicloud_uploads (uid, reference);
CREATE INDEX minicloud_uploads_type_idx ON minicloud_uploads (type);

CREATE TABLE minicloud_gallery (
id BIGSERIAL UNIQUE PRIMARY KEY,
uid VARCHAR(16) NOT NULL DEFAULT lpad(md5(random()::text), 16),
user_id BIGINT NOT NULL REFERENCES minicloud_users(id) ON DELETE CASCADE,
uploads_id BIGINT NOT NULL REFERENCES minicloud_uploads(id) ON DELETE CASCADE,
category TEXT NOT NULL DEFAULT 'Default',
title TEXT NOT NULL,
description TEXT,
thumbnail_data bytea NOT NULL,
thumbnail_size BIGINT NOT NULL,
thumbnail_mime TEXT NOT NULL,
created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
UNIQUE (user_id, title, category),
UNIQUE (uploads_id, title, category),
UNIQUE (user_id, uid)
);

CREATE INDEX minicloud_gallery_uid_idx ON minicloud_gallery (uid);
CREATE INDEX minicloud_gallery_user_id_idx ON minicloud_gallery (user_id);
CREATE INDEX minicloud_gallery_category_idx ON minicloud_gallery (lower(category));

CREATE TABLE minicloud_tasks (
id BIGSERIAL UNIQUE PRIMARY KEY,
uid VARCHAR(16) NOT NULL DEFAULT lpad(md5(random()::text), 16),
user_id BIGINT NOT NULL REFERENCES minicloud_users(id) ON DELETE CASCADE,
status TEXT NOT NULL DEFAULT 'pending',
title TEXT NOT NULL,
description TEXT,
category TEXT NOT NULL DEFAULT 'Default',
due TIMESTAMP WITHOUT TIME ZONE,
done TIMESTAMP WITHOUT TIME ZONE,
process TIMESTAMP WITHOUT TIME ZONE,
created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
updated_at TIMESTAMP NOT NULL,
UNIQUE (user_id, title, category),
UNIQUE (user_id, uid)
);

CREATE INDEX minicloud_tasks_uid_idx ON minicloud_tasks (uid);
CREATE INDEX minicloud_tasks_user_id_idx ON minicloud_tasks (user_id);
CREATE INDEX minicloud_tasks_category_idx ON minicloud_tasks (lower(category));

CREATE TABLE minicloud_notes (
id BIGSERIAL UNIQUE PRIMARY KEY,
uid VARCHAR(16) NOT NULL DEFAULT lpad(md5(random()::text), 16),
user_id BIGINT NOT NULL REFERENCES minicloud_users(id) ON DELETE CASCADE,
description TEXT NOT NULL,
tags TEXT[] NOT NULL DEFAULT '{}',
created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
UNIQUE (user_id, uid)
);

CREATE INDEX minicloud_notes_uid_idx ON minicloud_notes (uid);
CREATE INDEX minicloud_notes_user_id_idx ON minicloud_notes (user_id);
CREATE INDEX minicloud_notes_search_idx ON minicloud_notes USING GIN (to_tsvector('simple', description));

CREATE TABLE minicloud_diashow (
id BIGSERIAL UNIQUE PRIMARY KEY,
uid VARCHAR(16) NOT NULL DEFAULT lpad(md5(random()::text), 16),
uuid VARCHAR(32) NOT NULL UNIQUE DEFAULT lpad(md5(random()::text), 32),
user_id BIGINT NOT NULL REFERENCES minicloud_users(id) ON DELETE CASCADE,
category TEXT NOT NULL,
created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
UNIQUE (user_id, category),
UNIQUE (user_id, uid)
);

CREATE INDEX minicloud_diashow_uid_idx ON minicloud_diashow (uid);
CREATE INDEX minicloud_diashow_user_id_idx ON minicloud_diashow (user_id);
CREATE INDEX minicloud_diashow_uuid_idx ON minicloud_diashow (uuid);
CREATE INDEX minicloud_diashow_category_idx ON minicloud_diashow (lower(category));

CREATE TABLE minicloud_multimedia (
id BIGSERIAL UNIQUE PRIMARY KEY,
uuid VARCHAR(32) NOT NULL UNIQUE DEFAULT lpad(md5(random()::text), 32),
type TEXT NOT NULL,
category TEXT NOT NULL,
title TEXT NOT NULL,
description TEXT,
path TEXT NOT NULL UNIQUE,
mime TEXT NOT NULL,
size BIGINT NOT NULL,
director TEXT NOT NULL DEFAULT 'Generic',
actors TEXT[] NOT NULL DEFAULT '{}',
year INT NOT NULL,
capture TEXT,
created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
UNIQUE (category, title, year, mime),
UNIQUE (path, mime)
);

CREATE INDEX minicloud_multimedia_category_idx ON minicloud_multimedia (lower(category));
CREATE INDEX minicloud_multimedia_type_idx ON minicloud_multimedia (lower(type));
CREATE INDEX minicloud_multimedia_uuid_idx ON minicloud_multimedia (uuid);
CREATE INDEX minicloud_multimedia_director_idx ON minicloud_multimedia (director);
CREATE INDEX minicloud_multimedia_actors_idx ON minicloud_multimedia (actors);
CREATE INDEX minicloud_multimedia_title_idx ON minicloud_multimedia (title);
CREATE INDEX minicloud_multimedia_year_idx ON minicloud_multimedia (year);

CREATE TABLE minicloud_auths (
id BIGSERIAL UNIQUE PRIMARY KEY,
uid VARCHAR(16) NOT NULL DEFAULT lpad(md5(random()::text), 16),
user_id BIGINT NOT NULL REFERENCES minicloud_users(id) ON DELETE CASCADE,
token VARCHAR(32) NOT NULL UNIQUE DEFAULT lpad(md5(random()::text), 32),
xtimes INT NOT NULL DEFAULT 1,
created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
UNIQUE (user_id, uid)
);

CREATE OR REPLACE FUNCTION minicloud_updated_at_task()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now() AT TIME ZONE 'utc';
  RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER minicloud_updated_notes_trigger BEFORE
INSERT OR UPDATE ON minicloud_notes
FOR EACH ROW EXECUTE PROCEDURE minicloud_updated_at_task();

CREATE TRIGGER minicloud_updated_uploads_trigger BEFORE
INSERT OR UPDATE ON minicloud_uploads
FOR EACH ROW EXECUTE PROCEDURE minicloud_updated_at_task();

CREATE TRIGGER minicloud_updated_tasks_trigger BEFORE
INSERT OR UPDATE ON minicloud_tasks
FOR EACH ROW EXECUTE PROCEDURE minicloud_updated_at_task();

CREATE TRIGGER minicloud_updated_users_trigger BEFORE
INSERT OR UPDATE ON minicloud_users
FOR EACH ROW EXECUTE PROCEDURE minicloud_updated_at_task();

CREATE TRIGGER minicloud_updated_gallery_trigger BEFORE
INSERT OR UPDATE ON minicloud_gallery
FOR EACH ROW EXECUTE PROCEDURE minicloud_updated_at_task();

CREATE TRIGGER minicloud_updated_diashow_trigger BEFORE
INSERT OR UPDATE ON minicloud_diashow
FOR EACH ROW EXECUTE PROCEDURE minicloud_updated_at_task();

CREATE TRIGGER minicloud_updated_multimedia_trigger BEFORE
INSERT OR UPDATE ON minicloud_multimedia
FOR EACH ROW EXECUTE PROCEDURE minicloud_updated_at_task();

CREATE TRIGGER minicloud_updated_auth_trigger BEFORE
INSERT OR UPDATE ON minicloud_auths
FOR EACH ROW EXECUTE PROCEDURE minicloud_updated_at_task();

COMMIT;
