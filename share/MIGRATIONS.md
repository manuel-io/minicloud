### 2020.12.06
Add column `category` to the notes tool

    ALTER TABLE minicloud_notes ADD COLUMN category TEXT NOT NULL DEFAULT 'Default';

### 2020.11.29
All timestamps were converted to default utc

    ALTER TABLE minicloud_auths ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;
    ALTER TABLE minicloud_auths ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;
    ALTER TABLE minicloud_auths ALTER COLUMN created_at SET DEFAULT (now() AT TIME ZONE 'utc');

    ALTER TABLE minicloud_diashow ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;
    ALTER TABLE minicloud_diashow ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;
    ALTER TABLE minicloud_diashow ALTER COLUMN created_at SET DEFAULT (now() AT TIME ZONE 'utc');

    ALTER TABLE minicloud_gallery ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;
    ALTER TABLE minicloud_gallery ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;
    ALTER TABLE minicloud_gallery ALTER COLUMN created_at SET DEFAULT (now() AT TIME ZONE 'utc');

    ALTER TABLE minicloud_multimedia ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;
    ALTER TABLE minicloud_multimedia ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;
    ALTER TABLE minicloud_multimedia ALTER COLUMN created_at SET DEFAULT (now() AT TIME ZONE 'utc');

    ALTER TABLE minicloud_notes ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;
    ALTER TABLE minicloud_notes ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;
    ALTER TABLE minicloud_notes ALTER COLUMN created_at SET DEFAULT (now() AT TIME ZONE 'utc');

    ALTER TABLE minicloud_tasks ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;
    ALTER TABLE minicloud_tasks ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;
    ALTER TABLE minicloud_tasks ALTER COLUMN created_at SET DEFAULT (now() AT TIME ZONE 'utc');

    ALTER TABLE minicloud_uploads ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;
    ALTER TABLE minicloud_uploads ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;
    ALTER TABLE minicloud_uploads ALTER COLUMN created_at SET DEFAULT (now() AT TIME ZONE 'utc');

    ALTER TABLE minicloud_users ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;
    ALTER TABLE minicloud_users ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;
    ALTER TABLE minicloud_users ALTER COLUMN created_at SET DEFAULT (now() AT TIME ZONE 'utc');

### 2020.11.15
Move `minicloud.sock` to `/var/minicloud/service`

    mkdir -p /var/minicloud/service
    chown minicloud:minicloud /var/minicloud/service
    chmod a+rx /var/minicloud/service

### 2020.10.18
Modified unique constraints

    ALTER TABLE minicloud_multimedia DROP CONSTRAINT minicloud_multimedia_title_mime_key;
    ALTER TABLE minicloud_multimedia DROP CONSTRAINT minicloud_multimedia_title_year_mime_key;
    ALTER TABLE minicloud_multimedia ADD CONSTRAINT minicloud_multimedia_category_title_year_mime_key UNIQUE (category, title, year, mime);
    CREATE INDEX minicloud_multimedia_actors_idx ON minicloud_multimedia (actors);

### 2020.10.04
New Notes tool. See the updated [database schema](schema.sql)

### 2020.08.23
Update dlna search folders in `/etc/minidlna.conf`

    mv clips videoclips
    mv documentary documentaries
    mkdir ballets musicals
    chmod u=rwx,g=rwx,o=rx ballets musicals
    chown minicloud:minicloud *

### 2020.08.22
Change media types

    UPDATE minicloud_multimedia SET type = 'audiobooks' WHERE type = 'Audiobook';
    UPDATE minicloud_multimedia SET type = 'audiotracks' WHERE type = 'Music';
    UPDATE minicloud_multimedia SET type = 'documentaries' WHERE type = 'Documentary';
    UPDATE minicloud_multimedia SET type = 'movies' WHERE type = 'movie';
    UPDATE minicloud_multimedia SET type = 'series' WHERE type = 'Series';
    UPDATE minicloud_multimedia SET type = 'videoclips' WHERE type = 'Clip';

#### 2020.07.11

    UPDATE minicloud_multimedia SET actors = '{}' WHERE actors is NULL;
    ALTER TABLE minicloud_multimedia ALTER actors SET NOT NULL;
    ALTER TABLE minicloud_multimedia ALTER COLUMN actors SET DEFAULT '{}';
