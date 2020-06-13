FILE=$(su postgres -c 'psql -c "SHOW hba_file"' | grep conf)
cp /pg_hba.conf $FILE
