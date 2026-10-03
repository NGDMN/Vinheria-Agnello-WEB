package br.com.fiap.vinheria.dao;

import java.sql.Connection;
import java.sql.Date;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.Optional;

import br.com.fiap.vinheria.connection.ConexaoBanco;
import br.com.fiap.vinheria.model.Usuario;

public class UsuarioDao {

    public Long inserir(Usuario usuario) throws SQLException {
        String sql = "INSERT INTO TB_Usuario (nome, email, senha_hash, data_nascimento) VALUES (?, ?, ?, ?)";

        try (Connection conexao = ConexaoBanco.conectar(); PreparedStatement stmt = conexao.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS)) {

            stmt.setString(1, usuario.getNome());
            stmt.setString(2, usuario.getEmail());
            stmt.setString(3, usuario.getSenhaHash());
            stmt.setDate(4, Date.valueOf(usuario.getDataNascimento()));
            stmt.executeUpdate();

            try (ResultSet chaves = stmt.getGeneratedKeys()) {
                if (chaves.next()) {
                    Long id = chaves.getLong(1);
                    usuario.setId(id);
                    return id;
                }
            }
        }
        throw new SQLException("Falha ao obter o ID gerado para o usuário");
    }

    public Optional<Usuario> buscarPorEmail(String email) throws SQLException {
        String sql = "SELECT id_usuario, nome, email, senha_hash, data_nascimento, data_cadastro, ativo "
                + "FROM TB_Usuario WHERE email = ? AND ativo = 1";

        try (Connection conexao = ConexaoBanco.conectar(); PreparedStatement stmt = conexao.prepareStatement(sql)) {

            stmt.setString(1, email);

            try (ResultSet rs = stmt.executeQuery()) {
                if (rs.next()) {
                    return Optional.of(mapear(rs));
                }
            }
        }
        return Optional.empty();
    }

    private Usuario mapear(ResultSet rs) throws SQLException {
        Usuario usuario = new Usuario();
        usuario.setId(rs.getLong("id_usuario"));
        usuario.setNome(rs.getString("nome"));
        usuario.setEmail(rs.getString("email"));
        usuario.setSenhaHash(rs.getString("senha_hash"));
        usuario.setDataNascimento(rs.getDate("data_nascimento").toLocalDate());
        usuario.setDataCadastro(rs.getTimestamp("data_cadastro").toLocalDateTime());
        usuario.setAtivo(rs.getBoolean("ativo"));
        return usuario;
    }
}
