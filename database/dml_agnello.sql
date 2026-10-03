-- =============================================
-- Vinheria Agnello - DML seed (Azure SQL / T-SQL)
-- Executar apos ddl_vinheria.sql
-- =============================================

-- Dominio: tipos de vinho (IDs fixos, espelhados no enum TipoVinho do Java)
INSERT INTO TB_Tipo_Vinho (id_tipo, nome) VALUES
    (1, N'Tinto'),
    (2, N'Branco'),
    (3, N'Rosé'),
    (4, N'Espumante'),
    (5, N'Fortificado');

-- Catalogo
INSERT INTO TB_Vinho
    (nome, id_tipo, uva, pais, regiao, safra, teor_alcoolico, volume_ml, preco, estoque, caracteristicas, descricao, imagem_url)
VALUES
    (N'Catena Malbec', 1, N'Malbec', N'Argentina', N'Mendoza', 2021, 13.5, 750, 159.90, 24,
     N'Encorpado, frutas negras, toque de baunilha',
     N'Malbec de altitude de Mendoza, com notas de ameixa, amora e violeta. Taninos macios e passagem por barrica de carvalho francês.',
     N'vinheria/img/vinhos/Catena.jpeg'),

    (N'Casillero del Diablo Cabernet Sauvignon', 1, N'Cabernet Sauvignon', N'Chile', N'Valle Central', 2022, 13.5, 750, 69.90, 40,
     N'Médio corpo, cassis, pimenta',
     N'Cabernet Sauvignon chileno com aromas de cassis e cereja escura, notas de pimenta e taninos equilibrados.',
     N'vinheria/img/vinhos/Casillero.jpeg'),

    (N'Esporão Reserva Tinto', 1, N'Aragonez, Trincadeira, Cabernet Sauvignon, Alicante Bouschet', N'Portugal', N'Alentejo', 2020, 14.5, 750, 219.90, 12,
     N'Encorpado, frutas maduras, especiarias',
     N'Blend alentejano com fruta madura, especiarias e notas tostadas. Estrutura firme e final persistente.',
     N'vinheria/img/vinhos/Esporao.jpeg'),

    (N'Miolo Lote 43', 1, N'Merlot, Cabernet Sauvignon', N'Brasil', N'Vale dos Vinhedos', 2020, 13.5, 750, 289.90, 0,
     N'Elegante, frutas vermelhas, tostado',
     N'Ícone da Serra Gaúcha, produzido apenas em safras excepcionais. Frutas vermelhas maduras, notas tostadas e grande complexidade.',
     N'vinheria/img/vinhos/Miolo.jpeg'),

    (N'Cloudy Bay Sauvignon Blanc', 2, N'Sauvignon Blanc', N'Nova Zelândia', N'Marlborough', 2023, 13.5, 750, 349.90, 8,
     N'Fresco, cítrico, maracujá',
     N'Referência mundial de Sauvignon Blanc. Aromas de maracujá, limão e ervas frescas, com acidez vibrante.',
     N'vinheria/img/vinhos/CloudyBay.jpeg'),

    (N'Miraval Rosé', 3, N'Cinsault, Grenache, Syrah, Rolle', N'França', N'Provence', 2023, 13.0, 750, 299.90, 15,
     N'Leve, morango, floral',
     N'Rosé provençal de cor pálida, com notas de morango, pêssego e flores brancas. Seco e refrescante.',
     N'vinheria/img/vinhos/Miraval.jpeg'),

    (N'Chandon Brut', 4, N'Chardonnay, Pinot Noir, Riesling Itálico', N'Brasil', N'Serra Gaúcha', NULL, 12.0, 750, 119.90, 30,
     N'Borbulhas finas, maçã verde, brioche',
     N'Espumante pelo método charmat, com perlage fina, notas de maçã verde, frutas cítricas e leve toque de pão.',
     N'vinheria/img/vinhos/Chandon.jpeg'),

    (N'Taylor''s 10 Year Old Tawny', 5, N'Touriga Nacional, Touriga Franca, Tinta Roriz', N'Portugal', N'Douro', NULL, 20.0, 750, 329.90, 6,
     N'Doce, frutas secas, caramelo',
     N'Vinho do Porto envelhecido em barris por cerca de 10 anos. Notas de frutas secas, caramelo e especiarias.',
     N'vinheria/img/vinhos/Taylor.jpeg');

-- Validacao
SELECT * FROM TB_Tipo_Vinho;

SELECT v.id_vinho, v.nome, t.nome AS tipo, v.safra, v.preco, v.estoque,
       CASE WHEN v.estoque = 0 THEN N'Esgotado' ELSE N'Disponível' END AS situacao
FROM TB_Vinho v
JOIN TB_Tipo_Vinho t ON t.id_tipo = v.id_tipo
ORDER BY t.id_tipo, v.nome;