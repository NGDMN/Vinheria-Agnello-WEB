package br.com.fiap.vinheria.servlet;

import java.io.IOException;
import java.sql.SQLException;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;

import br.com.fiap.vinheria.service.UsuarioService;
import br.com.fiap.vinheria.service.ValidacaoException;
import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

@WebServlet("/signup")
public class SignupServlet extends HttpServlet {

    private static final String VIEW = "/WEB-INF/views/signup.jsp";

    private final UsuarioService usuarioService = new UsuarioService();

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        req.getRequestDispatcher(VIEW).forward(req, resp);
    }

    @Override
    protected void doPost(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        String nome = req.getParameter("nome");
        String email = req.getParameter("email");
        String senha = req.getParameter("senha");
        String confirmacaoSenha = req.getParameter("confirmacaoSenha");
        String dataNascimentoTexto = req.getParameter("dataNascimento");

        try {
            LocalDate dataNascimento = converterData(dataNascimentoTexto);
            usuarioService.cadastrar(nome, email, senha, confirmacaoSenha, dataNascimento);

            // Post/Redirect/Get: evita reenvio do formulario ao atualizar a pagina
            resp.sendRedirect(req.getContextPath() + "/login?cadastro=ok");
        } catch (ValidacaoException e) {
            req.setAttribute("erro", e.getMessage());
            // Devolve os campos preenchidos (exceto senhas)
            req.setAttribute("nome", nome);
            req.setAttribute("email", email);
            req.setAttribute("dataNascimento", dataNascimentoTexto);
            req.getRequestDispatcher(VIEW).forward(req, resp);
        } catch (SQLException e) {
            throw new ServletException("Erro ao cadastrar usuário", e);
        }
    }

    // input type="date" envia no formato yyyy-MM-dd
    private LocalDate converterData(String texto) throws ValidacaoException {
        if (texto == null || texto.isBlank()) {
            return null;
        }
        try {
            return LocalDate.parse(texto);
        } catch (DateTimeParseException e) {
            throw new ValidacaoException("Informe uma data de nascimento válida.");
        }
    }
}
