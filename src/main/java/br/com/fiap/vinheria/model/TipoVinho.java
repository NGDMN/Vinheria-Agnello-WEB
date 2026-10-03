package br.com.fiap.vinheria.model;

public enum TipoVinho {
    TINTO(1, "Tinto"),
    BRANCO(2, "Branco"),
    ROSE(3, "Rosé"),
    ESPUMANTE(4, "Espumante"),
    FORTIFICADO(5, "Fortificado");

    private final int idBanco;
    private final String nome;

    TipoVinho(int idBanco, String nome) {
        this.idBanco = idBanco;
        this.nome = nome;
    }

    public int getIdBanco() {
        return idBanco;
    }

    public String getNome() {
        return nome;
    }

    public static TipoVinho fromId(int id) {
        for (TipoVinho tv : TipoVinho.values()) {
            if (tv.idBanco == id) {
                return tv;
            }
        }
        throw new IllegalArgumentException("ID de TipoVinho inválido: " + id);
    }
}
