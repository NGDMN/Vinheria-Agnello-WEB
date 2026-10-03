package br.com.fiap.vinheria.dao;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

import br.com.fiap.vinheria.connection.ConexaoBanco;
import br.com.fiap.vinheria.model.TipoVinho;
import br.com.fiap.vinheria.model.Vinho;

public class VinhoDao {

    private static final String COLUNAS
            = "id_vinho, nome, id_tipo, uva, pais, regiao, safra, teor_alcoolico, volume_ml, "
            + "preco, estoque, caracteristicas, descricao, imagem_url, ativo";

    public List<Vinho> listarAtivos() throws SQLException {
        String sql = "SELECT " + COLUNAS + " FROM TB_Vinho WHERE ativo = 1 ORDER BY id_tipo, nome";
        List<Vinho> vinhos = new ArrayList<>();

        try (Connection conexao = ConexaoBanco.conectar(); PreparedStatement stmt = conexao.prepareStatement(sql); ResultSet rs = stmt.executeQuery()) {

            while (rs.next()) {
                vinhos.add(mapear(rs));
            }
        }
        return vinhos;
    }

    public Optional<Vinho> buscarPorId(Long id) throws SQLException {
        String sql = "SELECT " + COLUNAS + " FROM TB_Vinho WHERE id_vinho = ? AND ativo = 1";

        try (Connection conexao = ConexaoBanco.conectar(); PreparedStatement stmt = conexao.prepareStatement(sql)) {

            stmt.setLong(1, id);

            try (ResultSet rs = stmt.executeQuery()) {
                if (rs.next()) {
                    return Optional.of(mapear(rs));
                }
            }
        }
        return Optional.empty();
    }

    private Vinho mapear(ResultSet rs) throws SQLException {
        Vinho vinho = new Vinho();
        vinho.setId(rs.getLong("id_vinho"));
        vinho.setNome(rs.getString("nome"));
        vinho.setTipo(TipoVinho.fromId(rs.getInt("id_tipo")));
        vinho.setUva(rs.getString("uva"));
        vinho.setPais(rs.getString("pais"));
        vinho.setRegiao(rs.getString("regiao"));
        vinho.setSafra(rs.getObject("safra", Integer.class));
        vinho.setTeorAlcoolico(rs.getBigDecimal("teor_alcoolico"));
        vinho.setVolumeMl(rs.getInt("volume_ml"));
        vinho.setPreco(rs.getBigDecimal("preco"));
        vinho.setEstoque(rs.getInt("estoque"));
        vinho.setCaracteristicas(rs.getString("caracteristicas"));
        vinho.setDescricao(rs.getString("descricao"));
        vinho.setImagemUrl(rs.getString("imagem_url"));
        vinho.setAtivo(rs.getBoolean("ativo"));
        return vinho;
    }
}
