\o roles_report.csv

-- OSA 1: ROOLIT TYYPPEINEEN JA RYHMÄJÄSENYYDET
\echo === ROLES AND GROUP MEMBERSHIPS ===
\copy (SELECT 'rolname','tyyppi','kuuluu_ryhmiin' UNION ALL SELECT rol.rolname, CASE WHEN rol.rolcanlogin THEN 'käyttäjä' ELSE 'käyttöoikeusryhmä' END, COALESCE((SELECT string_agg(gr.rolname, ', ') FROM pg_auth_members m JOIN pg_roles gr ON m.roleid = gr.oid WHERE m.member = rol.oid), '') FROM pg_roles rol ORDER BY rol.rolcanlogin DESC, rol.rolname) TO STDOUT WITH CSV

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
