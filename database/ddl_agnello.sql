-- =============================================
-- Vinheria Agnello - DDL (Azure SQL / T-SQL)
-- =============================================

-- Remocao na ordem inversa de dependencia
DROP TABLE IF EXISTS TB_Vinho;
DROP TABLE IF EXISTS TB_Usuario;
DROP TABLE IF EXISTS TB_Tipo_Vinho;

-- Dominio
CREATE TABLE TB_Tipo_Vinho (
    id_tipo INT           NOT NULL,
    nome    NVARCHAR(30)  NOT NULL,
    CONSTRAINT pk_Tipo_Vinho      PRIMARY KEY (id_tipo),
    CONSTRAINT uq_Tipo_Vinho_Nome UNIQUE (nome)
);

CREATE TABLE TB_Usuario (
    id_usuario      BIGINT IDENTITY(1,1) NOT NULL,
    nome            NVARCHAR(100)        NOT NULL,
    email           NVARCHAR(150)        NOT NULL,
    senha_hash      NVARCHAR(100)        NOT NULL,
    data_nascimento DATE                 NOT NULL,
    data_cadastro   DATETIME2            NOT NULL CONSTRAINT df_Usuario_Data_Cadastro DEFAULT SYSUTCDATETIME(),
    ativo           BIT                  NOT NULL CONSTRAINT df_Usuario_Ativo DEFAULT 1,
    CONSTRAINT pk_Usuario PRIMARY KEY (id_usuario)
);

-- E-mail unico apenas entre usuarios ativos (permite recadastro apos soft delete)
CREATE UNIQUE INDEX uq_Usuario_Email_Ativo
    ON TB_Usuario (email)
    WHERE ativo = 1;

CREATE TABLE TB_Vinho (
    id_vinho        BIGINT IDENTITY(1,1) NOT NULL,
    nome            NVARCHAR(120)        NOT NULL,
    id_tipo         INT                  NOT NULL,
    uva             NVARCHAR(150)        NOT NULL,
    pais            NVARCHAR(60)         NOT NULL,
    regiao          NVARCHAR(60)         NULL,
    safra           SMALLINT             NULL,
    teor_alcoolico  DECIMAL(4,1)         NOT NULL,
    volume_ml       INT                  NOT NULL,
    preco           DECIMAL(10,2)        NOT NULL,
    estoque         INT                  NOT NULL CONSTRAINT df_Vinho_Estoque DEFAULT 0,
    caracteristicas NVARCHAR(200)        NULL,
    descricao       NVARCHAR(1000)       NULL,
    imagem_url      NVARCHAR(300)        NULL,
    ativo           BIT                  NOT NULL CONSTRAINT df_Vinho_Ativo DEFAULT 1,
    CONSTRAINT pk_Vinho            PRIMARY KEY (id_vinho),
    CONSTRAINT fk_Vinho_Tipo       FOREIGN KEY (id_tipo) REFERENCES TB_Tipo_Vinho (id_tipo),
    CONSTRAINT chk_Vinho_Preco     CHECK (preco >= 0),
    CONSTRAINT chk_Vinho_Estoque   CHECK (estoque >= 0),
    CONSTRAINT chk_Vinho_Teor      CHECK (teor_alcoolico BETWEEN 0 AND 25),
    CONSTRAINT chk_Vinho_Volume    CHECK (volume_ml > 0),
    CONSTRAINT chk_Vinho_Safra     CHECK (safra IS NULL OR safra BETWEEN 1900 AND 2100)
);

CREATE INDEX idx_Vinho_Tipo ON TB_Vinho (id_tipo);