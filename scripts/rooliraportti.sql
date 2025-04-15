\o roles_report.csv

-- OSA 1: ROOLIT TYYPPEINEEN JA RYHMÄJÄSENYYDET
\echo === ROLES AND GROUP MEMBERSHIPS ===
\copy (SELECT * FROM (SELECT 'rolname' AS rolname, 'tyyppi' AS tyyppi, 'kuuluu_ryhmiin' AS kuuluu_ryhmiin, 'voi_kirjautua' AS voi_kirjautua, NULL::boolean AS login_order UNION ALL SELECT r.rolname, CASE WHEN r.rolcanlogin THEN 'käyttäjä' ELSE 'käyttöoikeusryhmä' END, COALESCE(string_agg(g.rolname, ', '), ''), r.rolcanlogin::text, r.rolcanlogin FROM pg_roles r LEFT JOIN pg_auth_members m ON r.oid = m.member LEFT JOIN pg_roles g ON g.oid = m.roleid GROUP BY r.rolname, r.rolcanlogin) AS data ORDER BY login_order DESC, rolname) TO STDOUT WITH CSV

\echo
-- OSA 2: ROOLIEN PERUSTIEDOT
\echo === ROLES ===
\copy (SELECT 'rolname','rolsuper','rolcreaterole','rolcreatedb','rolcanlogin' UNION ALL SELECT rolname, rolsuper::text, rolcreaterole::text, rolcreatedb::text, rolcanlogin::text FROM pg_roles) TO STDOUT WITH CSV

\echo
-- OSA 3: ROOLIEN JÄSENYYDET
\echo === ROLE MEMBERSHIPS ===
\copy (SELECT 'member','role' UNION ALL SELECT member.rolname, role.rolname FROM pg_auth_members m JOIN pg_roles role ON m.roleid = role.oid JOIN pg_roles member ON m.member = member.oid) TO STDOUT WITH CSV

--\echo
-- OSA 4: TAULUOIKEUDET
--\echo === TABLE PRIVILEGES ===
--\copy (SELECT 'tablename','grantee','privilege_type' UNION ALL SELECT table_name, grantee, privilege_type FROM information_schema.role_table_grants) TO STDOUT WITH CSV

\o
