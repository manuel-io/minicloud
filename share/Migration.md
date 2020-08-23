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
