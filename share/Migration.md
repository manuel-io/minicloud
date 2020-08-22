### 2020.08.22

    UPDATE minicloud_multimedia SET type = 'audiobooks' WHERE type = 'Audiobook';
    UPDATE minicloud_multimedia SET type = 'audiotracks' WHERE type = 'Music';
    UPDATE minicloud_multimedia SET type = 'videoclips' WHERE type = 'Clip';
    UPDATE minicloud_multimedia SET type = 'documentaries' WHERE type = 'Documentary';
    UPDATE minicloud_multimedia SET type = 'movies' WHERE type = 'movie';
    UPDATE minicloud_multimedia SET type = 'audiotracks' WHERE type = 'Music';
    UPDATE minicloud_multimedia SET type = 'series' WHERE type = 'Series';
    UPDATE minicloud_multimedia SET type = 'audiotracks' WHERE type = 'Track';

#### 2020.07.11

    UPDATE minicloud_multimedia SET actors = '{}' WHERE actors is NULL;
    ALTER TABLE minicloud_multimedia ALTER actors SET NOT NULL;
    ALTER TABLE minicloud_multimedia ALTER COLUMN actors SET DEFAULT '{}';
