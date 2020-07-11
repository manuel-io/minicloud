#### 2020.07.11

    UPDATE minicloud_multimedia SET actors = '{}' WHERE actors is NULL;
    ALTER TABLE minicloud_multimedia ALTER actors SET NOT NULL;
    ALTER TABLE minicloud_multimedia ALTER COLUMN actors SET DEFAULT '{}';
