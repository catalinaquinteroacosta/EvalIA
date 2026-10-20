"""Explicit local monetary policy; request scope and concurrency remain enforced."""
def monitoring(connection):
 if not connection.execute("select 1 from sqlite_master where name='monetary_policy'").fetchone():return False
 row=connection.execute('select mode from monetary_policy where id=1').fetchone()
 return bool(row and row[0]=='monitor_only')
