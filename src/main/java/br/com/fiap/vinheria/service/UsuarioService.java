package br.com.fiap.vinheria.service;

import java.sql.SQLException;
import java.time.LocalDate;
import java.time.Period;
import java.util.Optional;

import org.mindrot.jbcrypt.BCrypt;

import br.com.fiap.vinheria.dao.UsuarioDao;
import br.com.fiap.vinheria.model.Usuario;

public class UsuarioService {

    private static final int IDADE_MINIMA = 18;
    private static final int TAMANHO_MINIMO_SENHA = 8;
    private static final String REGEX_EMAIL = "^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$";

    // Codigos de erro do SQL Server para violacao de indice/constraint unica
    private static final int ERRO_INDICE_UNICO = 2601;
    private static final int ERRO_CONSTRAINT_UNICA = 2627;

    private final UsuarioDao usuarioDao = new UsuarioDao();

    public Usuario cadastrar(String nome, String email, String senha, String confirmacaoSenha,
            LocalDate dataNascimento) throws ValidacaoException, SQLException {

        String nomeTratado = nome == null ? "" : nome.trim();
        String emailTratado = normalizarEmail(email);

        if (nomeTratado.isEmpty()) {
            throw new ValidacaoException("Informe o nome.");
        }
        if (emailTratado.isEmpty() || !emailTratado.matches(REGEX_EMAIL)) {
            throw new ValidacaoException("Informe um e-mail válido.");
        }
        if (senha == null || senha.length() < TAMANHO_MINIMO_SENHA) {
            throw new ValidacaoException("A senha deve ter pelo menos " + TAMANHO_MINIMO_SENHA + " caracteres.");
        }
        if (!senha.equals(confirmacaoSenha)) {
            throw new ValidacaoException("A confirmação de senha não confere.");
        }
        if (dataNascimento == null || dataNascimento.isAfter(LocalDate.now())) {
            throw new ValidacaoException("Informe uma data de nascimento válida.");
        }
        if (Period.between(dataNascimento, LocalDate.now()).getYears() < IDADE_MINIMA) {
            throw new ValidacaoException("É necessário ter " + IDADE_MINIMA + " anos ou mais para se cadastrar.");
        }
        if (usuarioDao.buscarPorEmail(emailTratado).isPresent()) {
            throw new ValidacaoException("Este e-mail já está cadastrado.");
        }

        String hash = BCrypt.hashpw(senha, BCrypt.gensalt());
        Usuario usuario = new Usuario(nomeTratado, emailTratado, hash, dataNascimento);

        try {
            usuarioDao.inserir(usuario);
        } catch (SQLException e) {
            // Cadastro simultaneo com o mesmo e-mail: o indice unico do banco barra o segundo
            if (e.getErrorCode() == ERRO_INDICE_UNICO || e.getErrorCode() == ERRO_CONSTRAINT_UNICA) {
                throw new ValidacaoException("Este e-mail já está cadastrado.");
            }
            throw e;
        }

        usuario.setSenhaHash(null);
        return usuario;
    }

    public Optional<Usuario> autenticar(String email, String senha) throws SQLException {
        String emailTratado = normalizarEmail(email);

        if (emailTratado.isEmpty() || senha == null || senha.isEmpty()) {
            return Optional.empty();
        }

        Optional<Usuario> encontrado = usuarioDao.buscarPorEmail(emailTratado);

        if (encontrado.isPresent() && BCrypt.checkpw(senha, encontrado.get().getSenhaHash())) {
            Usuario usuario = encontrado.get();
            usuario.setSenhaHash(null); // hash nao vai para a sessao
            return Optional.of(usuario);
        }
        return Optional.empty();
    }

    private String normalizarEmail(String email) {
        return email == null ? "" : email.trim().toLowerCase();
    }
}
