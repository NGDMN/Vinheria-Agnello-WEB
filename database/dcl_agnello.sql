   CREATE USER vinheria_app WITH PASSWORD = '<SENHA_FORTE>';

   GRANT SELECT ON dbo.TB_Vinho TO vinheria_app;
   GRANT SELECT, INSERT ON dbo.TB_Usuario TO vinheria_app;